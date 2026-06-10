"""
Dispatcher Recommendation System — combines ML predictions, route optimization,
anomaly detection, and live operational data into a ranked action list.
"""
import logging
from typing import Any, Dict, List

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Border, Shipment, ShipmentStatusEnum, Warehouse
from app.routers.routes import (
    REROUTE_THRESHOLD_MIN,
    _build_border_map,
    _build_warehouse_map,
    _detect_corridors,
    _score_corridor,
)

router = APIRouter()
logger = logging.getLogger(__name__)

ACTIVE_STATUSES = [
    ShipmentStatusEnum.IN_TRANSIT,
    ShipmentStatusEnum.AT_BORDER,
    ShipmentStatusEnum.AT_WAREHOUSE,
    ShipmentStatusEnum.DELAYED,
    ShipmentStatusEnum.PENDING,
]
URGENCY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}


def _fetch_predictions(shipment_ids: List[str]) -> Dict[str, Dict]:
    if not shipment_ids:
        return {}
    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.post(
                f"{settings.ml_service_url}/predict/batch",
                json={"shipment_ids": shipment_ids},
            )
            if resp.status_code == 200:
                return {p["shipment_id"]: p for p in resp.json()}
    except Exception as e:
        logger.warning(f"Prediction fetch failed: {e}")
    return {}


def _fetch_anomalies() -> List[Dict]:
    try:
        with httpx.Client(timeout=2.0) as client:
            resp = client.get(f"{settings.ml_service_url}/anomalies")
            if resp.status_code == 200:
                return [a for a in resp.json() if a.get("is_anomaly")]
    except Exception as e:
        logger.warning(f"Anomaly fetch failed: {e}")
    return []


