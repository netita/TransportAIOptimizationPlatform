import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import (
    Alert,
    AlertSeverityEnum,
    AlertTypeEnum,
    Border,
    BorderStatusEnum,
    Shipment,
    ShipmentStatusEnum,
    Truck,
    TruckStatusEnum,
    Warehouse,
)
from app.schemas import AlertRead, CongestionData, KPIDashboard, ModelMetrics, TimelinePoint

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/kpi", response_model=KPIDashboard)
def get_kpi(db: Session = Depends(get_db)):
    try:
        active_statuses = [
            ShipmentStatusEnum.IN_TRANSIT,
            ShipmentStatusEnum.AT_BORDER,
            ShipmentStatusEnum.AT_WAREHOUSE,
            ShipmentStatusEnum.DELAYED,
            ShipmentStatusEnum.PENDING,
        ]
        active_shipments = (
            db.query(Shipment)
            .filter(Shipment.status.in_(active_statuses))
            .count()
        )
        delayed_count = (
            db.query(Shipment)
            .filter(Shipment.status == ShipmentStatusEnum.DELAYED)
            .count()
        )
        at_risk_count = (
            db.query(Shipment)
            .filter(Shipment.risk_score >= 0.6)
            .filter(Shipment.status.in_(active_statuses))
            .count()
        )
        trucks_online = (
            db.query(Truck)
            .filter(
                Truck.status.in_(
                    [
                        TruckStatusEnum.MOVING,
                        TruckStatusEnum.IDLE,
                        TruckStatusEnum.AT_WAREHOUSE,
                        TruckStatusEnum.AT_BORDER,
                    ]
                )
            )
            .count()
        )
        border_alerts = (
            db.query(Alert)
            .filter(Alert.alert_type == AlertTypeEnum.BORDER)
            .filter(Alert.is_read == False)
            .count()
        )

        total_delivered = (
            db.query(Shipment)
            .filter(Shipment.status == ShipmentStatusEnum.DELIVERED)
            .count()
        )
        total_shipments = db.query(Shipment).count()
        on_time_rate = 0.0
        if total_delivered > 0:
            on_time_delivered = (
                db.query(Shipment)
                .filter(Shipment.status == ShipmentStatusEnum.DELIVERED)
                .filter(Shipment.delay_minutes == None)
                .count()
            )
            on_time_rate = on_time_delivered / total_delivered
        elif total_shipments > 0:
            not_delayed = total_shipments - delayed_count
            on_time_rate = not_delayed / total_shipments

        avg_delay_result = (
            db.query(func.avg(Shipment.delay_minutes))
            .filter(Shipment.delay_minutes != None)
            .scalar()
        )
        avg_delay = float(avg_delay_result) if avg_delay_result else 0.0

        return KPIDashboard(
            active_shipments=active_shipments,
            delayed_count=delayed_count,
            at_risk_count=at_risk_count,
            trucks_online=trucks_online,
            border_alerts=border_alerts,
            on_time_rate=round(on_time_rate, 3),
            avg_delay_minutes=round(avg_delay, 1),
        )
    except Exception as e:
        logger.error(f"Error computing KPI: {e}")
        return KPIDashboard(
            active_shipments=0,
            delayed_count=0,
            at_risk_count=0,
            trucks_online=0,
            border_alerts=0,
            on_time_rate=0.0,
            avg_delay_minutes=0.0,
        )


@router.get("/alerts", response_model=List[AlertRead])
def get_alerts(db: Session = Depends(get_db)):
    try:
        alerts = (
            db.query(Alert)
            .order_by(Alert.created_at.desc())
            .limit(50)
            .all()
        )
        return alerts
    except Exception as e:
        logger.error(f"Error fetching alerts: {e}")
        return []


@router.put("/alerts/{alert_id}/read")
def mark_alert_read(alert_id: int, db: Session = Depends(get_db)):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.is_read = True
    db.commit()
    return {"status": "ok"}


@router.get("/shipment-timeline", response_model=List[TimelinePoint])
def get_shipment_timeline(db: Session = Depends(get_db)):
    try:
        now = datetime.utcnow()
        result = []
        for hours_ago in range(23, -1, -1):
            window_start = now - timedelta(hours=hours_ago + 1)
            window_end = now - timedelta(hours=hours_ago)
            hour_label = window_start.strftime("%H:00")

            created = (
                db.query(Shipment)
                .filter(Shipment.created_at >= window_start)
                .filter(Shipment.created_at < window_end)
                .count()
            )
            delivered = (
                db.query(Shipment)
                .filter(Shipment.status == ShipmentStatusEnum.DELIVERED)
                .filter(Shipment.updated_at >= window_start)
                .filter(Shipment.updated_at < window_end)
                .count()
            )
            delayed = (
                db.query(Shipment)
                .filter(Shipment.status == ShipmentStatusEnum.DELAYED)
                .filter(Shipment.updated_at >= window_start)
                .filter(Shipment.updated_at < window_end)
                .count()
            )
            result.append(
                TimelinePoint(
                    hour=hour_label,
                    created=created,
                    delivered=delivered,
                    delayed=delayed,
                )
            )
        return result
    except Exception as e:
        logger.error(f"Error fetching timeline: {e}")
        return []


