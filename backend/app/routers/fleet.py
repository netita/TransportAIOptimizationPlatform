"""
Fleet Load Balancing — matches available trucks to pending shipments,
analyses corridor load distribution, and scores overall fleet balance.
"""
import logging
import math
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Shipment, ShipmentStatusEnum, Truck, TruckStatusEnum
from app.routers.routes import _detect_corridors

router = APIRouter()
logger = logging.getLogger(__name__)

PRIORITY_WEIGHT = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}

# Trucks per corridor considered balanced / overloaded
CORRIDOR_BALANCED_MAX = 5
CORRIDOR_HIGH_MAX = 8

ACTIVE_STATUSES = [
    ShipmentStatusEnum.IN_TRANSIT,
    ShipmentStatusEnum.AT_BORDER,
    ShipmentStatusEnum.DELAYED,
    ShipmentStatusEnum.AT_WAREHOUSE,
]


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(dlon / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))


def _pval(obj, attr: str) -> str:
    v = getattr(obj, attr)
    return v.value if hasattr(v, "value") else str(v)


def _build_corridor_load(shipments: List) -> List[Dict[str, Any]]:
    """Count active trucks per recognised corridor."""
    counts: Dict[str, int] = {}
    names: Dict[str, str] = {}

    for s in shipments:
        if not s.truck_id:
            continue
        corridors = _detect_corridors(s.origin, s.destination)
        if not corridors:
            continue
        # Use the primary corridor (or first match)
        primary = next((c for c in corridors if c.get("primary")), corridors[0])
        cid = primary["id"]
        counts[cid] = counts.get(cid, 0) + 1
        names[cid] = primary["name"]

    result = []
    for cid, cnt in sorted(counts.items(), key=lambda x: -x[1]):
        if cnt >= CORRIDOR_HIGH_MAX:
            level = "CRITICAL"
            rec = "Overloaded — avoid new assignments. Redistribute to lighter corridor."
        elif cnt >= CORRIDOR_BALANCED_MAX:
            level = "HIGH"
            rec = "Near capacity — prefer alternative corridors for new shipments."
        elif cnt >= 2:
            level = "BALANCED"
            rec = "Load within normal range."
        else:
            level = "LOW"
            rec = "Underutilised — prioritise this corridor for new assignments."

        result.append({
            "corridor_id": cid,
            "corridor_name": names[cid],
            "active_trucks": cnt,
            "load_level": level,
            "recommendation": rec,
        })

    return result


def _balance_score(corridor_load: List[Dict]) -> float:
    """0–1: 1 = perfectly even, 0 = all trucks on one corridor."""
    if len(corridor_load) <= 1:
        return 1.0 if corridor_load else 0.0
    loads = [c["active_trucks"] for c in corridor_load]
    mean = sum(loads) / len(loads)
    if mean == 0:
        return 1.0
    variance = sum((x - mean) ** 2 for x in loads) / len(loads)
    cv = math.sqrt(variance) / mean           # coefficient of variation
    return round(max(0.0, min(1.0, 1.0 - cv)), 2)


@router.get("/balance")
def get_fleet_balance(db: Session = Depends(get_db)):
    # ── Load data ───────────────────────────────────────────────────────────
    all_trucks = db.query(Truck).all()
    all_shipments = db.query(Shipment).all()

    available_trucks = [
        t for t in all_trucks
        if _pval(t, "status") in ("IDLE", "AT_WAREHOUSE")
        and not t.current_shipment_id
    ]
    pending_shipments = [
        s for s in all_shipments
        if _pval(s, "status") == "PENDING" and not s.truck_id
    ]
    active_shipments = [
        s for s in all_shipments
        if _pval(s, "status") in [x.value for x in ACTIVE_STATUSES]
    ]

    # ── Corridor load analysis ───────────────────────────────────────────────
    corridor_load = _build_corridor_load(active_shipments)
    balance = _balance_score(corridor_load)
    overloaded = sum(1 for c in corridor_load if c["load_level"] in ("HIGH", "CRITICAL"))

    # ── Assignment: greedy nearest-truck to highest-priority shipment ────────
    assignments: List[Dict[str, Any]] = []
    unassigned: List[Dict[str, Any]] = []

    if pending_shipments and available_trucks:
        sorted_shipments = sorted(
            pending_shipments,
            key=lambda s: (PRIORITY_WEIGHT.get(_pval(s, "priority"), 1), s.risk_score),
            reverse=True,
        )
        pool = list(available_trucks)

        for shipment in sorted_shipments:
            if not pool:
                unassigned.append({
                    "shipment_id": shipment.shipment_id,
                    "priority": _pval(shipment, "priority"),
                    "origin": shipment.origin,
                    "destination": shipment.destination,
                    "reason": "No available trucks remaining in pool.",
                })
                continue

            # Nearest truck by Haversine
            best = min(
                pool,
                key=lambda t: _haversine(t.lat, t.lon, shipment.origin_lat, shipment.origin_lon),
            )
            dist = round(_haversine(best.lat, best.lon, shipment.origin_lat, shipment.origin_lon), 1)
            priority_val = _pval(shipment, "priority")
            pw = PRIORITY_WEIGHT.get(priority_val, 1)
            score = round((pw / 4) * max(0.1, 1 - dist / 500), 3)

            assignments.append({
                "truck_id": best.truck_id,
                "shipment_id": shipment.shipment_id,
                "priority": priority_val,
                "distance_km": dist,
                "score": score,
                "truck_status": _pval(best, "status"),
                "origin": shipment.origin,
                "destination": shipment.destination,
                "reason": (
                    f"Nearest available truck ({dist} km away). "
                    f"{priority_val} priority shipment."
                ),
            })
            pool.remove(best)

    # ── Leftover available trucks (nothing pending to assign) ────────────────
    idle_unmatched: List[Dict[str, Any]] = []
    assigned_truck_ids = {a["truck_id"] for a in assignments}
    for t in available_trucks:
        if t.truck_id not in assigned_truck_ids:
            idle_unmatched.append({
                "truck_id": t.truck_id,
                "status": _pval(t, "status"),
                "lat": t.lat,
                "lon": t.lon,
            })

    return {
        "assignments": assignments,
        "unassigned_shipments": unassigned,
        "idle_trucks": idle_unmatched,
        "corridor_load": corridor_load,
        "summary": {
            "total_trucks": len(all_trucks),
            "available_trucks": len(available_trucks),
            "active_trucks": len(all_trucks) - len(available_trucks),
            "pending_shipments": len(pending_shipments),
            "assignments_made": len(assignments),
            "balance_score": balance,
            "overloaded_corridors": overloaded,
        },
    }
