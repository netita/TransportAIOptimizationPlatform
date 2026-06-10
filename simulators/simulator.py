"""
Discordia Transport AI Platform - Live Data Simulator
Simulates GPS updates, warehouse congestion, border wait times,
shipment delays, and alerts via the REST API.
"""

import asyncio
import logging
import math
import os
import random
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import httpx
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [SIMULATOR] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

ROUTES: List[Dict[str, Any]] = [
    {
        "name": "Sofia-Istanbul",
        "waypoints": [
            (42.6977, 23.3219),
            (42.2000, 24.5000),
            (41.9000, 25.8000),
            (41.7167, 26.3667),
            (41.4000, 27.5000),
            (41.0082, 28.9784),
        ],
    },
    {
        "name": "Sofia-Vienna",
        "waypoints": [
            (42.6977, 23.3219),
            (43.2000, 22.5000),
            (44.7866, 20.4489),
            (45.3000, 19.5000),
            (46.5000, 18.5000),
            (47.4979, 19.0402),
            (47.9167, 17.0833),
            (48.2082, 16.3738),
        ],
    },
    {
        "name": "Sofia-Munich",
        "waypoints": [
            (42.6977, 23.3219),
            (43.8561, 25.9697),
            (44.4268, 26.1025),
            (46.1667, 21.0833),
            (47.4979, 19.0402),
            (47.9167, 17.0833),
            (48.2082, 16.3738),
            (48.1351, 11.5820),
        ],
    },
    {
        "name": "Bucharest-Berlin",
        "waypoints": [
            (44.4268, 26.1025),
            (46.1667, 21.0833),
            (47.4979, 19.0402),
            (48.5000, 17.5000),
            (50.0755, 14.4378),
            (51.1079, 13.4000),
            (52.5200, 13.4050),
        ],
    },
    {
        "name": "Istanbul-Munich",
        "waypoints": [
            (41.0082, 28.9784),
            (41.7167, 26.3667),
            (42.6977, 23.3219),
            (43.8561, 25.9697),
            (44.4268, 26.1025),
            (46.1667, 21.0833),
            (47.9167, 17.0833),
            (48.2082, 16.3738),
            (48.1351, 11.5820),
        ],
    },
]


class TruckSimulator:
    def __init__(self, truck_id: str):
        self.truck_id = truck_id
        route_def = random.choice(ROUTES)
        self.waypoints = route_def["waypoints"]
        self.route_name = route_def["name"]
        self.current_waypoint_idx = random.randint(0, len(self.waypoints) - 2)
        self.progress = random.uniform(0.0, 1.0)
        self.speed_kmh = random.uniform(70.0, 90.0)
        self.status = "MOVING"

    def get_position(self) -> Tuple[float, float]:
        wp_a = self.waypoints[self.current_waypoint_idx]
        wp_b = self.waypoints[
            min(self.current_waypoint_idx + 1, len(self.waypoints) - 1)
        ]
        lat = wp_a[0] + (wp_b[0] - wp_a[0]) * self.progress
        lon = wp_a[1] + (wp_b[1] - wp_a[1]) * self.progress
        return lat, lon

    def get_heading(self) -> float:
        wp_a = self.waypoints[self.current_waypoint_idx]
        wp_b = self.waypoints[
            min(self.current_waypoint_idx + 1, len(self.waypoints) - 1)
        ]
        dlat = wp_b[0] - wp_a[0]
        dlon = wp_b[1] - wp_a[1]
        heading = math.degrees(math.atan2(dlon, dlat)) % 360
        return heading

    def advance(self, dt_seconds: float = 5.0):
        if random.random() < 0.02:
            self.status = "IDLE"
            self.speed_kmh = 0.0
            return
        self.status = "MOVING"
        self.speed_kmh = random.uniform(68.0, 92.0)
        distance_km = (self.speed_kmh * dt_seconds) / 3600.0
        wp_a = self.waypoints[self.current_waypoint_idx]
        wp_b = self.waypoints[
            min(self.current_waypoint_idx + 1, len(self.waypoints) - 1)
        ]
        seg_lat = wp_b[0] - wp_a[0]
        seg_lon = wp_b[1] - wp_a[1]
        seg_km = math.sqrt(seg_lat**2 + seg_lon**2) * 111.0
        if seg_km > 0:
            progress_increment = distance_km / seg_km
        else:
            progress_increment = 0.1
        self.progress += progress_increment
        if self.progress >= 1.0:
            self.progress = 0.0
            self.current_waypoint_idx += 1
            if self.current_waypoint_idx >= len(self.waypoints) - 1:
                self.current_waypoint_idx = 0
                route_def = random.choice(ROUTES)
                self.waypoints = route_def["waypoints"]
                self.route_name = route_def["name"]


