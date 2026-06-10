import math
from datetime import datetime
from typing import Any, Dict, List, Optional


PRIORITY_MAP = {
    "LOW": 0,
    "MEDIUM": 1,
    "HIGH": 2,
    "CRITICAL": 3,
}

CARRIER_MAP = {
    "Discordia": 0,
    "Willi Betz": 1,
    "Schenker": 2,
    "DHL Freight": 3,
    "DB Schenker": 4,
    "Kuehne+Nagel": 5,
    "Ekol": 6,
}

FEATURE_NAMES = [
    "distance_km",
    "priority_encoded",
    "carrier_encoded",
    "border_wait_time_min",
    "border_inspection_rate",
    "border_weather_risk",
    "warehouse_congestion_risk",
    "warehouse_queue_time_min",
    "hour_of_day",
    "day_of_week",
    "is_already_delayed",
    "trucks_online_ratio",
]


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great-circle distance in kilometres between two lat/lon points."""
    R = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def find_nearest_border(origin_lat: float, origin_lon: float, borders: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Return the border closest to the shipment origin coordinates."""
    if not borders:
        return None
    nearest = min(
        borders,
        key=lambda b: haversine_km(origin_lat, origin_lon, b["lat"], b["lon"]),
    )
    return nearest


def find_nearest_warehouse(dest_lat: float, dest_lon: float, warehouses: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Return the warehouse closest to the shipment destination coordinates."""
    if not warehouses:
        return None
    nearest = min(
        warehouses,
        key=lambda w: haversine_km(dest_lat, dest_lon, w["lat"], w["lon"]),
    )
    return nearest


def build_feature_vector(
    shipment: Dict[str, Any],
    borders: List[Dict[str, Any]],
    warehouses: List[Dict[str, Any]],
    trucks_online: int = 25,
    total_trucks: int = 50,
) -> List[float]:
    """
    Build a feature vector for a single shipment.

    Parameters
    ----------
    shipment : dict with keys matching the Shipment model fields
    borders  : list of border dicts (lat, lon, wait_time_min, inspection_rate, weather_risk)
    warehouses: list of warehouse dicts (lat, lon, congestion_risk, queue_time_min)
    trucks_online: number of online trucks
    total_trucks : normalisation denominator (default 50)

    Returns
    -------
    list of 12 floats in FEATURE_NAMES order
    """
    # --- distance ---
    distance_km = float(shipment.get("distance_km") or 0.0)

    # --- priority ---
    priority_raw = str(shipment.get("priority", "MEDIUM")).upper()
    priority_encoded = float(PRIORITY_MAP.get(priority_raw, 1))

    # --- carrier ---
    carrier_raw = str(shipment.get("carrier", ""))
    carrier_encoded = float(CARRIER_MAP.get(carrier_raw, 7))

    # --- nearest border features ---
    origin_lat = float(shipment.get("origin_lat") or 0.0)
    origin_lon = float(shipment.get("origin_lon") or 0.0)
    nearest_border = find_nearest_border(origin_lat, origin_lon, borders)
    if nearest_border:
        border_wait_time_min = float(nearest_border.get("wait_time_min") or 30.0)
        border_inspection_rate = float(nearest_border.get("inspection_rate") or 0.1)
        border_weather_risk = float(nearest_border.get("weather_risk") or 0.0)
    else:
        border_wait_time_min = 30.0
        border_inspection_rate = 0.1
        border_weather_risk = 0.0

    # --- nearest warehouse features ---
    dest_lat = float(shipment.get("dest_lat") or 0.0)
    dest_lon = float(shipment.get("dest_lon") or 0.0)
    nearest_warehouse = find_nearest_warehouse(dest_lat, dest_lon, warehouses)
    if nearest_warehouse:
        warehouse_congestion_risk = float(nearest_warehouse.get("congestion_risk") or 0.0)
        warehouse_queue_time_min = float(nearest_warehouse.get("queue_time_min") or 0.0)
    else:
        warehouse_congestion_risk = 0.0
        warehouse_queue_time_min = 0.0

    # --- temporal features ---
    created_at = shipment.get("created_at")
    if isinstance(created_at, datetime):
        hour_of_day = float(created_at.hour)
        day_of_week = float(created_at.weekday())
    elif isinstance(created_at, str):
        try:
            dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            hour_of_day = float(dt.hour)
            day_of_week = float(dt.weekday())
        except Exception:
            hour_of_day = 12.0
            day_of_week = 0.0
    else:
        hour_of_day = 12.0
        day_of_week = 0.0

    # --- delay status ---
    status_raw = str(shipment.get("status", "")).upper()
    is_already_delayed = 1.0 if status_raw == "DELAYED" else 0.0

    # --- fleet load ---
    trucks_online_ratio = float(trucks_online) / float(max(total_trucks, 1))

    return [
        distance_km,
        priority_encoded,
        carrier_encoded,
        border_wait_time_min,
        border_inspection_rate,
        border_weather_risk,
        warehouse_congestion_risk,
        warehouse_queue_time_min,
        hour_of_day,
        day_of_week,
        is_already_delayed,
        trucks_online_ratio,
    ]
