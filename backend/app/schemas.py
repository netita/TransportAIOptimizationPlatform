from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from app.models import (
    AlertSeverityEnum,
    AlertTypeEnum,
    BorderStatusEnum,
    PriorityEnum,
    ShipmentStatusEnum,
    TruckStatusEnum,
)


class ShipmentBase(BaseModel):
    shipment_id: str
    origin: str
    destination: str
    origin_lat: float
    origin_lon: float
    dest_lat: float
    dest_lon: float
    distance_km: float
    carrier: str
    priority: PriorityEnum
    status: ShipmentStatusEnum
    eta: datetime
    actual_arrival: Optional[datetime] = None
    delay_minutes: Optional[int] = None
    risk_score: float
    truck_id: Optional[str] = None


class ShipmentCreate(ShipmentBase):
    pass


class ShipmentRead(ShipmentBase):
    id: int
    created_at: datetime
    updated_at: datetime
    predicted_delay_minutes: Optional[float] = None
    delay_probability: Optional[float] = None
    prediction_confidence: Optional[float] = None
    top_factors: Optional[list] = None

    class Config:
        from_attributes = True


class ShipmentListResponse(BaseModel):
    items: List[ShipmentRead]
    total: int


class ModelMetrics(BaseModel):
    mae: float
    rmse: float
    accuracy: float
    auc: float
    total_samples: int
    trained_at: str
    model_version: str


class TruckRead(BaseModel):
    id: int
    truck_id: str
    lat: float
    lon: float
    speed_kmh: float
    heading: float
    status: TruckStatusEnum
    current_shipment_id: Optional[str] = None
    last_updated: datetime

    class Config:
        from_attributes = True


class TruckUpdate(BaseModel):
    truck_id: str
    lat: float
    lon: float
    speed_kmh: float
    heading: float
    status: TruckStatusEnum
    current_shipment_id: Optional[str] = None


class WarehouseRead(BaseModel):
    id: int
    name: str
    city: str
    country: str
    lat: float
    lon: float
    total_docks: int
    available_docks: int
    incoming_trucks: int
    avg_unload_time_min: float
    queue_time_min: float
    congestion_risk: float
    updated_at: datetime

    class Config:
        from_attributes = True


class WarehouseUpdate(BaseModel):
    available_docks: Optional[int] = None
    incoming_trucks: Optional[int] = None
    avg_unload_time_min: Optional[float] = None
    queue_time_min: Optional[float] = None
    congestion_risk: Optional[float] = None


class BorderRead(BaseModel):
    id: int
    name: str
    lat: float
    lon: float
    wait_time_min: float
    inspection_rate: float
    weather_risk: float
    status: BorderStatusEnum
    updated_at: datetime

    class Config:
        from_attributes = True


class BorderUpdate(BaseModel):
    wait_time_min: Optional[float] = None
    inspection_rate: Optional[float] = None
    weather_risk: Optional[float] = None
    status: Optional[BorderStatusEnum] = None


class AlertRead(BaseModel):
    id: int
    alert_type: AlertTypeEnum
    severity: AlertSeverityEnum
    message: str
    shipment_id: Optional[str] = None
    truck_id: Optional[str] = None
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


class KPIDashboard(BaseModel):
    active_shipments: int
    delayed_count: int
    at_risk_count: int
    trucks_online: int
    border_alerts: int
    on_time_rate: float
    avg_delay_minutes: float


class CopilotMessage(BaseModel):
    role: str
    content: str


class CopilotRequest(BaseModel):
    message: str
    history: List[CopilotMessage] = []


class CopilotResponse(BaseModel):
    response: str
    model: str


class ShipmentStatusUpdate(BaseModel):
    status: ShipmentStatusEnum
    delay_minutes: Optional[int] = None
    risk_score: Optional[float] = None


class TimelinePoint(BaseModel):
    hour: str
    created: int
    delivered: int
    delayed: int


class CongestionData(BaseModel):
    name: str
    city: str
    congestion_risk: float
    queue_time_min: float
    available_docks: int
    total_docks: int