_truck_simulators: Dict[str, TruckSimulator] = {}
_truck_ids: List[str] = []
_initialized = False


async def wait_for_backend(max_retries: int = 30, delay: float = 5.0):
    logger.info(f"Waiting for backend at {BACKEND_URL}...")
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{BACKEND_URL}/health")
                if resp.status_code == 200:
                    logger.info("Backend is ready.")
                    return True
        except Exception:
            pass
        logger.info(f"Backend not ready (attempt {attempt + 1}/{max_retries}), retrying in {delay}s...")
        await asyncio.sleep(delay)
    logger.error("Backend never became ready.")
    return False


async def initialize():
    global _truck_ids, _initialized
    logger.info("Initializing simulator...")
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(f"{BACKEND_URL}/api/v1/simulator/seed")
            if resp.status_code == 200:
                logger.info(f"Seed result: {resp.json()}")
    except Exception as e:
        logger.warning(f"Seed call failed (may already be seeded): {e}")

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{BACKEND_URL}/api/v1/gps/live")
            if resp.status_code == 200:
                trucks = resp.json()
                _truck_ids = [t["truck_id"] for t in trucks]
                logger.info(f"Loaded {len(_truck_ids)} trucks for simulation.")
                for truck in trucks:
                    sim = TruckSimulator(truck["truck_id"])
                    sim.progress = random.uniform(0.0, 1.0)
                    _truck_simulators[truck["truck_id"]] = sim
    except Exception as e:
        logger.error(f"Failed to load trucks: {e}")
        _truck_ids = [f"BGN-{1000 + i}" for i in range(1, 51)]
        for tid in _truck_ids:
            _truck_simulators[tid] = TruckSimulator(tid)

    _initialized = True
    logger.info("Simulator initialized.")


async def update_gps():
    if not _truck_ids:
        return
    sample = random.sample(_truck_ids, min(10, len(_truck_ids)))
    updates = []
    for tid in sample:
        sim = _truck_simulators.get(tid)
        if not sim:
            sim = TruckSimulator(tid)
            _truck_simulators[tid] = sim
        sim.advance(5.0)
        lat, lon = sim.get_position()
        lat += random.uniform(-0.001, 0.001)
        lon += random.uniform(-0.001, 0.001)
        updates.append(
            {
                "truck_id": tid,
                "lat": round(lat, 5),
                "lon": round(lon, 5),
                "speed_kmh": round(sim.speed_kmh, 1),
                "heading": round(sim.get_heading(), 1),
                "status": sim.status,
            }
        )
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{BACKEND_URL}/api/v1/trucks/bulk-update", json=updates
            )
            if resp.status_code == 200:
                logger.debug(f"GPS updated {len(updates)} trucks")
            else:
                logger.warning(f"GPS update failed: {resp.status_code}")
    except Exception as e:
        logger.warning(f"GPS update error: {e}")


