import asyncio
import json
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx
from fastapi import BackgroundTasks, FastAPI, HTTPException
from pydantic import BaseModel

from app.anomaly import AnomalyDetector, AnomalyResult
from app.predict import model_store, predict_shipment
from app.train import run_training

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Discordia ML Service",
    description="XGBoost ETA prediction and delay classification for Discordia logistics",
    version="1.0.0",
)

MODELS_DIR = "/app/models"
RETRAIN_INTERVAL_SECONDS = 30 * 60  # 30 minutes

# In-memory state
_metrics: Dict[str, Any] = {}
_last_trained: Optional[datetime] = None
_model_trained: bool = False

# Prediction cache: {shipment_id: (result_dict, expires_at)}
_prediction_cache: Dict[str, tuple] = {}
CACHE_TTL_SECONDS = 300  # 5 minutes

# Anomaly detector (global singleton)
_anomaly_detector = AnomalyDetector()

# Anomaly results cache: (results_list, expires_at)
_anomaly_cache: Optional[tuple] = None
ANOMALY_CACHE_TTL_SECONDS = 60  # 60 seconds


# -----------------------------------------------------------------------
# Pydantic schemas
# -----------------------------------------------------------------------


class HealthResponse(BaseModel):
    status: str
    model_trained: bool
    last_trained: Optional[str]


class MetricsResponse(BaseModel):
    mae: float
    rmse: float
    accuracy: float
    auc: float
    total_samples: int
    trained_at: str
    model_version: str


class PredictionRequest(BaseModel):
    shipment_id: str


class BatchPredictionRequest(BaseModel):
    shipment_ids: List[str]


class PredictionResponse(BaseModel):
    shipment_id: str
    predicted_delay_minutes: float
    delay_probability: float
    predicted_eta_offset_minutes: float
    confidence: float
    top_factors: List[Dict[str, str]]
    model_version: str


# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------


def _models_exist() -> bool:
    return (
        os.path.exists(f"{MODELS_DIR}/regressor.joblib")
        and os.path.exists(f"{MODELS_DIR}/classifier.joblib")
        and os.path.exists(f"{MODELS_DIR}/metadata.json")
    )


def _wait_for_postgres(max_retries: int = 10, interval: float = 3.0) -> bool:
    """Block until PostgreSQL is ready or retries exhausted."""
    from app.database import engine
    from sqlalchemy import text

    for attempt in range(1, max_retries + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("PostgreSQL is ready.")
            return True
        except Exception as e:
            logger.warning(
                f"Waiting for PostgreSQL ({attempt}/{max_retries}): {e}"
            )
            time.sleep(interval)
    logger.error("PostgreSQL did not become ready in time.")
    return False


async def _fetch_from_backend(path: str, timeout: float = 5.0) -> Any:
    """GET a resource from the backend API."""
    from app.config import settings

    url = f"{settings.backend_url}{path}"
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.json()


async def _get_borders() -> List[Dict[str, Any]]:
    try:
        return await _fetch_from_backend("/api/v1/borders/")
    except Exception as e:
        logger.warning(f"Could not fetch borders from backend: {e}")
        return []


async def _get_warehouses() -> List[Dict[str, Any]]:
    try:
        return await _fetch_from_backend("/api/v1/warehouse/")
    except Exception as e:
        logger.warning(f"Could not fetch warehouses from backend: {e}")
        return []


async def _get_shipment(shipment_id: str) -> Optional[Dict[str, Any]]:
    try:
        return await _fetch_from_backend(f"/api/v1/shipments/{shipment_id}")
    except Exception as e:
        logger.warning(f"Could not fetch shipment {shipment_id}: {e}")
        return None


async def _get_all_shipments() -> List[Dict[str, Any]]:
    try:
        data = await _fetch_from_backend("/api/v1/shipments/?limit=500")
        return data.get("items", [])
    except Exception as e:
        logger.warning(f"Could not fetch shipments list: {e}")
        return []


async def _get_live_trucks() -> List[Dict[str, Any]]:
    try:
        return await _fetch_from_backend("/api/v1/gps/live")
    except Exception as e:
        logger.warning(f"Could not fetch live trucks: {e}")
        return []


def _cache_get(shipment_id: str) -> Optional[Dict[str, Any]]:
    entry = _prediction_cache.get(shipment_id)
    if entry is None:
        return None
    result, expires_at = entry
    if datetime.utcnow() > expires_at:
        del _prediction_cache[shipment_id]
        return None
    return result


def _cache_set(shipment_id: str, result: Dict[str, Any]) -> None:
    _prediction_cache[shipment_id] = (
        result,
        datetime.utcnow() + timedelta(seconds=CACHE_TTL_SECONDS),
    )


def _do_train_sync() -> Dict[str, Any]:
    """Run training synchronously and update global state."""
    global _metrics, _last_trained, _model_trained
    metrics = run_training()
    _metrics = metrics
    _last_trained = datetime.utcnow()
    _model_trained = True
    model_store.reload()
    return metrics


async def _background_retrain_loop():
    """Periodically retrain the model every RETRAIN_INTERVAL_SECONDS."""
    while True:
        await asyncio.sleep(RETRAIN_INTERVAL_SECONDS)
        logger.info("Background retraining triggered...")
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, _do_train_sync)
            logger.info("Background retraining complete.")
        except Exception as e:
            logger.error(f"Background retraining failed: {e}")


