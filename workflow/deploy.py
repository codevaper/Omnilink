import os
import sys
import requests
from dotenv import load_dotenv


load_dotenv()


CAMUNDA_REST_URL = os.getenv(
    "CAMUNDA_REST_URL",
    "http://localhost:8080/engine-rest"
).rstrip("/")


BPMN_FILE = os.path.join(
    os.path.dirname(__file__),
    "citizen_application_review.bpmn"
)


def deploy_bpmn():
    print(f"Deploying BPMN to {CAMUNDA_REST_URL}")

    if not os.path.exists(BPMN_FILE):
        print(f"ERROR: BPMN file not found: {BPMN_FILE}")
        sys.exit(1)

    try:
        with open(BPMN_FILE, "rb") as f:
            files = {
                "deployment-name": (
                    None,
                    "citizen_application_review"
                ),
                "enable-duplicate-filtering": (
                    None,
                    "false"
                ),
                "deployment-source": (
                    None,
                    "OmniLink"
                ),
                "citizen_application_review.bpmn": (
                    "citizen_application_review.bpmn",
                    f,
                    "application/xml"
                ),
            }

            response = requests.post(
                f"{CAMUNDA_REST_URL}/deployment/create",
                files=files,
                timeout=30
            )

    except requests.RequestException as exc:
        print(f"ERROR: could not connect to Camunda: {exc}")
        sys.exit(1)

    if response.status_code not in (200, 201):
        print(f"ERROR: deployment failed: HTTP {response.status_code}")
        print(response.text)
        sys.exit(1)

    data = response.json()

    deployment_id = data.get("id")
    deployed_processes = data.get("deployedProcessDefinitions") or {}

    print("Deployment successful.")
    print(f"  Deployment ID: {deployment_id}")

    if deployed_processes:
        for process_id, process in deployed_processes.items():
            key = process.get("key", process_id)
            version = process.get("version")
            definition_id = process.get("id")

            print(
                f"  Process definition: "
                f"{key} v{version} (id={definition_id})"
            )
    else:
        print(
            "  Process definition: deployment accepted by Camunda."
        )


if __name__ == "__main__":
    deploy_bpmn()