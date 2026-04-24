import requests
import time
import threading
import argparse

FACADE_URL = "http://localhost:5000/transaction"
COUNTER_METRICS = "http://localhost:5002/metrics"
ACCOUNTS_URL = "http://localhost:5000/accounts"

LOGGING_METRICS = [
    "http://localhost:5001/metrics",
    "http://localhost:5003/metrics",
    "http://localhost:5004/metrics"
]


def worker(user_id, requests_per_client, barrier):
    barrier.wait()

    for _ in range(requests_per_client):
        requests.post(FACADE_URL, json={
            "user_id": user_id,
            "amount": 1
        }, timeout=5)


def wait_until_processed(expected_total):

    while True:
        try:
            data = requests.get(ACCOUNTS_URL, timeout=2).json()
            current_total = sum(data.values())

            if current_total >= expected_total:
                return

        except:
            pass

        time.sleep(30)


def get_total_logging_time():
    total = 0
    for url in LOGGING_METRICS:
        try:
            r = requests.get(url, timeout=2)
            total += r.json().get("total_log_time", 0)
        except:
            continue
    return total


def get_total_counter_time():
    try:
        r = requests.get(COUNTER_METRICS, timeout=2)
        return r.json().get("total_counter_time", 0)
    except:
        return 0


def run_test(clients, requests_per_client, scenario):
    threads = []

    barrier = threading.Barrier(clients)

    print(f"\n Running test: clients={clients}, requests={requests_per_client}, scenario={scenario}")

    start = time.time()

    for i in range(clients):
        user_id = str(i) if scenario == 1 else "1"

        t = threading.Thread(
            target=worker,
            args=(user_id, requests_per_client, barrier)
        )
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    send_end = time.time()

    total_requests = clients * requests_per_client

    wait_until_processed(total_requests)

    end = time.time()

    total_time = send_end - start
    full_time = end - start
    rps = total_requests / total_time

    total_log = get_total_logging_time()
    total_counter = get_total_counter_time()

    print("\n===== RESULT =====")
    print(f"Total requests: {total_requests}")
    print(f"Send time: {total_time:.2f} sec")
    print(f"Full time (with processing): {full_time:.2f} sec")
    print(f"RPS (send phase): {rps:.2f}")

    print("\nService contribution:")
    print(f"Logging total time: {total_log:.2f}")
    print(f"Counter total time: {total_counter:.2f}")

    print(f"Avg logging per request: {total_log / total_requests:.6f}")
    print(f"Avg counter per request: {total_counter / total_requests:.6f}")
    print("==================\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("--clients", type=int, default=10)
    parser.add_argument("--requests", type=int, default=1000)
    parser.add_argument("--scenario", type=int, choices=[1, 2], default=1)

    args = parser.parse_args()

    run_test(args.clients, args.requests, args.scenario)