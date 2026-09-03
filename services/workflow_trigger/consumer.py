import os
import json
import requests

from confluent_kafka import Consumer
from dotenv import load_dotenv


load_dotenv()

TOPIC = "application.submitted"
PROCESS_KEY = "citizen_application_review"

CAMUNDA_REST_URL = os.getenv(
    "CAMUNDA_REST_URL",
    "http://localhost:8080/engine-rest",
)

CAMUNDA_AUTH_USER = os.getenv("CAMUNDA_AUTH_USER")
CAMUNDA_AUTH_PASSWORD = os.getenv("CAMUNDA_AUTH_PASSWORD")


def get_auth():
    if CAMUNDA_AUTH_USER and CAMUNDA_AUTH_PASSWORD:
        return (
            CAMUNDA_AUTH_USER,
            CAMUNDA_AUTH_PASSWORD,
        )

    return None


def start_process(event):
    unified_app_id = event.get("unified_app_id")

    if not unified_app_id:
        print(
            "[workflow-trigger] event missing "
            "unified_app_id"
        )
        return

    body = {
        "businessKey": unified_app_id,
        "variables": {
            "applicantName": {
                "value": event.get(
                    "applicant_name",
                    "",
                ),
                "type": "String",
            },
            "sourceSystem": {
                "value": event.get(
                    "source_system",
                    "",
                ),
                "type": "String",
            },
            "panNumber": {
                "value": event.get(
                    "pan_number",
                    "",
                ),
                "type": "String",
            },
            "requestType": {
                "value": event.get(
                    "request_type",
                    "",
                ),
                "type": "String",
            },
            "citizenId": {
                "value": event.get(
                    "citizen_id",
                    "",
                ),
                "type": "String",
            },
            "consentId": {
                "value": str(
                    event.get(
                        "consent_id",
                        "",
                    )
                ),
                "type": "String",
            },
            "submissionId": {
                "value": event.get(
                    "submission_id",
                    unified_app_id,
                ),
                "type": "String",
            },
        },
    }

    url = (
        f"{CAMUNDA_REST_URL}/process-definition/"
        f"key/{PROCESS_KEY}/start"
    )

    print(
        f"[workflow-trigger] starting Camunda process "
        f"for {unified_app_id}",
        flush=True,
    )

    try:
        resp = requests.post(
            url,
            json=body,
            auth=get_auth(),
            timeout=10,
        )
    except requests.RequestException as e:
        print(
            f"[workflow-trigger] Camunda connection error "
            f"for {unified_app_id}: {e}",
            flush=True,
        )
        return

    if resp.status_code == 401:
        print(
            "[workflow-trigger] 401 Unauthorized. "
            "Check Camunda authentication settings.",
            flush=True,
        )
        return

    if resp.status_code != 200:
        print(
            f"[workflow-trigger] FAILED for "
            f"{unified_app_id}: "
            f"{resp.status_code} {resp.text}",
            flush=True,
        )
        return

    instance = resp.json()

    print(
        f"[workflow-trigger] started process instance "
        f"{instance.get('id')} for {unified_app_id} "
        f"({event.get('applicant_name', '')})",
        flush=True,
    )


def main():
    bootstrap_servers = os.getenv(
        "KAFKA_BOOTSTRAP_SERVERS",
        "localhost:9092",
    )

    consumer = Consumer({
        "bootstrap.servers": bootstrap_servers,
        "group.id": "workflow-trigger",
        "auto.offset.reset": "earliest",
        "enable.auto.commit": True,
    })

    consumer.subscribe([TOPIC])

    print(
        f"[workflow-trigger] listening on "
        f"'{TOPIC}' ...",
        flush=True,
    )

    try:
        while True:
            msg = consumer.poll(1.0)

            if msg is None:
                continue

            if msg.error():
                print(
                    f"[workflow-trigger] Kafka error: "
                    f"{msg.error()}",
                    flush=True,
                )
                continue

            try:
                raw_value = msg.value().decode("utf-8")
                event = json.loads(raw_value)
            except Exception as e:
                print(
                    f"[workflow-trigger] invalid event: "
                    f"{e}",
                    flush=True,
                )
                continue

            print(
                f"[workflow-trigger] received event "
                f"{event.get('event_type')} "
                f"for "
                f"{event.get('unified_app_id')}",
                flush=True,
            )

            if (
                event.get("event_type")
                == "application.submitted"
            ):
                start_process(event)

    except KeyboardInterrupt:
        print(
            "\n[workflow-trigger] stopped.",
            flush=True,
        )

    finally:
        consumer.close()


if __name__ == "__main__":
    main()