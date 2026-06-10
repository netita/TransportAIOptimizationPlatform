import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    Integer,
    String,
    func,
)

from app.database import Base


class PriorityEnum(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ShipmentStatusEnum(str, enum.Enum):
    PENDING = "PENDING"
    IN_TRANSIT = "IN_TRANSIT"
    AT_BORDER = "AT_BORDER"
    AT_WAREHOUSE = "AT_WAREHOUSE"
    DELIVERED = "DELIVERED"
    DELAYED = "DELAYED"


class TruckStatusEnum(str, enum.Enum):
    MOVING = "MOVING"
    IDLE = "IDLE"
    AT_WAREHOUSE = "AT_WAREHOUSE"
    AT_BORDER = "AT_BORDER"
    OFFLINE = "OFFLINE"


class BorderStatusEnum(str, enum.Enum):
    NORMAL = "NORMAL"
    SLOW = "SLOW"
    CONGESTED = "CONGESTED"
    CLOSED = "CLOSED"


class AlertTypeEnum(str, enum.Enum):
    DELAY = "DELAY"
    CONGESTION = "CONGESTION"
    BORDER = "BORDER"
    ANOMALY = "ANOMALY"
    SLA_RISK = "SLA_RISK"
    ROUTE = "ROUTE"


class AlertSeverityEnum(str, enum.Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class Shipment(Base):
    __tablename__ = "shipments"

    id = Column(Integer, primary_key=True, index=True)
    shipment_id = Column(String, unique=True, index=True, nullable=False)
    origin = Column(String, nullable=False)
    destination = Column(String, nullable=False)
    origin_lat = Column(Float, nullable=False)
    origin_lon = Column(Float, nullable=False)
    dest_lat = Column(Float, nullable=False)
    dest_lon = Column(Float, nullable=False)
    distance_km = Column(Float, nullable=False, default=0.0)
    carrier = Column(String, nullable=False)
    priority = Column(Enum(PriorityEnum), nullable=False, default=PriorityEnum.MEDIUM)
    status = Column(
        Enum(ShipmentStatusEnum),
        nullable=False,
        default=ShipmentStatusEnum.IN_TRANSIT,
    )
    eta = Column(DateTime, nullable=False)
    actual_arrival = Column(DateTime, nullable=True)
    delay_minutes = Column(Integer, nullable=True)
    risk_score = Column(Float, nullable=False, default=0.0)
    truck_id = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class Truck(Base):
    __tablename__ = "trucks"

    id = Column(Integer, primary_key=True, index=True)
    truck_id = Column(String, unique=True, index=True, nullable=False)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    speed_kmh = Column(Float, nullable=False, default=0.0)
    heading = Column(Float, nullable=False, default=0.0)
    status = Column(
        Enum(TruckStatusEnum), nullable=False, default=TruckStatusEnum.IDLE
    )
    current_shipment_id = Column(String, nullable=True)
    last_updated = Column(DateTime, nullable=False, default=datetime.utcnow)


class Warehouse(Base):
    __tablename__ = "warehouses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    city = Column(String, nullable=False)
    country = Column(String, nullable=False)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    total_docks = Column(Integer, nullable=False, default=20)
    available_docks = Column(Integer, nullable=False, default=10)
    incoming_trucks = Column(Integer, nullable=False, default=0)
    avg_unload_time_min = Column(Float, nullable=False, default=45.0)
    queue_time_min = Column(Float, nullable=False, default=0.0)
    congestion_risk = Column(Float, nullable=False, default=0.0)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class Border(Base):
    __tablename__ = "borders"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    wait_time_min = Column(Float, nullable=False, default=30.0)
    inspection_rate = Column(Float, nullable=False, default=0.1)
    weather_risk = Column(Float, nullable=False, default=0.0)
    status = Column(
        Enum(BorderStatusEnum), nullable=False, default=BorderStatusEnum.NORMAL
    )
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    alert_type = Column(Enum(AlertTypeEnum), nullable=False)
    severity = Column(Enum(AlertSeverityEnum), nullable=False)
    message = Column(String, nullable=False)
    shipment_id = Column(String, nullable=True)
    truck_id = Column(String, nullable=True)
    is_read = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
