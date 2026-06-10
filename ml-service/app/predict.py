import json
import logging
import threading
from typing import Any, Dict, List, Optional

import joblib
import numpy as np

from app.features import FEATURE_NAMES, build_feature_vector

logger = logging.getLogger(__name__)

MODELS_DIR = "/app/models"

FEATURE_DISPLAY_NAMES = {
    "distance_km": "Route Distance",
    "priority_encoded": "Shipment Priority",
    "carrier_encoded": "Carrier",
    "border_wait_time_min": "Border Wait Time",
    "border_inspection_rate": "Border Inspection Rate",
    "border_weather_risk": "Border Weather Risk",
    "warehouse_congestion_risk": "Warehouse Congestion",
    "warehouse_queue_time_min": "Warehouse Queue Time",
    "hour_of_day": "Hour of Day",
    "day_of_week": "Day of Week",
    "is_already_delayed": "Already Delayed",
    "trucks_online_ratio": "Fleet Load",
}


class ModelStore:
    """Thread-safe lazy-loaded model store."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._regressor = None
        self._classifier = None
        self._metadata: Optional[Dict[str, Any]] = None
        self._loaded = False

    def load(self) -> None:
        with self._lock:
            try:
                self._regressor = joblib.load(f"{MODELS_DIR}/regressor.joblib")
                self._classifier = joblib.load(f"{MODELS_DIR}/classifier.joblib")
                with open(f"{MODELS_DIR}/metadata.json") as f:
                    self._metadata = json.load(f)
                self._loaded = True
                logger.info(
                    f"Models loaded (version {self._metadata.get('model_version', 'unknown')})"
                )
            except Exception as e:
                logger.error(f"Failed to load models: {e}")
                self._loaded = False

    def reload(self) -> None:
        with self._lock:
            self._loaded = False
        self.load()

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def regressor(self):
        return self._regressor

    @property
    def classifier(self):
        return self._classifier

    @property
    def metadata(self) -> Dict[str, Any]:
        return self._metadata or {}


# Singleton model store
model_store = ModelStore()


class PredictionResult:
    def __init__(
        self,
        shipment_id: str,
        predicted_delay_minutes: float,
        delay_probability: float,
        predicted_eta_offset_minutes: float,
        confidence: float,
        top_factors: List[Dict[str, str]],
        model_version: str,
    ) -> None:
        self.shipment_id = shipment_id
        self.predicted_delay_minutes = predicted_delay_minutes
        self.delay_probability = delay_probability
        self.predicted_eta_offset_minutes = predicted_eta_offset_minutes
        self.confidence = confidence
        self.top_factors = top_factors
        self.model_version = model_version

    def to_dict(self) -> Dict[str, Any]:
        return {
            "shipment_id": self.shipment_id,
            "predicted_delay_minutes": self.predicted_delay_minutes,
            "delay_probability": self.delay_probability,
            "predicted_eta_offset_minutes": self.predicted_eta_offset_minutes,
            "confidence": self.confidence,
            "top_factors": self.top_factors,
            "model_version": self.model_version,
        }


def _get_top_factors(
    regressor,
    feature_vector: List[float],
    n: int = 3,
) -> List[Dict[str, str]]:
    """Return top N features by model importance with HIGH/MEDIUM/LOW impact labels."""
    importances = regressor.feature_importances_
    indexed = sorted(enumerate(importances), key=lambda x: x[1], reverse=True)
    top = indexed[:n]

    factors = []
    for idx, importance in top:
        name = FEATURE_NAMES[idx] if idx < len(FEATURE_NAMES) else f"feature_{idx}"
        display = FEATURE_DISPLAY_NAMES.get(name, name.replace("_", " ").title())
        if importance >= 0.2:
            impact = "HIGH"
        elif importance >= 0.1:
            impact = "MEDIUM"
        else:
            impact = "LOW"
        factors.append({"factor": display, "impact": impact})

    return factors


def _compute_confidence(feature_vector: List[float]) -> float:
    """
    Simple confidence proxy: 1 minus the coefficient of variation of the feature vector.
    Clipped to [0.5, 0.99].
    """
    arr = np.array(feature_vector, dtype=np.float32)
    std = float(np.std(arr))
    mean = float(np.mean(np.abs(arr))) + 1e-9
    cv = std / mean
    confidence = max(0.5, min(0.99, 1.0 - cv / 10.0))
    return round(confidence, 3)


def predict_shipment(
    shipment_data: Dict[str, Any],
    borders: List[Dict[str, Any]],
    warehouses: List[Dict[str, Any]],
    trucks_online: int = 25,
) -> PredictionResult:
    """
    Build feature vector and run both models on a single shipment.

    Parameters
    ----------
    shipment_data : dict matching Shipment model fields
    borders       : list of border dicts
    warehouses    : list of warehouse dicts
    trucks_online : current online truck count (fleet load)

    Returns
    -------
    PredictionResult
    """
    if not model_store.is_loaded:
        model_store.load()

    shipment_id = str(shipment_data.get("shipment_id", "unknown"))

    feature_vector = build_feature_vector(
        shipment_data, borders, warehouses, trucks_online
    )
    X = np.array([feature_vector], dtype=np.float32)

    regressor = model_store.regressor
    classifier = model_store.classifier
    metadata = model_store.metadata

    predicted_delay_minutes = float(max(0.0, regressor.predict(X)[0]))
    delay_probability = float(
        np.clip(classifier.predict_proba(X)[0][1], 0.0, 1.0)
    )

    # ETA offset = positive means late, negative means early
    predicted_eta_offset_minutes = predicted_delay_minutes

    confidence = _compute_confidence(feature_vector)
    top_factors = _get_top_factors(regressor, feature_vector, n=3)
    model_version = metadata.get("model_version", "unknown")

    return PredictionResult(
        shipment_id=shipment_id,
        predicted_delay_minutes=round(predicted_delay_minutes, 1),
        delay_probability=round(delay_probability, 3),
        predicted_eta_offset_minutes=round(predicted_eta_offset_minutes, 1),
        confidence=confidence,
        top_factors=top_factors,
        model_version=model_version,
    )
