"""
Route Optimization Engine — compares corridor options per shipment
using live border wait times and warehouse congestion data.
"""
import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Border, Shipment, ShipmentStatusEnum, Warehouse

router = APIRouter()
logger = logging.getLogger(__name__)

AVG_SPEED_KMH = 80.0
REROUTE_THRESHOLD_MIN = 30.0  # minimum savings to recommend a reroute

# Each corridor defines border checkpoints (partial name match) and optional warehouse stops.
# Primary=True marks the default route for that origin-destination pair.
CORRIDORS: List[Dict[str, Any]] = [
    {
        "id": "TR_DE_RS",
        "name": "Turkey → Germany (via Serbia)",
        "origin_contains": ["istanbul", "turkey"],
        "dest_contains": ["munich", "berlin", "hamburg", "germany", "frankfurt", "cologne"],
        "borders": ["Kapitan Andreevo", "Kalotina", "Batrovci", "Nickelsdorf"],
        "warehouses": ["Sofia Hub"],
        "distance_km": 2200,
        "primary": True,
    },
    {
        "id": "TR_DE_RO",
        "name": "Turkey → Germany (via Romania)",
        "origin_contains": ["istanbul", "turkey"],
        "dest_contains": ["munich", "berlin", "hamburg", "germany", "frankfurt", "cologne"],
        "borders": ["Kapitan Andreevo", "Giurgiu", "Nadlac", "Nickelsdorf"],
        "warehouses": ["Sofia Hub", "Bucharest Hub"],
        "distance_km": 2380,
        "primary": False,
    },
    {
        "id": "TR_AT_RS",
        "name": "Turkey → Austria (via Serbia)",
        "origin_contains": ["istanbul", "turkey"],
        "dest_contains": ["vienna", "austria", "budapest", "hungary"],
        "borders": ["Kapitan Andreevo", "Kalotina", "Batrovci", "Nickelsdorf"],
        "warehouses": ["Sofia Hub"],
        "distance_km": 1800,
        "primary": True,
    },
    {
        "id": "TR_AT_RO",
        "name": "Turkey → Austria (via Romania)",
        "origin_contains": ["istanbul", "turkey"],
        "dest_contains": ["vienna", "austria", "budapest", "hungary"],
        "borders": ["Kapitan Andreevo", "Giurgiu", "Nadlac", "Nickelsdorf"],
        "warehouses": ["Sofia Hub", "Bucharest Hub"],
        "distance_km": 1980,
        "primary": False,
    },
    {
        "id": "BG_DE_RS",
        "name": "Bulgaria → Germany (via Serbia)",
        "origin_contains": ["sofia", "bulgaria", "varna", "plovdiv"],
        "dest_contains": ["munich", "berlin", "hamburg", "germany", "frankfurt", "cologne"],
        "borders": ["Kalotina", "Batrovci", "Nickelsdorf"],
        "warehouses": ["Sofia Hub"],
        "distance_km": 1550,
        "primary": True,
    },
    {
        "id": "BG_DE_RO",
        "name": "Bulgaria → Germany (via Romania)",
        "origin_contains": ["sofia", "bulgaria", "varna", "plovdiv"],
        "dest_contains": ["munich", "berlin", "hamburg", "germany", "frankfurt", "cologne"],
        "borders": ["Giurgiu", "Nadlac", "Nickelsdorf"],
        "warehouses": ["Sofia Hub", "Bucharest Hub"],
        "distance_km": 1750,
        "primary": False,
    },
    {
        "id": "RO_DE",
        "name": "Romania → Germany",
        "origin_contains": ["bucharest", "romania"],
        "dest_contains": ["munich", "berlin", "hamburg", "germany", "frankfurt", "cologne"],
        "borders": ["Nadlac", "Nickelsdorf"],
        "warehouses": ["Bucharest Hub"],
        "distance_km": 1900,
        "primary": True,
    },
    {
        "id": "RO_DE_VIA_BG",
        "name": "Romania → Germany (via Bulgaria-Serbia)",
        "origin_contains": ["bucharest", "romania"],
        "dest_contains": ["munich", "berlin", "hamburg", "germany", "frankfurt", "cologne"],
        "borders": ["Giurgiu", "Kalotina", "Batrovci", "Nickelsdorf"],
        "warehouses": ["Sofia Hub"],
        "distance_km": 2100,
        "primary": False,
    },
    {
        "id": "BG_AT",
        "name": "Bulgaria → Austria",
        "origin_contains": ["sofia", "bulgaria", "varna"],
        "dest_contains": ["vienna", "austria", "budapest", "hungary"],
        "borders": ["Kalotina", "Batrovci", "Nickelsdorf"],
        "warehouses": ["Sofia Hub"],
        "distance_km": 1200,
        "primary": True,
    },
    {
        "id": "TR_BG",
        "name": "Turkey → Bulgaria",
        "origin_contains": ["istanbul", "turkey"],
        "dest_contains": ["sofia", "bulgaria", "varna"],
        "borders": ["Kapitan Andreevo"],
        "warehouses": ["Sofia Hub"],
        "distance_km": 570,
        "primary": True,
    },
]


