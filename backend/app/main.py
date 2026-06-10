import asyncio
import json
import logging
import random
from datetime import datetime, timedelta
from typing import List

import redis as redis_lib
import redis.asyncio as aioredis
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.config import settings
from app.database import Base, SessionLocal, engine
from app.models import (
    Alert,
    AlertSeverityEnum,
    AlertTypeEnum,
    Border,
    BorderStatusEnum,
    PriorityEnum,
    Shipment,
    ShipmentStatusEnum,
    Truck,
    TruckStatusEnum,
    Warehouse,
)
from app.routers import analytics, borders, copilot, dispatcher, fleet, gps, routes, shipments, warehouse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Discordia AI Operations Platform",
    description="AI-augmented logistics platform for Discordia Transport",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(shipments.router, prefix="/api/v1/shipments", tags=["shipments"])
app.include_router(gps.router, prefix="/api/v1/gps", tags=["gps"])
app.include_router(warehouse.router, prefix="/api/v1/warehouse", tags=["warehouse"])
app.include_router(borders.router, prefix="/api/v1/borders", tags=["borders"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["analytics"])
app.include_router(copilot.router, prefix="/api/v1/copilot", tags=["copilot"])
app.include_router(routes.router, prefix="/api/v1/routes", tags=["routes"])
app.include_router(dispatcher.router, prefix="/api/v1/dispatcher", tags=["dispatcher"])
app.include_router(fleet.router, prefix="/api/v1/fleet", tags=["fleet"])


WAREHOUSES_SEED = [
    {
        "name": "Sofia Hub",
        "city": "Sofia",
        "country": "Bulgaria",
        "lat": 42.6977,
        "lon": 23.3219,
        "total_docks": 32,
        "available_docks": 12,
        "incoming_trucks": 8,
        "avg_unload_time_min": 55.0,
        "queue_time_min": 35.0,
        "congestion_risk": 0.62,
    },
    {
        "name": "Bucharest Hub",
        "city": "Bucharest",
        "country": "Romania",
        "lat": 44.4268,
        "lon": 26.1025,
        "total_docks": 28,
        "available_docks": 18,
        "incoming_trucks": 5,
        "avg_unload_time_min": 45.0,
        "queue_time_min": 20.0,
        "congestion_risk": 0.35,
    },
    {
        "name": "Istanbul Hub",
        "city": "Istanbul",
        "country": "Turkey",
        "lat": 41.0082,
        "lon": 28.9784,
        "total_docks": 48,
        "available_docks": 15,
        "incoming_trucks": 18,
        "avg_unload_time_min": 65.0,
        "queue_time_min": 90.0,
        "congestion_risk": 0.78,
    },
    {
        "name": "Munich Hub",
        "city": "Munich",
        "country": "Germany",
        "lat": 48.1351,
        "lon": 11.5820,
        "total_docks": 40,
        "available_docks": 22,
        "incoming_trucks": 10,
        "avg_unload_time_min": 40.0,
        "queue_time_min": 15.0,
        "congestion_risk": 0.28,
    },
    {
        "name": "Vienna Hub",
        "city": "Vienna",
        "country": "Austria",
        "lat": 48.2082,
        "lon": 16.3738,
        "total_docks": 36,
        "available_docks": 20,
        "incoming_trucks": 7,
        "avg_unload_time_min": 42.0,
        "queue_time_min": 18.0,
        "congestion_risk": 0.31,
    },
    {
        "name": "Budapest Hub",
        "city": "Budapest",
        "country": "Hungary",
        "lat": 47.4979,
        "lon": 19.0402,
        "total_docks": 24,
        "available_docks": 14,
        "incoming_trucks": 6,
        "avg_unload_time_min": 48.0,
        "queue_time_min": 25.0,
        "congestion_risk": 0.42,
    },
    {
        "name": "Belgrade Hub",
        "city": "Belgrade",
        "country": "Serbia",
        "lat": 44.7866,
        "lon": 20.4489,
        "total_docks": 20,
        "available_docks": 11,
        "incoming_trucks": 4,
        "avg_unload_time_min": 50.0,
        "queue_time_min": 30.0,
        "congestion_risk": 0.45,
    },
    {
        "name": "Varna Port",
        "city": "Varna",
        "country": "Bulgaria",
        "lat": 43.2141,
        "lon": 27.9147,
        "total_docks": 16,
        "available_docks": 8,
        "incoming_trucks": 3,
        "avg_unload_time_min": 70.0,
        "queue_time_min": 45.0,
        "congestion_risk": 0.55,
    },
]

BORDERS_SEED = [
    {
        "name": "Bulgaria-Romania (Giurgiu/Ruse)",
        "lat": 43.8561,
        "lon": 25.9697,
        "wait_time_min": 45.0,
        "inspection_rate": 0.12,
        "weather_risk": 0.05,
        "status": BorderStatusEnum.SLOW,
    },
    {
        "name": "Romania-Hungary (Nadlac)",
        "lat": 46.1667,
        "lon": 21.0833,
        "wait_time_min": 25.0,
        "inspection_rate": 0.08,
        "weather_risk": 0.03,
        "status": BorderStatusEnum.NORMAL,
    },
    {
        "name": "Bulgaria-Turkey (Kapitan Andreevo)",
        "lat": 41.7167,
        "lon": 26.3667,
        "wait_time_min": 120.0,
        "inspection_rate": 0.35,
        "weather_risk": 0.10,
        "status": BorderStatusEnum.CONGESTED,
    },
    {
        "name": "Bulgaria-Serbia (Kalotina)",
        "lat": 43.0500,
        "lon": 22.7167,
        "wait_time_min": 35.0,
        "inspection_rate": 0.15,
        "weather_risk": 0.02,
        "status": BorderStatusEnum.NORMAL,
    },
    {
        "name": "Serbia-Croatia (Batrovci)",
        "lat": 45.0500,
        "lon": 19.1333,
        "wait_time_min": 55.0,
        "inspection_rate": 0.20,
        "weather_risk": 0.04,
        "status": BorderStatusEnum.SLOW,
    },
    {
        "name": "Hungary-Austria (Nickelsdorf)",
        "lat": 47.9167,
        "lon": 17.0833,
        "wait_time_min": 15.0,
        "inspection_rate": 0.05,
        "weather_risk": 0.02,
        "status": BorderStatusEnum.NORMAL,
    },
    {
        "name": "Romania-Moldova (Albita)",
        "lat": 46.4333,
        "lon": 28.2167,
        "wait_time_min": 90.0,
        "inspection_rate": 0.40,
        "weather_risk": 0.08,
        "status": BorderStatusEnum.CONGESTED,
    },
    {
        "name": "Bulgaria-Greece (Kulata)",
        "lat": 41.3667,
        "lon": 23.3833,
        "wait_time_min": 30.0,
        "inspection_rate": 0.10,
        "weather_risk": 0.03,
        "status": BorderStatusEnum.NORMAL,
    },
]

ROUTE_CONFIGS = [
    {
        "origin": "Istanbul, Turkey",
        "destination": "Sofia, Bulgaria",
        "o_lat": 41.0082,
        "o_lon": 28.9784,
        "d_lat": 42.6977,
        "d_lon": 23.3219,
        "distance_km": 570,
    },
    {
        "origin": "Sofia, Bulgaria",
        "destination": "Munich, Germany",
        "o_lat": 42.6977,
        "o_lon": 23.3219,
        "d_lat": 48.1351,
        "d_lon": 11.5820,
        "distance_km": 1520,
    },
    {
        "origin": "Sofia, Bulgaria",
        "destination": "Vienna, Austria",
        "o_lat": 42.6977,
        "o_lon": 23.3219,
        "d_lat": 48.2082,
        "d_lon": 16.3738,
        "distance_km": 1200,
    },
    {
        "origin": "Bucharest, Romania",
        "destination": "Berlin, Germany",
        "o_lat": 44.4268,
        "o_lon": 26.1025,
        "d_lat": 52.5200,
        "d_lon": 13.4050,
        "distance_km": 1850,
    },
    {
        "origin": "Istanbul, Turkey",
        "destination": "Munich, Germany",
        "o_lat": 41.0082,
        "o_lon": 28.9784,
        "d_lat": 48.1351,
        "d_lon": 11.5820,
        "distance_km": 2080,
    },
    {
        "origin": "Varna, Bulgaria",
        "destination": "Hamburg, Germany",
        "o_lat": 43.2141,
        "o_lon": 27.9147,
        "d_lat": 53.5753,
        "d_lon": 10.0153,
        "distance_km": 2100,
    },
    {
        "origin": "Sofia, Bulgaria",
        "destination": "Amsterdam, Netherlands",
        "o_lat": 42.6977,
        "o_lon": 23.3219,
        "d_lat": 52.3676,
        "d_lon": 4.9041,
        "distance_km": 2050,
    },
    {
        "origin": "Bucharest, Romania",
        "destination": "Paris, France",
        "o_lat": 44.4268,
        "o_lon": 26.1025,
        "d_lat": 48.8566,
        "d_lon": 2.3522,
        "distance_km": 2200,
    },
    {
        "origin": "Istanbul, Turkey",
        "destination": "Vienna, Austria",
        "o_lat": 41.0082,
        "o_lon": 28.9784,
        "d_lat": 48.2082,
        "d_lon": 16.3738,
        "distance_km": 1800,
    },
    {
        "origin": "Sofia, Bulgaria",
        "destination": "Budapest, Hungary",
        "o_lat": 42.6977,
        "o_lon": 23.3219,
        "d_lat": 47.4979,
        "d_lon": 19.0402,
        "distance_km": 850,
    },
]

CARRIERS = [
    "Discordia",
    "Willi Betz",
    "Schenker",
    "DHL Freight",
    "DB Schenker",
    "Kuehne+Nagel",
    "Ekol",
]

TRUCK_COORDS = [
    (42.6977, 23.3219),
    (41.7167, 26.3667),
    (43.8561, 25.9697),
    (44.4268, 26.1025),
    (46.1667, 21.0833),
    (47.4979, 19.0402),
    (48.2082, 16.3738),
    (48.1351, 11.5820),
    (44.7866, 20.4489),
    (41.0082, 28.9784),
    (43.2141, 27.9147),
    (45.0500, 19.1333),
    (47.9167, 17.0833),
    (52.5200, 13.4050),
    (53.5753, 10.0153),
    (52.3676, 4.9041),
    (48.8566, 2.3522),
    (42.0000, 27.5000),
    (43.5000, 24.5000),
    (45.5000, 22.0000),
]


def seed_database(db: Session):
    try:
        count = db.query(Shipment).count()
        if count > 0:
            logger.info(f"Database already seeded ({count} shipments), skipping.")
            return
    except Exception as e:
        logger.error(f"Error checking seed status: {e}")
        return

    logger.info("Seeding database with initial data...")

    for w_data in WAREHOUSES_SEED:
        warehouse = Warehouse(**w_data)
        db.add(warehouse)

    for b_data in BORDERS_SEED:
        border = Border(**b_data)
        db.add(border)

    db.flush()

    trucks = []
    for i in range(1, 51):
        coord_idx = (i - 1) % len(TRUCK_COORDS)
        base_lat, base_lon = TRUCK_COORDS[coord_idx]
        lat = base_lat + random.uniform(-0.5, 0.5)
        lon = base_lon + random.uniform(-0.5, 0.5)
        status = random.choice(
            [TruckStatusEnum.MOVING, TruckStatusEnum.MOVING, TruckStatusEnum.IDLE, TruckStatusEnum.AT_BORDER]
        )
        speed = random.uniform(65, 90) if status == TruckStatusEnum.MOVING else 0.0
        truck = Truck(
            truck_id=f"BGN-{1000 + i}",
            lat=lat,
            lon=lon,
            speed_kmh=speed,
            heading=random.uniform(0, 360),
            status=status,
            last_updated=datetime.utcnow(),
        )
        db.add(truck)
        trucks.append(truck)

    db.flush()

    truck_list = db.query(Truck).all()

    priorities = [
        PriorityEnum.LOW,
        PriorityEnum.MEDIUM,
        PriorityEnum.MEDIUM,
        PriorityEnum.HIGH,
        PriorityEnum.CRITICAL,
    ]
    statuses = [
        ShipmentStatusEnum.IN_TRANSIT,
        ShipmentStatusEnum.IN_TRANSIT,
        ShipmentStatusEnum.IN_TRANSIT,
        ShipmentStatusEnum.AT_BORDER,
        ShipmentStatusEnum.DELAYED,
        ShipmentStatusEnum.AT_WAREHOUSE,
    ]

    now = datetime.utcnow()

    for i in range(1, 31):
        route = ROUTE_CONFIGS[(i - 1) % len(ROUTE_CONFIGS)]
        carrier = CARRIERS[(i - 1) % len(CARRIERS)]
        priority = priorities[(i - 1) % len(priorities)]
        status = statuses[(i - 1) % len(statuses)]

        hours_ahead = random.randint(4, 72)
        eta = now + timedelta(hours=hours_ahead)

        is_delayed = status == ShipmentStatusEnum.DELAYED
        delay_min = random.randint(60, 360) if is_delayed else None
        risk = random.uniform(0.6, 0.95) if is_delayed else random.uniform(0.1, 0.55)

        truck = truck_list[(i - 1) % len(truck_list)] if truck_list else None

        shipment = Shipment(
            shipment_id=f"DIS-2024-{10000 + i}",
            origin=route["origin"],
            destination=route["destination"],
            origin_lat=route["o_lat"],
            origin_lon=route["o_lon"],
            dest_lat=route["d_lat"],
            dest_lon=route["d_lon"],
            distance_km=route["distance_km"] + random.uniform(-50, 50),
            carrier=carrier,
            priority=priority,
            status=status,
            eta=eta,
            delay_minutes=delay_min,
            risk_score=risk,
            truck_id=truck.truck_id if truck else None,
            created_at=now - timedelta(hours=random.randint(1, 48)),
            updated_at=now,
        )
        db.add(shipment)

    alert_templates = [
        (
            AlertTypeEnum.BORDER,
            AlertSeverityEnum.CRITICAL,
            "Bulgaria-Turkey border (Kapitan Andreevo) congestion: 2h+ wait time. 6 trucks affected.",
            None,
        ),
        (
            AlertTypeEnum.DELAY,
            AlertSeverityEnum.WARNING,
            "DIS-2024-10005 delayed by 180 min due to border inspection. SLA at risk.",
            "DIS-2024-10005",
        ),
        (
            AlertTypeEnum.CONGESTION,
            AlertSeverityEnum.WARNING,
            "Istanbul Hub at 78% capacity. Recommend rerouting 3 incoming trucks to Varna Port.",
            None,
        ),
        (
            AlertTypeEnum.SLA_RISK,
            AlertSeverityEnum.CRITICAL,
            "DIS-2024-10011 (CRITICAL priority) at risk of missing SLA window. Current delay: 4h.",
            "DIS-2024-10011",
        ),
        (
            AlertTypeEnum.ROUTE,
            AlertSeverityEnum.INFO,
            "Alternative route via Vidin bridge available. Estimated 45 min faster than Ruse crossing.",
            None,
        ),
        (
            AlertTypeEnum.ANOMALY,
            AlertSeverityEnum.WARNING,
            "Truck BGN-1023 stationary for 3h at unauthorized location near Plovdiv.",
            None,
        ),
        (
            AlertTypeEnum.BORDER,
            AlertSeverityEnum.WARNING,
            "Romania-Moldova (Albita) border reporting 90 min delays. Heavy customs inspection.",
            None,
        ),
        (
            AlertTypeEnum.DELAY,
            AlertSeverityEnum.INFO,
            "DIS-2024-10018 arrived Sofia Hub. Unloading in progress.",
            "DIS-2024-10018",
        ),
    ]

    for i, (atype, severity, message, ship_id) in enumerate(alert_templates):
        alert = Alert(
            alert_type=atype,
            severity=severity,
            message=message,
            shipment_id=ship_id,
            is_read=False,
            created_at=now - timedelta(minutes=random.randint(1, 120)),
        )
        db.add(alert)

    db.commit()
    logger.info("Database seeded successfully.")


@app.on_event("startup")
async def startup_event():
    logger.info("Starting Discordia AI Operations Platform...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()
    logger.info("Platform ready.")


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "Discordia AI Operations Platform"}


@app.get("/")
def root():
    return {
        "service": "Discordia AI Operations Platform",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    r = None
    pubsub = None
    try:
        r = aioredis.from_url(settings.redis_url, decode_responses=True)
        pubsub = r.pubsub()
        await pubsub.subscribe("live_events")
        await websocket.send_json({"type": "connected", "message": "Subscribed to live events"})

        last_ping = asyncio.get_event_loop().time()
        PING_INTERVAL = 25  # seconds — keeps connection alive through proxies/browser timeouts

        while True:
            # Non-blocking message poll
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=0.05)
            if message and message["type"] == "message":
                try:
                    data = json.loads(message["data"])
                    await websocket.send_json(data)
                except Exception:
                    pass

            # Periodic ping so the browser never sees a silent idle connection
            now = asyncio.get_event_loop().time()
            if now - last_ping >= PING_INTERVAL:
                await websocket.send_json({"type": "ping"})
                last_ping = now

            await asyncio.sleep(0.05)

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        try:
            if pubsub:
                await pubsub.unsubscribe()
                await pubsub.aclose()
            if r:
                await r.aclose()
        except Exception:
            pass


@app.post("/api/v1/simulator/seed")
def simulator_seed():
    db = SessionLocal()
    try:
        seed_database(db)
        count = db.query(Shipment).count()
        return {"status": "ok", "shipments": count}
    finally:
        db.close()


@app.post("/api/v1/trucks/bulk-update")
def bulk_update_trucks(updates: List[dict]):
    from app.models import Truck

    db = SessionLocal()
    try:
        updated = 0
        for u in updates:
            truck = db.query(Truck).filter(Truck.truck_id == u.get("truck_id")).first()
            if truck:
                truck.lat = u.get("lat", truck.lat)
                truck.lon = u.get("lon", truck.lon)
                truck.speed_kmh = u.get("speed_kmh", truck.speed_kmh)
                truck.heading = u.get("heading", truck.heading)
                if "status" in u:
                    try:
                        truck.status = TruckStatusEnum(u["status"])
                    except ValueError:
                        pass
                truck.last_updated = datetime.utcnow()
                updated += 1
        db.commit()

        try:
            r = redis_lib.Redis.from_url(settings.redis_url, decode_responses=True)
            r.publish("live_events", json.dumps({"type": "gps_update", "count": updated}))
            r.close()
        except Exception:
            pass

        return {"updated": updated}
    finally:
        db.close()
