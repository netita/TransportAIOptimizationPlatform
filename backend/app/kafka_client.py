import json
import logging
from typing import Any, Dict, Optional

from app.config import settings

logger = logging.getLogger(__name__)

_producer = None

TOPICS = {
    "gps": "gps-events",
    "shipment": "shipment-events",
    "warehouse": "warehouse-events",
    "border": "border-events",
}


def get_producer():
    global _producer
    if _producer is None:
        try:
            from kafka import KafkaProducer

            _producer = KafkaProducer(
                bootstrap_servers=settings.kafka_bootstrap_servers.split(","),
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                key_serializer=lambda k: k.encode("utf-8") if k else None,
                retries=3,
                request_timeout_ms=5000,
                api_version_auto_timeout_ms=5000,
            )
            logger.info("Kafka producer connected")
        except Exception as e:
            logger.warning(f"Kafka producer not available: {e}")
            _producer = None
    return _producer


def publish(topic: str, data: Dict[str, Any], key: Optional[str] = None) -> bool:
    producer = get_producer()
    if producer is None:
        logger.debug(f"Kafka not available, skipping publish to {topic}")
        return False
    try:
        future = producer.send(topic, value=data, key=key)
        producer.flush(timeout=2)
        return True
    except Exception as e:
        logger.warning(f"Failed to publish to Kafka topic {topic}: {e}")
        return False


def publish_gps_event(truck_id: str, lat: float, lon: float, speed: float) -> bool:
    return publish(
        TOPICS["gps"],
        {"truck_id": truck_id, "lat": lat, "lon": lon, "speed_kmh": speed},
        key=truck_id,
    )


def publish_shipment_event(shipment_id: str, status: str, data: Dict) -> bool:
    return publish(
        TOPICS["shipment"],
        {"shipment_id": shipment_id, "status": status, **data},
        key=shipment_id,
    )


def publish_warehouse_event(warehouse_id: int, data: Dict) -> bool:
    return publish(TOPICS["warehouse"], {"warehouse_id": warehouse_id, **data})


def publish_border_event(border_id: int, data: Dict) -> bool:
    return publish(TOPICS["border"], {"border_id": border_id, **data})
