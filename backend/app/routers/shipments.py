import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

import httpx
import redis as redis_lib
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Shipment, ShipmentStatusEnum
from app.schemas import ShipmentListResponse, ShipmentRead, ShipmentStatusUpdate

logger = logging.getLogger(__name__)

router = APIRouter()


def _fetch_predictions_batch(shipment_ids: List[str], timeout: float = 2.0) -> Dict[str, Any]:
    """
    Call ML service POST /predict/batch with a list of shipment_ids.
    Returns a dict keyed by shipment_id.
    Gracefully returns empty dict if the ML service is unavailable.
    """
    if not shipment_ids:
        return {}
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(
                f"{settings.ml_service_url}/predict/batch",
                json={"shipment_ids": shipment_ids},
            )
            resp.raise_for_status()
            predictions = resp.json()
        return {p["shipment_id"]: p for p in predictions}
    except Exception as e:
        logger.warning(f"ML service unavailable for batch predictions: {e}")
        return {}


@router.get("/", response_model=ShipmentListResponse)
def list_shipments(
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    carrier: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    try:
        query = db.query(Shipment)
        if status:
            try:
                query = query.filter(Shipment.status == ShipmentStatusEnum(status))
            except ValueError:
                pass
        if priority:
            from app.models import PriorityEnum
            try:
                query = query.filter(Shipment.priority == PriorityEnum(priority))
            except ValueError:
                pass
        if carrier:
            query = query.filter(Shipment.carrier.ilike(f"%{carrier}%"))

        total = query.count()
        items = (
            query.order_by(Shipment.risk_score.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

        # Enrich with ML predictions (fail-safe: skip if ML unavailable)
        shipment_ids = [s.shipment_id for s in items]
        predictions = _fetch_predictions_batch(shipment_ids)

        enriched_items = []
        for shipment in items:
            pred = predictions.get(shipment.shipment_id)
            shipment_dict = {
                col.name: getattr(shipment, col.name)
                for col in shipment.__table__.columns
            }
            if pred:
                shipment_dict["predicted_delay_minutes"] = pred.get("predicted_delay_minutes")
                shipment_dict["delay_probability"] = pred.get("delay_probability")
                shipment_dict["prediction_confidence"] = pred.get("confidence")
                shipment_dict["top_factors"] = pred.get("top_factors")
            else:
                shipment_dict["predicted_delay_minutes"] = None
                shipment_dict["delay_probability"] = None
                shipment_dict["prediction_confidence"] = None
                shipment_dict["top_factors"] = None
            enriched_items.append(ShipmentRead(**shipment_dict))

        return ShipmentListResponse(items=enriched_items, total=total)
    except Exception as e:
        logger.error(f"Error listing shipments: {e}")
        return ShipmentListResponse(items=[], total=0)


@router.get("/stream/live")
async def stream_shipments():
    async def event_generator():
        r = None
        pubsub = None
        try:
            r = redis_lib.Redis.from_url(settings.redis_url, decode_responses=True)
            pubsub = r.pubsub()
            pubsub.subscribe("live_events")
            yield "data: {\"type\": \"connected\"}\n\n"
            while True:
                message = pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=1.0
                )
                if message and message["type"] == "message":
                    yield f"data: {message['data']}\n\n"
                await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"SSE stream error: {e}")
            yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"
        finally:
            if pubsub:
                try:
                    pubsub.unsubscribe()
                except Exception:
                    pass
            if r:
                try:
                    r.close()
                except Exception:
                    pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{shipment_id}/prediction")
def get_shipment_prediction(shipment_id: str):
    """Proxy to ML service GET /predict/{shipment_id}."""
    try:
        with httpx.Client(timeout=3.0) as client:
            resp = client.get(
                f"{settings.ml_service_url}/predict/{shipment_id}"
            )
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"ML service error: {e.response.text}",
        )
    except Exception as e:
        logger.warning(f"ML service unavailable for prediction of {shipment_id}: {e}")
        raise HTTPException(status_code=503, detail="ML service unavailable")


@router.get("/{shipment_id}", response_model=ShipmentRead)
def get_shipment(shipment_id: str, db: Session = Depends(get_db)):
    shipment = (
        db.query(Shipment).filter(Shipment.shipment_id == shipment_id).first()
    )
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")

    predictions = _fetch_predictions_batch([shipment_id])
    pred = predictions.get(shipment_id)
    shipment_dict = {col.name: getattr(shipment, col.name) for col in shipment.__table__.columns}
    if pred:
        shipment_dict["predicted_delay_minutes"] = pred.get("predicted_delay_minutes")
        shipment_dict["delay_probability"] = pred.get("delay_probability")
        shipment_dict["prediction_confidence"] = pred.get("confidence")
        shipment_dict["top_factors"] = pred.get("top_factors")
    else:
        shipment_dict["predicted_delay_minutes"] = None
        shipment_dict["delay_probability"] = None
        shipment_dict["prediction_confidence"] = None
        shipment_dict["top_factors"] = None
    return ShipmentRead(**shipment_dict)


@router.put("/{shipment_id}/status", response_model=ShipmentRead)
def update_shipment_status(
    shipment_id: str,
    update: ShipmentStatusUpdate,
    db: Session = Depends(get_db),
):
    shipment = (
        db.query(Shipment).filter(Shipment.shipment_id == shipment_id).first()
    )
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")

    shipment.status = update.status
    if update.delay_minutes is not None:
        shipment.delay_minutes = update.delay_minutes
    if update.risk_score is not None:
        shipment.risk_score = update.risk_score

    from datetime import datetime
    shipment.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(shipment)

    try:
        r = redis_lib.Redis.from_url(settings.redis_url, decode_responses=True)
        r.publish(
            "live_events",
            json.dumps(
                {
                    "type": "shipment_update",
                    "shipment_id": shipment_id,
                    "status": update.status.value,
                }
            ),
        )
        r.close()
    except Exception:
        pass

    return shipment
