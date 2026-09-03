"""
Tracker stub
-------------
The simplest possible Kafka consumer — just proves that events
published by the gateway actually arrive on the other side. This gets
replaced by a real, persistent citizen tracker (with storage + UI) in
Step 6. For now it only prints to the console.
"""

import os
import json

from confluent_kafka import Consumer
from dotenv import load_dotenv


load_dotenv()

TOPIC = "application_events"


def main():
    consumer = Consumer({
        "bootstrap.servers": os.getenv(
            "KAFKA_BOOTSTRAP_SERVERS",
            "localhost:9092",
        ),
        "group.id": "tracker-stub",
        "auto.offset.reset": "earliest",
    })

    consumer.subscribe([TOPIC])

    print(
        f"[tracker-stub] listening on topic '{TOPIC}' "
        f"... (Ctrl+C to stop)"
    )

    try:
        while True:
            msg = consumer.poll(1.0)

            if msg is None:
                continue

            if msg.error():
                print(f"[tracker-stub] error: {msg.error()}")
                continue

            event = json.loads(msg.value().decode("utf-8"))

            print("\n=== NEW EVENT RECEIVED ===")
            print(f"  Type:          {event.get('event_type')}")
            print(f"  App ID:        {event.get('unified_app_id')}")
            print(f"  Applicant:     {event.get('applicant_name')}")
            print(f"  Source system: {event.get('source_system')}")
            print(f"  Timestamp:     {event.get('timestamp')}")
            print("===========================\n")

    except KeyboardInterrupt:
        print("\n[tracker-stub] stopped.")

    finally:
        consumer.close()


if __name__ == "__main__":
    main()