async def update_warehouses():
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{BACKEND_URL}/api/v1/warehouse/")
            if resp.status_code != 200:
                return
            warehouses = resp.json()

        for wh in warehouses:
            new_congestion = max(0.0, min(1.0, wh["congestion_risk"] + random.uniform(-0.08, 0.10)))
            docks_delta = random.randint(-2, 2)
            new_available = max(0, min(wh["total_docks"], wh["available_docks"] + docks_delta))
            new_queue = max(0.0, wh["queue_time_min"] + random.uniform(-10.0, 15.0))
            new_incoming = max(0, wh["incoming_trucks"] + random.randint(-1, 2))
            update_data = {
                "congestion_risk": round(new_congestion, 3),
                "available_docks": new_available,
                "queue_time_min": round(new_queue, 1),
                "incoming_trucks": new_incoming,
            }
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.put(
                    f"{BACKEND_URL}/api/v1/warehouse/{wh['id']}", json=update_data
                )
        logger.debug(f"Updated {len(warehouses)} warehouses")
    except Exception as e:
        logger.warning(f"Warehouse update error: {e}")


async def update_borders():
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{BACKEND_URL}/api/v1/borders/")
            if resp.status_code != 200:
                return
            borders = resp.json()

        for border in borders:
            wait_delta = random.uniform(-15.0, 20.0)
            new_wait = max(5.0, border["wait_time_min"] + wait_delta)
            new_weather = max(0.0, min(1.0, border["weather_risk"] + random.uniform(-0.03, 0.05)))

            if new_wait < 30:
                new_status = "NORMAL"
            elif new_wait < 60:
                new_status = "SLOW"
            elif new_wait < 120:
                new_status = "CONGESTED"
            else:
                new_status = "CONGESTED"

            if random.random() < 0.01:
                new_status = "CLOSED"
                new_wait = 999.0

            update_data = {
                "wait_time_min": round(new_wait, 1),
                "weather_risk": round(new_weather, 3),
                "status": new_status,
            }
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.put(
                    f"{BACKEND_URL}/api/v1/borders/{border['id']}", json=update_data
                )
        logger.debug(f"Updated {len(borders)} borders")
    except Exception as e:
        logger.warning(f"Border update error: {e}")


DELAY_REASONS = [
    "Border inspection causing significant delay",
    "Traffic congestion on E80 motorway",
    "Weather conditions affecting route",
    "Mechanical issue requiring roadside assistance",
    "Customs documentation processing",
    "Ferry connection delay at port",
    "Road works on primary route",
    "Driver rest period (mandatory)",
]


async def update_shipment_delays():
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{BACKEND_URL}/api/v1/shipments/?limit=30")
            if resp.status_code != 200:
                return
            data = resp.json()
            shipments = data.get("items", [])

        for shipment in shipments:
            if random.random() < 0.05:
                if shipment["status"] in ("IN_TRANSIT", "AT_BORDER"):
                    new_delay = random.randint(30, 240)
                    new_risk = min(1.0, shipment["risk_score"] + random.uniform(0.1, 0.3))
                    update_data = {
                        "status": "DELAYED",
                        "delay_minutes": new_delay,
                        "risk_score": round(new_risk, 3),
                    }
                    async with httpx.AsyncClient(timeout=5.0) as client:
                        await client.put(
                            f"{BACKEND_URL}/api/v1/shipments/{shipment['shipment_id']}/status",
                            json=update_data,
                        )
                    logger.info(
                        f"Shipment {shipment['shipment_id']} delayed by {new_delay} min"
                    )
                elif shipment["status"] == "DELAYED":
                    if random.random() < 0.3:
                        new_risk = max(0.1, shipment["risk_score"] - random.uniform(0.1, 0.2))
                        update_data = {
                            "status": "IN_TRANSIT",
                            "delay_minutes": shipment.get("delay_minutes"),
                            "risk_score": round(new_risk, 3),
                        }
                        async with httpx.AsyncClient(timeout=5.0) as client:
                            await client.put(
                                f"{BACKEND_URL}/api/v1/shipments/{shipment['shipment_id']}/status",
                                json=update_data,
                            )
                        logger.info(
                            f"Shipment {shipment['shipment_id']} resumed transit"
                        )
    except Exception as e:
        logger.warning(f"Shipment delay update error: {e}")