@router.get("/recommendations")
def get_dispatcher_recommendations(db: Session = Depends(get_db)):
    actions: List[Dict[str, Any]] = []

    shipments = db.query(Shipment).filter(Shipment.status.in_(ACTIVE_STATUSES)).all()
    borders = db.query(Border).all()
    warehouses = db.query(Warehouse).all()

    border_map = _build_border_map(borders)
    warehouse_map = _build_warehouse_map(warehouses)
    predictions = _fetch_predictions([s.shipment_id for s in shipments])
    anomalies = _fetch_anomalies()

    reroute_ids: set = set()

    # ── 1. REROUTE ──────────────────────────────────────────────────────────
    for shipment in shipments:
        if shipment.status not in (
            ShipmentStatusEnum.IN_TRANSIT,
            ShipmentStatusEnum.AT_BORDER,
            ShipmentStatusEnum.DELAYED,
        ):
            continue
        corridors = _detect_corridors(shipment.origin, shipment.destination)
        if not corridors:
            continue

        scored = [_score_corridor(c, border_map, warehouse_map) for c in corridors]
        primary = next((c for c in corridors if c.get("primary")), corridors[0])
        current = next(s for s in scored if s["corridor_id"] == primary["id"])
        best = min(scored, key=lambda x: x["total_time_min"])

        savings = current["total_time_min"] - best["total_time_min"]
        if best["corridor_id"] == current["corridor_id"] or savings <= REROUTE_THRESHOLD_MIN:
            continue

        urgency = "CRITICAL" if savings > 90 else "HIGH" if savings > 45 else "MEDIUM"
        priority_val = shipment.priority.value if hasattr(shipment.priority, "value") else str(shipment.priority)
        top_bottleneck = current["bottlenecks"][0] if current["bottlenecks"] else "border congestion"
        hours_saved = savings / 60

        reroute_ids.add(shipment.shipment_id)
        actions.append({
            "id": f"reroute-{shipment.shipment_id}",
            "type": "REROUTE",
            "urgency": urgency,
            "title": f"Reroute {shipment.shipment_id}",
            "description": (
                f"{priority_val} · {shipment.origin} → {shipment.destination}. "
                f"{top_bottleneck}. Switch to {best['corridor_name']}."
            ),
            "action": f"Switch to {best['corridor_name']} — saves {hours_saved:.1f}h",
            "entity_id": shipment.shipment_id,
            "entity_type": "shipment",
            "impact_minutes": round(savings),
            "impact_label": f"Saves {hours_saved:.1f}h",
        })

    # ── 2. ESCALATE — high delay probability on HIGH/CRITICAL shipments ─────
    for shipment in shipments:
        if shipment.shipment_id in reroute_ids:
            continue
        pred = predictions.get(shipment.shipment_id, {})
        delay_prob = pred.get("delay_probability", 0.0)
        pred_delay = pred.get("predicted_delay_minutes", 0.0)
        priority_val = shipment.priority.value if hasattr(shipment.priority, "value") else str(shipment.priority)

        if delay_prob < 0.7 or priority_val not in ("CRITICAL", "HIGH"):
            continue

        urgency = "CRITICAL" if delay_prob >= 0.9 or priority_val == "CRITICAL" else "HIGH"
        factors = pred.get("top_factors", [])
        factor_str = f" Top factor: {factors[0]['factor']}." if factors else ""

        actions.append({
            "id": f"escalate-{shipment.shipment_id}",
            "type": "ESCALATE",
            "urgency": urgency,
            "title": f"Escalate {shipment.shipment_id}",
            "description": (
                f"{priority_val} · {int(delay_prob * 100)}% delay probability, "
                f"ML predicts +{int(pred_delay)} min.{factor_str}"
            ),
            "action": "Contact carrier. Update ETA. Notify consignee.",
            "entity_id": shipment.shipment_id,
            "entity_type": "shipment",
            "impact_minutes": round(pred_delay),
            "impact_label": f"{int(delay_prob * 100)}% delay risk",
        })

    # ── 3. INVESTIGATE — anomalous trucks (WARNING/CRITICAL only) ───────────
    seen_trucks: set = set()
    for anomaly in anomalies:
        entity_id = anomaly.get("entity_id", "")
        if anomaly.get("entity_type") != "truck":
            continue
        if anomaly.get("severity") == "INFO" or entity_id in seen_trucks:
            continue
        seen_trucks.add(entity_id)

        score = anomaly.get("anomaly_score", 0.0)
        urgency = "CRITICAL" if anomaly.get("severity") == "CRITICAL" else "HIGH"

        actions.append({
            "id": f"investigate-{entity_id}",
            "type": "INVESTIGATE",
            "urgency": urgency,
            "title": f"Investigate {entity_id}",
            "description": anomaly.get("reason", "Anomalous truck behavior detected."),
            "action": "Verify truck status. Contact driver. Check GPS feed.",
            "entity_id": entity_id,
            "entity_type": "truck",
            "impact_minutes": round(score * 60),
            "impact_label": f"Score: {score:.2f}",
        })

    # ── 4. HOLD — critically congested warehouses ───────────────────────────
    for wh in warehouses:
        if wh.congestion_risk <= 0.8:
            continue
        urgency = "CRITICAL" if wh.congestion_risk > 0.9 else "HIGH"
        pct = int(wh.congestion_risk * 100)

        actions.append({
            "id": f"hold-{wh.id}",
            "type": "HOLD",
            "urgency": urgency,
            "title": f"Hold trucks — {wh.name}",
            "description": (
                f"{wh.name} at {pct}% congestion. "
                f"Queue: {int(wh.queue_time_min)} min. "
                f"{wh.available_docks}/{wh.total_docks} docks free."
            ),
            "action": f"Hold inbound trucks. Redirect to alternative hub.",
            "entity_id": wh.name,
            "entity_type": "warehouse",
            "impact_minutes": round(wh.queue_time_min),
            "impact_label": f"{int(wh.queue_time_min)} min queue",
        })

    # ── Sort & summarise ────────────────────────────────────────────────────
    actions.sort(
        key=lambda a: (URGENCY_ORDER.get(a["urgency"], 4), -(a["impact_minutes"] or 0))
    )

    return {
        "actions": actions[:15],
        "summary": {
            "total": len(actions),
            "critical": sum(1 for a in actions if a["urgency"] == "CRITICAL"),
            "high": sum(1 for a in actions if a["urgency"] == "HIGH"),
            "total_saveable_minutes": sum(
                a["impact_minutes"] for a in actions if a["type"] == "REROUTE"
            ),
        },
    }
