import os
import sys
import argparse
import requests

from dotenv import load_dotenv


load_dotenv()

CAMUNDA_REST_URL = os.getenv(
    "CAMUNDA_REST_URL",
    "http://localhost:8080/engine-rest",
)

CAMUNDA_AUTH_USER = os.getenv("CAMUNDA_AUTH_USER")
CAMUNDA_AUTH_PASSWORD = os.getenv("CAMUNDA_AUTH_PASSWORD")


def get_auth():
    if CAMUNDA_AUTH_USER and CAMUNDA_AUTH_PASSWORD:
        return (CAMUNDA_AUTH_USER, CAMUNDA_AUTH_PASSWORD)
    return None


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--app-id",
        required=True,
        help="OmniLink unified application ID",
    )

    parser.add_argument(
        "--approved",
        required=True,
        choices=["true", "false"],
    )

    args = parser.parse_args()

    approved_bool = args.approved == "true"

    try:
        resp = requests.get(
            f"{CAMUNDA_REST_URL}/task",
            params={
                "processInstanceBusinessKey": args.app_id
            },
            auth=get_auth(),
            timeout=10,
        )
    except requests.RequestException as e:
        print(f"ERROR: Could not reach Camunda: {e}")
        sys.exit(1)

    if resp.status_code == 401:
        print("ERROR: 401 Unauthorized.")
        sys.exit(1)

    if resp.status_code != 200:
        print(
            f"ERROR: Task lookup failed: "
            f"{resp.status_code} {resp.text}"
        )
        sys.exit(1)

    tasks = resp.json()

    if not tasks:
        print(
            f"No open task found for {args.app_id}."
        )
        print(
            "Check workflow_trigger and confirm the process started."
        )
        sys.exit(1)

    task_id = tasks[0]["id"]

    try:
        complete_resp = requests.post(
            f"{CAMUNDA_REST_URL}/task/{task_id}/complete",
            json={
                "variables": {
                    "approved": {
                        "value": approved_bool,
                        "type": "Boolean",
                    }
                }
            },
            auth=get_auth(),
            timeout=10,
        )
    except requests.RequestException as e:
        print(f"ERROR: Could not complete task: {e}")
        sys.exit(1)

    if complete_resp.status_code not in (200, 204):
        print(
            f"ERROR: Task completion failed: "
            f"{complete_resp.status_code} "
            f"{complete_resp.text}"
        )
        sys.exit(1)

    print(
        f"Task {task_id} completed for {args.app_id} "
        f"— approved={approved_bool}"
    )


if __name__ == "__main__":
    main()