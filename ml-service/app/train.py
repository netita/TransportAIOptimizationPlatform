import json
import logging
import random
from datetime import datetime
from typing import Any, Dict, List

import joblib
import numpy as np
from sklearn.metrics import (
    accuracy_score,
    mean_absolute_error,
    mean_squared_error,
    roc_auc_score,
)
from sqlalchemy import text
from xgboost import XGBClassifier, XGBRegressor

from app.database import SessionLocal
from app.features import FEATURE_NAMES, build_feature_vector

logger = logging.getLogger(__name__)

MODELS_DIR = "/app/models"


def _load_shipments_from_db(db) -> List[Dict[str, Any]]:
    result = db.execute(text("""
        SELECT shipment_id, origin, destination,
               origin_lat, origin_lon, dest_lat, dest_lon,
               distance_km, carrier, priority, status,
               eta, actual_arrival, delay_minutes, risk_score,
               truck_id, created_at, updated_at
        FROM shipments
    """))
    columns = result.keys()
    return [dict(zip(columns, row)) for row in result.fetchall()]


def _load_borders_from_db(db) -> List[Dict[str, Any]]:
    result = db.execute(text(
        "SELECT id, name, lat, lon, wait_time_min, inspection_rate, weather_risk, status FROM borders"
    ))
    columns = result.keys()
    return [dict(zip(columns, row)) for row in result.fetchall()]


def _load_warehouses_from_db(db) -> List[Dict[str, Any]]:
    result = db.execute(text(
        "SELECT id, name, city, lat, lon, congestion_risk, queue_time_min FROM warehouses"
    ))
    columns = result.keys()
    return [dict(zip(columns, row)) for row in result.fetchall()]


def _load_trucks_online_from_db(db) -> int:
    result = db.execute(text(
        "SELECT COUNT(*) FROM trucks WHERE status IN ('MOVING', 'IDLE', 'AT_WAREHOUSE', 'AT_BORDER')"
    ))
    return int(result.scalar() or 0)


def _compute_targets(shipment: Dict[str, Any]) -> tuple:
    """Return (delay_minutes, is_delayed) for a real shipment."""
    delay_minutes = float(shipment.get("delay_minutes") or 0)
    is_delayed = 1 if shipment.get("status", "").upper() == "DELAYED" or delay_minutes > 0 else 0
    return delay_minutes, is_delayed


def _synthetic_delay(
    border_wait: float,
    congestion: float,
    distance_km: float,
    noise: float,
) -> float:
    """Formula used for both augmentation and is consistent with features."""
    delay = max(0.0, border_wait * 0.3 + congestion * 60 + distance_km / 1500 * 30 + noise)
    return delay