def _build_border_map(borders: List) -> Dict[str, Dict]:
    return {
        b.name: {
            "wait_time_min": float(b.wait_time_min),
            "status": b.status.value if hasattr(b.status, "value") else str(b.status),
            "inspection_rate": float(b.inspection_rate),
        }
        for b in borders
    }


def _build_warehouse_map(warehouses: List) -> Dict[str, Dict]:
    return {
        w.name: {
            "congestion_risk": float(w.congestion_risk),
            "queue_time_min": float(w.queue_time_min),
        }
        for w in warehouses
    }


def _find_border(keyword: str, border_map: Dict) -> tuple:
    """Partial name match. Returns (wait_min, full_name)."""
    for name, data in border_map.items():
        if keyword.lower() in name.lower():
            return data["wait_time_min"], name
    return 0.0, keyword


def _score_corridor(corridor: Dict, border_map: Dict, warehouse_map: Dict) -> Dict:
    """
    Score a corridor by total estimated transit time.
    Route selection is based on border wait times + driving distance only.
    Warehouse congestion is reported for visibility but does not affect the score
    since warehouses are delivery endpoints, not mandatory road stops.
    """
    border_delay = 0.0
    bottlenecks: List[str] = []
    border_breakdown: List[Dict] = []

    for kw in corridor["borders"]:
        wait, matched = _find_border(kw, border_map)
        border_delay += wait
        border_breakdown.append({"name": matched, "wait_min": round(wait)})
        if wait >= 60:
            bottlenecks.append(f"{matched}: {wait:.0f} min")

    # Warehouse congestion info — reported in bottlenecks for dispatcher visibility
    for wh_name in corridor.get("warehouses", []):
        wh = warehouse_map.get(wh_name)
        if wh and wh["congestion_risk"] > 0.65:
            bottlenecks.append(
                f"{wh_name}: {wh['congestion_risk'] * 100:.0f}% congested "
                f"({wh['queue_time_min']:.0f} min queue)"
            )

    drive_time = (corridor["distance_km"] / AVG_SPEED_KMH) * 60
    total_time = drive_time + border_delay

    return {
        "corridor_id": corridor["id"],
        "corridor_name": corridor["name"],
        "border_delay_min": round(border_delay, 1),
        "warehouse_delay_min": 0.0,
        "drive_time_min": round(drive_time, 1),
        "total_time_min": round(total_time, 1),
        "distance_km": corridor["distance_km"],
        "bottlenecks": bottlenecks,
        "border_breakdown": border_breakdown,
    }


def _detect_corridors(origin: str, destination: str) -> List[Dict]:
    origin_lc = origin.lower()
    dest_lc = destination.lower()
    return [
        c for c in CORRIDORS
        if any(kw in origin_lc for kw in c["origin_contains"])
        and any(kw in dest_lc for kw in c["dest_contains"])
    ]