ALERT_TEMPLATES = [
    {
        "alert_type": "BORDER",
        "severity": "WARNING",
        "message": "Bulgaria-Turkey border queue increasing. Current wait: {wait}min. Consider Vidin alternative.",
    },
    {
        "alert_type": "CONGESTION",
        "severity": "WARNING",
        "message": "Sofia Hub approaching capacity ({pct}% utilization). Recommend holding 2 inbound trucks.",
    },
    {
        "alert_type": "DELAY",
        "severity": "CRITICAL",
        "message": "SLA breach imminent for CRITICAL priority shipment. Escalation required.",
    },
    {
        "alert_type": "ROUTE",
        "severity": "INFO",
        "message": "AI recommends route change: E79 via Vidin saves estimated 52 minutes vs E80 today.",
    },
    {
        "alert_type": "ANOMALY",
        "severity": "WARNING",
        "message": "Truck stationary >2h in non-standard location. Manual check recommended.",
    },
    {
        "alert_type": "BORDER",
        "severity": "CRITICAL",
        "message": "Romania-Moldova border closed for maintenance. All traffic diverted. ETA impact: +3h.",
    },
    {
        "alert_type": "SLA_RISK",
        "severity": "WARNING",
        "message": "3 shipments approaching SLA deadline in next 4 hours. Review and prioritize.",
    },
]


async def generate_alert():
    template = random.choice(ALERT_TEMPLATES)
    message = template["message"].format(
        wait=random.randint(60, 150),
        pct=random.randint(75, 95),
    )
    alert_data = {
        "alert_type": template["alert_type"],
        "severity": template["severity"],
        "message": message,
        "shipment_id": None,
        "truck_id": None,
        "is_read": False,
        "created_at": datetime.utcnow().isoformat(),
    }

    try:
        import httpx as _httpx
        from app.database import SessionLocal
        from app.models import Alert, AlertSeverityEnum, AlertTypeEnum

        db = SessionLocal()
        try:
            alert = Alert(
                alert_type=AlertTypeEnum(template["alert_type"]),
                severity=AlertSeverityEnum(template["severity"]),
                message=message,
                is_read=False,
                created_at=datetime.utcnow(),
            )
            db.add(alert)
            db.commit()
            logger.info(f"Alert created: [{template['severity']}] {message[:60]}...")
        finally:
            db.close()
    except ImportError:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(
                    f"{BACKEND_URL}/api/v1/analytics/alerts/create",
                    json=alert_data,
                )
        except Exception as e:
            logger.debug(f"Alert creation via API failed: {e}")
    except Exception as e:
        logger.debug(f"Alert creation failed: {e}")


async def gps_loop():
    while True:
        await update_gps()
        await asyncio.sleep(5)


async def warehouse_loop():
    while True:
        await asyncio.sleep(30)
        await update_warehouses()


async def border_loop():
    while True:
        await asyncio.sleep(60)
        await update_borders()


async def delay_loop():
    while True:
        await asyncio.sleep(120)
        await update_shipment_delays()


async def alert_loop():
    while True:
        await asyncio.sleep(180)
        await generate_alert()


async def main():
    logger.info("Discordia Transport Simulator starting...")
    ready = await wait_for_backend(max_retries=40, delay=5.0)
    if not ready:
        logger.error("Backend not reachable. Exiting.")
        return

    await initialize()

    logger.info("Starting simulation loops...")
    await asyncio.gather(
        gps_loop(),
        warehouse_loop(),
        border_loop(),
        delay_loop(),
        alert_loop(),
    )


if __name__ == "__main__":
    asyncio.run(main())
