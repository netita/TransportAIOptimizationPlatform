"""
IsolationForest-based anomaly detection for trucks and shipments.
"""
import logging
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import List, Optional

import numpy as np
from sklearn.ensemble import IsolationForest

logger = logging.getLogger(__name__)

# Europe bounding box (rough)
EUROPE_LAT_MIN = 35.0
EUROPE_LAT_MAX = 72.0
EUROPE_LON_MIN = -10.0
EUROPE_LON_MAX = 40.0


@dataclass
class AnomalyResult:
    entity_id: str
    entity_type: str  # "truck" or "shipment"
    anomaly_score: float  # 0-1, higher = more anomalous
    is_anomaly: bool  # anomaly_score > 0.7
    reason: str
    severity: str  # "INFO", "WARNING", "CRITICAL"

    def to_dict(self) -> dict:
        return {
            "entity_id": str(self.entity_id),
            "entity_type": str(self.entity_type),
            "anomaly_score": float(self.anomaly_score),
            "is_anomaly": bool(self.is_anomaly),
            "reason": str(self.reason),
            "severity": str(self.severity),
        }


def _severity_from_score(score: float) -> str:
    if score > 0.9:
        return "CRITICAL"
    elif score > 0.7:
        return "WARNING"
    return "INFO"


def _truck_features(truck: dict) -> Optional[List[float]]:
    """Extract feature vector from a truck dict. Returns None if data is incomplete."""
    try:
        speed = float(truck.get("speed_kmh", 0.0))
        lat = float(truck.get("lat", 0.0))
        lon = float(truck.get("lon", 0.0))
        status = truck.get("status", "IDLE")
        last_updated_str = truck.get("last_updated")

        if last_updated_str:
            # Parse ISO datetime string
            last_updated = datetime.fromisoformat(
                last_updated_str.replace("Z", "+00:00")
            )
            # Ensure timezone-aware
            if last_updated.tzinfo is None:
                last_updated = last_updated.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            time_since_update = (now - last_updated).total_seconds() / 60.0
        else:
            time_since_update = 0.0

        is_moving = 1.0 if status == "MOVING" else 0.0

        return [speed, lat, lon, time_since_update, is_moving]
    except Exception as e:
        logger.debug(f"Failed to extract truck features: {e}")
        return None


def _shipment_features(shipment: dict) -> Optional[List[float]]:
    """Extract feature vector from a shipment dict. Returns None if data is incomplete."""
    try:
        delay_minutes = float(shipment.get("delay_minutes") or 0.0)
        risk_score = float(shipment.get("risk_score", 0.0))
        distance_km = float(shipment.get("distance_km", 0.0))

        priority = shipment.get("priority", "MEDIUM")
        priority_map = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
        priority_encoded = float(priority_map.get(priority, 1))

        created_at_str = shipment.get("created_at")
        if created_at_str:
            created_at = datetime.fromisoformat(
                created_at_str.replace("Z", "+00:00")
            )
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            hours_since_created = (now - created_at).total_seconds() / 3600.0
        else:
            hours_since_created = 0.0

        return [delay_minutes, risk_score, distance_km, priority_encoded, hours_since_created]
    except Exception as e:
        logger.debug(f"Failed to extract shipment features: {e}")
        return None


def _score_to_anomaly(raw_score: float) -> float:
    clamped = max(-1.0, min(0.5, float(raw_score)))
    return round(1.0 - (clamped + 1.0) / 1.5, 4)