@router.get("/recommendations")
def get_route_recommendations(db: Session = Depends(get_db)):
    """
    Route optimization recommendations for all active shipments.
    Scores each applicable corridor using live border + warehouse data
    and flags shipments where switching corridors saves >30 min.
    """
    borders = db.query(Border).all()
    warehouses = db.query(Warehouse).all()
    shipments = db.query(Shipment).filter(
        Shipment.status.in_([
            ShipmentStatusEnum.IN_TRANSIT,
            ShipmentStatusEnum.AT_BORDER,
            ShipmentStatusEnum.DELAYED,
        ])
    ).all()

    border_map = _build_border_map(borders)
    warehouse_map = _build_warehouse_map(warehouses)

    recommendations = []
    reroute_count = 0
    total_savings = 0.0
    bottleneck_hits: Dict[str, int] = {}

    for shipment in shipments:
        corridors = _detect_corridors(shipment.origin, shipment.destination)
        if not corridors:
            continue

        scored = [_score_corridor(c, border_map, warehouse_map) for c in corridors]

        primary = next((c for c in corridors if c.get("primary")), corridors[0])
        current_score = next(s for s in scored if s["corridor_id"] == primary["id"])
        best_score = min(scored, key=lambda x: x["total_time_min"])

        savings = current_score["total_time_min"] - best_score["total_time_min"]
        should_reroute = (
            best_score["corridor_id"] != current_score["corridor_id"]
            and savings > REROUTE_THRESHOLD_MIN
        )

        if should_reroute:
            reroute_count += 1
            total_savings += savings
            urgency = "CRITICAL" if savings > 90 else "HIGH" if savings > 45 else "MEDIUM"
        else:
            urgency = "LOW"

        # Track border-only bottlenecks (exclude warehouse congestion notes)
        for bn in current_score["bottlenecks"]:
            if "congested" not in bn:
                key = bn.split(":")[0].strip()
                bottleneck_hits[key] = bottleneck_hits.get(key, 0) + 1

        if should_reroute:
            reason = (
                f"Switch to {best_score['corridor_name']} — "
                f"saves ~{savings:.0f} min "
                f"({current_score['border_delay_min']:.0f} vs {best_score['border_delay_min']:.0f} min border delays)"
            )
        elif current_score["bottlenecks"]:
            reason = f"On optimal route. Active bottlenecks: {', '.join(current_score['bottlenecks'])}"
        else:
            reason = "Route is clear — no significant delays detected."

        priority_val = shipment.priority.value if hasattr(shipment.priority, "value") else str(shipment.priority)
        status_val = shipment.status.value if hasattr(shipment.status, "value") else str(shipment.status)

        recommendations.append({
            "shipment_id": shipment.shipment_id,
            "truck_id": shipment.truck_id,
            "origin": shipment.origin,
            "destination": shipment.destination,
            "priority": priority_val,
            "status": status_val,
            "current_route": current_score["corridor_name"],
            "recommended_route": best_score["corridor_name"],
            "should_reroute": should_reroute,
            "savings_minutes": round(savings, 1),
            "urgency": urgency,
            "current_total_time_min": current_score["total_time_min"],
            "recommended_total_time_min": best_score["total_time_min"],
            "current_border_delay_min": current_score["border_delay_min"],
            "recommended_border_delay_min": best_score["border_delay_min"],
            "bottlenecks": current_score["bottlenecks"],
            "border_breakdown": current_score["border_breakdown"],
            "reason": reason,
            "all_options": [
                {
                    "name": s["corridor_name"],
                    "total_time_min": s["total_time_min"],
                    "border_delay_min": s["border_delay_min"],
                    "distance_km": s["distance_km"],
                    "is_recommended": s["corridor_id"] == best_score["corridor_id"],
                }
                for s in sorted(scored, key=lambda x: x["total_time_min"])
            ],
        })

    recommendations.sort(key=lambda r: (-int(r["should_reroute"]), -r["savings_minutes"]))

    worst_bottleneck = None
    if bottleneck_hits:
        worst_key = max(bottleneck_hits, key=lambda k: bottleneck_hits[k])
        for name, data in border_map.items():
            if worst_key.lower() in name.lower():
                affected = bottleneck_hits[worst_key]
                worst_bottleneck = (
                    f"{name}: {data['wait_time_min']:.0f} min wait "
                    f"(affects {affected} shipment{'s' if affected != 1 else ''})"
                )
                break

    return {
        "recommendations": recommendations,
        "summary": {
            "total_analyzed": len(recommendations),
            "reroute_recommended": reroute_count,
            "total_savings_minutes": round(total_savings),
            "worst_bottleneck": worst_bottleneck,
        },
    }


@router.get("/corridors")
def list_corridors():
    """List all defined route corridors with their checkpoints."""
    return [
        {
            "id": c["id"],
            "name": c["name"],
            "borders": c["borders"],
            "warehouses": c.get("warehouses", []),
            "distance_km": c["distance_km"],
            "primary": c.get("primary", False),
        }
        for c in CORRIDORS
    ]
