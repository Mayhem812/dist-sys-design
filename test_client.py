import requests
import time
import threading
import argparse

URL = "http://localhost:5000/transaction"


def worker(user_id, requests_per_client, barrier, results):
    total_log = 0
    total_counter = 0

    barrier.wait()

    for _ in range(requests_per_client):
        r = requests.post(URL, json={
            "user_id": user_id,
            "amount": 1
        }, timeout=5)

        data = r.json()

        total_log += data.get("log_time", 0)
        total_counter += data.get("counter_time", 0)

    results.append((total_log, total_counter))


def run_test(clients, requests_per_client, scenario):
    threads = []
    results = []

    barrier = threading.Barrier(clients)

    print(f"\n Running test: clients={clients}, requests={requests_per_client}, scenario={scenario}")

    start = time.time()

    for i in range(clients):
        user_id = str(i) if scenario == 1 else "1"

        t = threading.Thread(
            target=worker,
            args=(user_id, requests_per_client, barrier, results)
        )
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    end = time.time()

    total_requests = clients * requests_per_client
    total_time = end - start
    rps = total_requests / total_time

    total_log = sum(r[0] for r in results)
    total_counter = sum(r[1] for r in results)

    print("\n===== RESULT =====")
    print(f"Total requests: {total_requests}")
    print(f"Total time: {total_time:.2f} sec")
    print(f"RPS: {rps:.2f}")

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