class AnomalyDetector:
    def __init__(self):
        self._truck_model = IsolationForest(
            contamination=0.1,
            n_estimators=100,
            random_state=42,
        )
        self._shipment_model = IsolationForest(
            contamination=0.1,
            n_estimators=100,
            random_state=42,
        )
        self._truck_fitted = False
        self._shipment_fitted = False

    def fit_trucks(self, trucks: List[dict]) -> None:
        """Fit the truck anomaly model, augmented with synthetic noise."""
        try:
            feature_vectors = []
            for truck in trucks:
                feats = _truck_features(truck)
                if feats is not None:
                    feature_vectors.append(feats)

            if len(feature_vectors) < 2:
                logger.warning(
                    f"Not enough truck data to fit anomaly model ({len(feature_vectors)} samples)"
                )
                return

            base = np.array(feature_vectors, dtype=float)
            rng = np.random.default_rng(42)

            # Generate 50 synthetic variations per truck by adding Gaussian noise
            synthetic_rows = []
            for row in base:
                noise = rng.normal(0, 1, size=(50, len(row)))
                # Scale noise to feature ranges: speed ±15, lat/lon ±0.5,
                # time_since_update ±10, is_moving ±0 (clamp to 0/1)
                scales = np.array([15.0, 0.5, 0.5, 10.0, 0.0])
                scaled_noise = noise * scales
                variations = row + scaled_noise
                # Clamp is_moving to [0, 1]
                variations[:, 4] = np.clip(variations[:, 4], 0, 1)
                # Clamp speed to non-negative
                variations[:, 0] = np.clip(variations[:, 0], 0, None)
                synthetic_rows.append(variations)

            augmented = np.vstack([base] + synthetic_rows)
            self._truck_model.fit(augmented)
            self._truck_fitted = True
            logger.info(
                f"Truck anomaly model fitted on {len(augmented)} samples "
                f"({len(base)} real + {len(augmented) - len(base)} synthetic)"
            )
        except Exception as e:
            logger.error(f"Failed to fit truck anomaly model: {e}")

    def fit_shipments(self, shipments: List[dict]) -> None:
        """Fit the shipment anomaly model, augmented with synthetic noise."""
        try:
            feature_vectors = []
            for shipment in shipments:
                feats = _shipment_features(shipment)
                if feats is not None:
                    feature_vectors.append(feats)

            if len(feature_vectors) < 2:
                logger.warning(
                    f"Not enough shipment data to fit anomaly model ({len(feature_vectors)} samples)"
                )
                return

            base = np.array(feature_vectors, dtype=float)
            rng = np.random.default_rng(42)

            # Generate 50 synthetic variations per shipment
            synthetic_rows = []
            for row in base:
                noise = rng.normal(0, 1, size=(50, len(row)))
                # Scale noise: delay ±30min, risk ±0.05, distance ±50km,
                # priority ±0 (round/clamp), hours_since_created ±2
                scales = np.array([30.0, 0.05, 50.0, 0.0, 2.0])
                scaled_noise = noise * scales
                variations = row + scaled_noise
                # Clamp values to valid ranges
                variations[:, 0] = np.clip(variations[:, 0], 0, None)   # delay >= 0
                variations[:, 1] = np.clip(variations[:, 1], 0.0, 1.0)  # risk 0-1
                variations[:, 2] = np.clip(variations[:, 2], 0, None)   # distance >= 0
                variations[:, 3] = np.clip(variations[:, 3], 0, 3)      # priority 0-3
                variations[:, 4] = np.clip(variations[:, 4], 0, None)   # hours >= 0
                synthetic_rows.append(variations)

            augmented = np.vstack([base] + synthetic_rows)
            self._shipment_model.fit(augmented)
            self._shipment_fitted = True
            logger.info(
                f"Shipment anomaly model fitted on {len(augmented)} samples "
                f"({len(base)} real + {len(augmented) - len(base)} synthetic)"
            )
        except Exception as e:
            logger.error(f"Failed to fit shipment anomaly model: {e}")

    def score_truck(self, truck: dict) -> AnomalyResult:
        """Compute anomaly score for a single truck."""
        entity_id = truck.get("truck_id", "unknown")
        feats = _truck_features(truck)

        # Determine human-readable reason based on feature values
        def _reason_for_truck(f: List[float]) -> str:
            speed, lat, lon, time_since_update, is_moving = f
            if speed > 120:
                return "Impossible speed detected"
            if time_since_update > 480:
                return "No GPS signal for 8h+"
            if time_since_update > 180 and is_moving == 1.0:
                return "Truck moving but no GPS update for 3h+"
            if not (EUROPE_LAT_MIN <= lat <= EUROPE_LAT_MAX and
                    EUROPE_LON_MIN <= lon <= EUROPE_LON_MAX):
                return "GPS position outside expected region"
            return "Statistical anomaly in movement pattern"

        if feats is None:
            return AnomalyResult(
                entity_id=entity_id,
                entity_type="truck",
                anomaly_score=0.0,
                is_anomaly=False,
                reason="Insufficient data",
                severity="INFO",
            )

        if not self._truck_fitted:
            # Rule-based fallback when model not fitted
            reason = _reason_for_truck(feats)
            score = 0.5
            return AnomalyResult(
                entity_id=entity_id,
                entity_type="truck",
                anomaly_score=score,
                is_anomaly=False,
                reason=reason,
                severity=_severity_from_score(score),
            )

        try:
            X = np.array([feats])
            raw = float(self._truck_model.decision_function(X)[0])
            anomaly_score = _score_to_anomaly(raw)
            is_anomaly = bool(self._truck_model.predict(X)[0] == -1)
            reason = _reason_for_truck(feats)
            return AnomalyResult(
                entity_id=entity_id,
                entity_type="truck",
                anomaly_score=anomaly_score,
                is_anomaly=is_anomaly,
                reason=reason,
                severity=_severity_from_score(anomaly_score),
            )
        except Exception as e:
            logger.warning(f"Error scoring truck {entity_id}: {e}")
            return AnomalyResult(
                entity_id=entity_id,
                entity_type="truck",
                anomaly_score=0.0,
                is_anomaly=False,
                reason="Scoring error",
                severity="INFO",
            )

    def score_shipment(self, shipment: dict) -> AnomalyResult:
        """Compute anomaly score for a single shipment."""
        entity_id = shipment.get("shipment_id", "unknown")
        feats = _shipment_features(shipment)

        def _reason_for_shipment(f: List[float]) -> str:
            delay_minutes, risk_score, distance_km, priority_encoded, hours_since_created = f
            if delay_minutes > 600:
                return "Extreme delay: 10h+"
            if risk_score > 0.9:
                return "Critical risk score"
            return "Statistical anomaly in shipment pattern"

        if feats is None:
            return AnomalyResult(
                entity_id=entity_id,
                entity_type="shipment",
                anomaly_score=0.0,
                is_anomaly=False,
                reason="Insufficient data",
                severity="INFO",
            )

        if not self._shipment_fitted:
            reason = _reason_for_shipment(feats)
            score = 0.5
            return AnomalyResult(
                entity_id=entity_id,
                entity_type="shipment",
                anomaly_score=score,
                is_anomaly=False,
                reason=reason,
                severity=_severity_from_score(score),
            )

        try:
            X = np.array([feats])
            raw = float(self._shipment_model.decision_function(X)[0])
            anomaly_score = _score_to_anomaly(raw)
            is_anomaly = self._shipment_model.predict(X)[0] == -1
            reason = _reason_for_shipment(feats)
            return AnomalyResult(
                entity_id=entity_id,
                entity_type="shipment",
                anomaly_score=anomaly_score,
                is_anomaly=is_anomaly,
                reason=reason,
                severity=_severity_from_score(anomaly_score),
            )
        except Exception as e:
            logger.warning(f"Error scoring shipment {entity_id}: {e}")
            return AnomalyResult(
                entity_id=entity_id,
                entity_type="shipment",
                anomaly_score=0.0,
                is_anomaly=False,
                reason="Scoring error",
                severity="INFO",
            )

    def score_all(self, trucks: List[dict], shipments: List[dict]) -> List[AnomalyResult]:
        """Score all trucks and shipments; return only anomalies (is_anomaly=True)."""
        results = []

        for truck in trucks:
            try:
                result = self.score_truck(truck)
                if result.is_anomaly:
                    results.append(result)
            except Exception as e:
                logger.warning(f"Unexpected error scoring truck: {e}")

        for shipment in shipments:
            try:
                result = self.score_shipment(shipment)
                if result.is_anomaly:
                    results.append(result)
            except Exception as e:
                logger.warning(f"Unexpected error scoring shipment: {e}")

        return results