def run_training() -> Dict[str, Any]:
    """
    Full training pipeline.

    1. Load real data from PostgreSQL
    2. Build feature vectors
    3. Augment synthetically (50x per real shipment)
    4. Train XGBoost regressor + classifier
    5. Compute metrics
    6. Save models + metadata
    7. Return metrics dict
    """
    logger.info("Starting XGBoost training pipeline...")

    db = SessionLocal()
    try:
        shipments = _load_shipments_from_db(db)
        borders = _load_borders_from_db(db)
        warehouses = _load_warehouses_from_db(db)
        trucks_online = _load_trucks_online_from_db(db)
    finally:
        db.close()

    logger.info(
        f"Loaded {len(shipments)} shipments, {len(borders)} borders, "
        f"{len(warehouses)} warehouses from DB"
    )

    if not shipments:
        logger.warning("No shipments in DB — training on synthetic data only")
        # Provide a minimal synthetic base so training doesn't fail completely
        shipments = [
            {
                "shipment_id": f"SYNTH-{i}",
                "origin": "Sofia",
                "destination": "Munich",
                "origin_lat": 42.7,
                "origin_lon": 23.3,
                "dest_lat": 48.1,
                "dest_lon": 11.6,
                "distance_km": 1500,
                "carrier": "Discordia",
                "priority": "MEDIUM",
                "status": "IN_TRANSIT",
                "delay_minutes": 0,
                "created_at": datetime.utcnow(),
            }
            for i in range(10)
        ]

    rng = random.Random(42)
    np_rng = np.random.default_rng(42)

    X_real: List[List[float]] = []
    y_delay_real: List[float] = []
    y_class_real: List[int] = []

    for shipment in shipments:
        fv = build_feature_vector(shipment, borders, warehouses, trucks_online)
        delay_minutes, is_delayed = _compute_targets(shipment)
        X_real.append(fv)
        y_delay_real.append(delay_minutes)
        y_class_real.append(is_delayed)

    X_aug: List[List[float]] = []
    y_delay_aug: List[float] = []
    y_class_aug: List[int] = []

    for i, (fv, shipment) in enumerate(zip(X_real, shipments)):
        for _ in range(50):
            aug = fv.copy()
            # border_wait_time_min is index 3
            aug[3] = max(0.0, aug[3] + rng.uniform(-30, 120))
            # warehouse_congestion_risk is index 6
            aug[6] = max(0.0, min(1.0, aug[6] + rng.uniform(-0.2, 0.3)))
            # hour_of_day is index 8
            aug[8] = float(rng.randint(0, 23))
            # day_of_week is index 9
            aug[9] = float(rng.randint(0, 6))
            # distance_km is index 0
            aug[0] = max(50.0, aug[0] + rng.uniform(-100, 100))

            noise = rng.gauss(0, 15)
            delay = _synthetic_delay(aug[3], aug[6], aug[0], noise)
            is_del = 1 if delay > 45 else 0

            X_aug.append(aug)
            y_delay_aug.append(delay)
            y_class_aug.append(is_del)

    X_all = X_real + X_aug
    y_delay_all = y_delay_real + y_delay_aug
    y_class_all = y_class_real + y_class_aug

    total_samples = len(X_all)
    logger.info(f"Total training samples (real + synthetic): {total_samples}")

    X_np = np.array(X_all, dtype=np.float32)
    y_delay_np = np.array(y_delay_all, dtype=np.float32)
    y_class_np = np.array(y_class_all, dtype=np.int32)

    # ---- Train regressor ----
    regressor = XGBRegressor(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.1,
        subsample=0.8,
        random_state=42,
        verbosity=0,
    )
    regressor.fit(X_np, y_delay_np)

    y_delay_pred = regressor.predict(X_np)
    mae = float(mean_absolute_error(y_delay_np, y_delay_pred))
    rmse = float(np.sqrt(mean_squared_error(y_delay_np, y_delay_pred)))

    # ---- Train classifier ----
    classifier = XGBClassifier(
        n_estimators=200,
        max_depth=5,
        learning_rate=0.1,
        use_label_encoder=False,
        eval_metric="logloss",
        random_state=42,
        verbosity=0,
    )
    classifier.fit(X_np, y_class_np)

    y_class_pred = classifier.predict(X_np)
    y_class_proba = classifier.predict_proba(X_np)[:, 1]
    accuracy = float(accuracy_score(y_class_np, y_class_pred))
    try:
        auc = float(roc_auc_score(y_class_np, y_class_proba))
    except Exception:
        auc = 0.5

    logger.info(
        f"XGBoost ETA Model: MAE={mae:.1f} min, RMSE={rmse:.1f} min | "
        f"Delay Classifier: Accuracy={accuracy * 100:.1f}%, AUC={auc:.3f}"
    )

    # ---- Save models ----
    joblib.dump(regressor, f"{MODELS_DIR}/regressor.joblib")
    joblib.dump(classifier, f"{MODELS_DIR}/classifier.joblib")

    model_version = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    metadata = {
        "feature_names": FEATURE_NAMES,
        "model_version": model_version,
        "trained_at": datetime.utcnow().isoformat(),
        "total_samples": total_samples,
        "real_samples": len(X_real),
        "mae": mae,
        "rmse": rmse,
        "accuracy": accuracy,
        "auc": auc,
    }
    with open(f"{MODELS_DIR}/metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    logger.info(f"Models saved to {MODELS_DIR} (version {model_version})")

    return {
        "mae": round(mae, 2),
        "rmse": round(rmse, 2),
        "accuracy": round(accuracy, 4),
        "auc": round(auc, 4),
        "total_samples": total_samples,
        "model_version": model_version,
        "trained_at": metadata["trained_at"],
    }
