"""
Kafka producer helper — wraps confluent-kafka so the gateway doesn't
need to know connection/serialization details.
"""

import os
import json

from confluent_kafka import Producer


_producer = None


def get_producer():
    global _producer

    if _producer is None:
        _producer = Producer({
            "bootstrap.servers": os.getenv(
                "KAFKA_BOOTSTRAP_SERVERS",
                "localhost:9092",
            ),
        })

    return _producer


def _delivery_report(err, msg):
    if err is not None:
        print(f"[kafka] delivery FAILED: {err}")
    else:
        print(
            f"[kafka] delivered -> "
            f"topic={msg.topic()} "
            f"partition={msg.partition()} "
            f"offset={msg.offset()}"
        )


def publish_event(topic: str, event: dict):
    """Publish one JSON event to the given Kafka topic,
    keyed by unified_app_id.
    """

    producer = get_producer()

    key = event.get("unified_app_id", "")

    producer.produce(
        topic,
        key=key.encode("utf-8"),
        value=json.dumps(event).encode("utf-8"),
        callback=_delivery_report,
    )

    producer.flush(timeout=5)