@router.get("/congestion-heatmap", response_model=List[CongestionData])
def get_congestion_heatmap(db: Session = Depends(get_db)):
    try:
        warehouses = db.query(Warehouse).order_by(Warehouse.congestion_risk.desc()).all()
        return [
            CongestionData(
                name=w.name,
                city=w.city,
                congestion_risk=w.congestion_risk,
                queue_time_min=w.queue_time_min,
                available_docks=w.available_docks,
                total_docks=w.total_docks,
            )
            for w in warehouses
        ]
    except Exception as e:
        logger.error(f"Error fetching congestion heatmap: {e}")
        return []


@router.get("/model-metrics", response_model=ModelMetrics)
def get_model_metrics():
    """Proxy to ML service GET /metrics."""
    try:
        with httpx.Client(timeout=3.0) as client:
            resp = client.get(f"{settings.ml_service_url}/metrics")
            resp.raise_for_status()
            data = resp.json()
            return ModelMetrics(**data)
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"ML service error: {e.response.text}",
        )
    except Exception as e:
        logger.warning(f"ML service unavailable for model-metrics: {e}")
        raise HTTPException(status_code=503, detail="ML service unavailable")


@router.get("/anomalies")
def get_anomalies(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """
    Proxy to ML service GET /anomalies.
    Also creates Alert records in DB for CRITICAL anomalies not already alerted
    in the last 30 minutes.
    """
    try:
        with httpx.Client(timeout=2.0) as client:
            resp = client.get(f"{settings.ml_service_url}/anomalies")
            resp.raise_for_status()
            anomalies: List[Dict[str, Any]] = resp.json()
    except Exception as e:
        logger.warning(f"ML service unavailable for anomalies: {e}")
        return []

    # Fire-and-forget: create Alert records for CRITICAL anomalies not recently alerted
    try:
        cutoff = datetime.utcnow() - timedelta(minutes=30)
        for anomaly in anomalies:
            if anomaly.get("severity") != "CRITICAL":
                continue
            entity_id = anomaly.get("entity_id", "")
            entity_type = anomaly.get("entity_type", "")

            # Build query to check if a recent ANOMALY alert already exists
            existing_query = (
                db.query(Alert)
                .filter(Alert.alert_type == AlertTypeEnum.ANOMALY)
                .filter(Alert.created_at >= cutoff)
            )
            if entity_type == "truck":
                existing_query = existing_query.filter(Alert.truck_id == entity_id)
            else:
                existing_query = existing_query.filter(Alert.shipment_id == entity_id)

            if existing_query.first() is not None:
                continue

            # Create new alert
            alert = Alert(
                alert_type=AlertTypeEnum.ANOMALY,
                severity=AlertSeverityEnum.CRITICAL,
                message=f"[ANOMALY] {entity_id}: {anomaly.get('reason', '')}",
                shipment_id=entity_id if entity_type == "shipment" else None,
                truck_id=entity_id if entity_type == "truck" else None,
                is_read=False,
            )
            db.add(alert)

        db.commit()
    except Exception as e:
        logger.warning(f"Failed to create anomaly alert records (non-fatal): {e}")
        try:
            db.rollback()
        except Exception:
            pass

    return anomalies


@router.get("/predictions/summary")
def get_predictions_summary(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Fetch predictions for all active shipments from the ML service,
    then return aggregate summary statistics.
    """
    active_statuses = [
        ShipmentStatusEnum.IN_TRANSIT,
        ShipmentStatusEnum.AT_BORDER,
        ShipmentStatusEnum.AT_WAREHOUSE,
        ShipmentStatusEnum.DELAYED,
        ShipmentStatusEnum.PENDING,
    ]
    active_shipments = (
        db.query(Shipment).filter(Shipment.status.in_(active_statuses)).all()
    )
    shipment_ids = [s.shipment_id for s in active_shipments]

    if not shipment_ids:
        return {
            "avg_predicted_delay": 0.0,
            "pct_likely_delayed": 0.0,
            "top_factors": [],
        }

    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.post(
                f"{settings.ml_service_url}/predict/batch",
                json={"shipment_ids": shipment_ids},
            )
            resp.raise_for_status()
            predictions = resp.json()
    except Exception as e:
        logger.warning(f"ML service unavailable for predictions summary: {e}")
        return {
            "avg_predicted_delay": 0.0,
            "pct_likely_delayed": 0.0,
            "top_factors": [],
        }

    if not predictions:
        return {
            "avg_predicted_delay": 0.0,
            "pct_likely_delayed": 0.0,
            "top_factors": [],
        }

    delays = [p["predicted_delay_minutes"] for p in predictions]
    probs = [p["delay_probability"] for p in predictions]
    avg_predicted_delay = round(sum(delays) / len(delays), 1) if delays else 0.0
    pct_likely_delayed = round(
        sum(1 for p in probs if p >= 0.5) / len(probs) * 100, 1
    ) if probs else 0.0

    # Aggregate top factors across all predictions
    factor_counts: Dict[str, int] = {}
    for pred in predictions:
        for fac in pred.get("top_factors", []):
            factor_name = fac.get("factor", "")
            if factor_name:
                factor_counts[factor_name] = factor_counts.get(factor_name, 0) + 1

    top_factors = sorted(factor_counts.items(), key=lambda x: x[1], reverse=True)[:3]
    top_factors_list = [{"factor": f, "count": c} for f, c in top_factors]

    return {
        "avg_predicted_delay": avg_predicted_delay,
        "pct_likely_delayed": pct_likely_delayed,
        "top_factors": top_factors_list,
    }