# -----------------------------------------------------------------------
# Startup
# -----------------------------------------------------------------------


@app.on_event("startup")
async def startup_event():
    global _metrics, _last_trained, _model_trained

    logger.info("ML service starting up...")

    # Wait for PostgreSQL
    loop = asyncio.get_event_loop()
    pg_ready = await loop.run_in_executor(None, _wait_for_postgres)
    if not pg_ready:
        logger.error("Cannot connect to PostgreSQL; model will not be trained on startup.")

    # Train or load
    if _models_exist():
        logger.info("Existing models found — loading...")
        model_store.load()
        meta = model_store.metadata
        _metrics = {
            "mae": meta.get("mae", 0.0),
            "rmse": meta.get("rmse", 0.0),
            "accuracy": meta.get("accuracy", 0.0),
            "auc": meta.get("auc", 0.0),
            "total_samples": meta.get("total_samples", 0),
            "model_version": meta.get("model_version", "unknown"),
            "trained_at": meta.get("trained_at", datetime.utcnow().isoformat()),
        }
        _last_trained = datetime.fromisoformat(
            meta.get("trained_at", datetime.utcnow().isoformat())
        )
        _model_trained = True
        logger.info(f"Models loaded — version {meta.get('model_version')}")
    else:
        logger.info("No models found — running initial training pipeline...")
        try:
            metrics = await loop.run_in_executor(None, _do_train_sync)
            logger.info(
                f"Initial training complete: MAE={metrics['mae']}, "
                f"RMSE={metrics['rmse']}, Accuracy={metrics['accuracy']}, "
                f"AUC={metrics['auc']}, Samples={metrics['total_samples']}"
            )
        except Exception as e:
            logger.error(f"Initial training failed: {e}")

    # Fit anomaly detector from DB data
    logger.info("Fitting anomaly detector from live data...")
    try:
        trucks, shipments = await asyncio.gather(
            _get_live_trucks(),
            _get_all_shipments(),
        )
        _anomaly_detector.fit_trucks(trucks)
        _anomaly_detector.fit_shipments(shipments)
        logger.info(
            f"Anomaly detector fitted: {len(trucks)} trucks, {len(shipments)} shipments"
        )
    except Exception as e:
        logger.warning(f"Anomaly detector fit failed on startup (non-fatal): {e}")

    # Start background retraining loop
    asyncio.create_task(_background_retrain_loop())
    logger.info("ML service ready.")


# -----------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------


@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(
        status="ok",
        model_trained=_model_trained,
        last_trained=_last_trained.isoformat() if _last_trained else None,
    )


@app.get("/metrics", response_model=MetricsResponse)
def get_metrics():
    if not _model_trained or not _metrics:
        raise HTTPException(status_code=503, detail="Model not yet trained")
    return MetricsResponse(
        mae=_metrics.get("mae", 0.0),
        rmse=_metrics.get("rmse", 0.0),
        accuracy=_metrics.get("accuracy", 0.0),
        auc=_metrics.get("auc", 0.0),
        total_samples=_metrics.get("total_samples", 0),
        trained_at=_metrics.get("trained_at", ""),
        model_version=_metrics.get("model_version", "unknown"),
    )


@app.post("/retrain", response_model=MetricsResponse)
async def retrain():
    logger.info("Manual retrain requested.")
    try:
        loop = asyncio.get_event_loop()
        metrics = await loop.run_in_executor(None, _do_train_sync)
        return MetricsResponse(
            mae=metrics["mae"],
            rmse=metrics["rmse"],
            accuracy=metrics["accuracy"],
            auc=metrics["auc"],
            total_samples=metrics["total_samples"],
            trained_at=metrics["trained_at"],
            model_version=metrics["model_version"],
        )
    except Exception as e:
        logger.error(f"Retrain failed: {e}")
        raise HTTPException(status_code=500, detail=f"Retraining failed: {str(e)}")


@app.post("/predict", response_model=PredictionResponse)
async def predict_single(request: PredictionRequest):
    if not _model_trained:
        raise HTTPException(status_code=503, detail="Model not yet trained")

    # Check cache
    cached = _cache_get(request.shipment_id)
    if cached:
        return PredictionResponse(**cached)

    shipment = await _get_shipment(request.shipment_id)
    if not shipment:
        raise HTTPException(
            status_code=404,
            detail=f"Shipment {request.shipment_id} not found",
        )

    borders, warehouses = await asyncio.gather(_get_borders(), _get_warehouses())

    result = predict_shipment(shipment, borders, warehouses)
    result_dict = result.to_dict()
    _cache_set(request.shipment_id, result_dict)
    return PredictionResponse(**result_dict)


@app.post("/predict/batch", response_model=List[PredictionResponse])
async def predict_batch(request: BatchPredictionRequest):
    if not _model_trained:
        raise HTTPException(status_code=503, detail="Model not yet trained")

    borders, warehouses = await asyncio.gather(_get_borders(), _get_warehouses())

    results = []
    for shipment_id in request.shipment_ids:
        cached = _cache_get(shipment_id)
        if cached:
            results.append(PredictionResponse(**cached))
            continue

        shipment = await _get_shipment(shipment_id)
        if not shipment:
            logger.warning(f"Shipment {shipment_id} not found during batch predict")
            continue

        try:
            result = predict_shipment(shipment, borders, warehouses)
            result_dict = result.to_dict()
            _cache_set(shipment_id, result_dict)
            results.append(PredictionResponse(**result_dict))
        except Exception as e:
            logger.error(f"Prediction failed for {shipment_id}: {e}")

    return results


@app.get("/predict/{shipment_id}", response_model=PredictionResponse)
async def predict_get(shipment_id: str):
    if not _model_trained:
        raise HTTPException(status_code=503, detail="Model not yet trained")

    cached = _cache_get(shipment_id)
    if cached:
        return PredictionResponse(**cached)

    shipment = await _get_shipment(shipment_id)
    if not shipment:
        raise HTTPException(
            status_code=404,
            detail=f"Shipment {shipment_id} not found",
        )

    borders, warehouses = await asyncio.gather(_get_borders(), _get_warehouses())

    result = predict_shipment(shipment, borders, warehouses)
    result_dict = result.to_dict()
    _cache_set(shipment_id, result_dict)
    return PredictionResponse(**result_dict)


# -----------------------------------------------------------------------
# Anomaly detection endpoints
# -----------------------------------------------------------------------


def _anomaly_cache_get() -> Optional[List[Dict[str, Any]]]:
    global _anomaly_cache
    if _anomaly_cache is None:
        return None
    results, expires_at = _anomaly_cache
    if datetime.utcnow() > expires_at:
        _anomaly_cache = None
        return None
    return results


def _anomaly_cache_set(results: List[Dict[str, Any]]) -> None:
    global _anomaly_cache
    _anomaly_cache = (results, datetime.utcnow() + timedelta(seconds=ANOMALY_CACHE_TTL_SECONDS))


@app.get("/anomalies")
async def get_anomalies() -> List[Dict[str, Any]]:
    """
    Fetch live trucks + shipments from backend, run anomaly scoring,
    and return only anomalies. Results cached for 60 seconds.
    """
    cached = _anomaly_cache_get()
    if cached is not None:
        return cached

    try:
        trucks, shipments_data = await asyncio.gather(
            _get_live_trucks(),
            _get_all_shipments(),
        )
    except Exception as e:
        logger.warning(f"Failed to fetch data for anomaly scoring: {e}")
        trucks = []
        shipments_data = []

    try:
        anomalies = _anomaly_detector.score_all(trucks, shipments_data)
        results = [a.to_dict() for a in anomalies]
    except Exception as e:
        logger.error(f"Anomaly scoring failed: {e}")
        results = []

    _anomaly_cache_set(results)
    return results


@app.post("/anomalies/retrain")
async def retrain_anomalies() -> Dict[str, Any]:
    """Refit the anomaly detector from current DB data."""
    global _anomaly_cache

    try:
        trucks, shipments_data = await asyncio.gather(
            _get_live_trucks(),
            _get_all_shipments(),
        )
        _anomaly_detector.fit_trucks(trucks)
        _anomaly_detector.fit_shipments(shipments_data)
        # Invalidate anomaly cache
        _anomaly_cache = None
        logger.info(
            f"Anomaly detector retrained: {len(trucks)} trucks, {len(shipments_data)} shipments"
        )
        return {
            "status": "ok",
            "trucks_used": len(trucks),
            "shipments_used": len(shipments_data),
        }
    except Exception as e:
        logger.error(f"Anomaly retrain failed: {e}")
        raise HTTPException(status_code=500, detail=f"Anomaly retrain failed: {str(e)}")
