import logging
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Warehouse
from app.schemas import WarehouseRead, WarehouseUpdate

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=List[WarehouseRead])
def list_warehouses(db: Session = Depends(get_db)):
    try:
        return db.query(Warehouse).all()
    except Exception as e:
        logger.error(f"Error fetching warehouses: {e}")
        return []


@router.get("/{warehouse_id}", response_model=WarehouseRead)
def get_warehouse(warehouse_id: int, db: Session = Depends(get_db)):
    warehouse = db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    return warehouse


@router.put("/{warehouse_id}", response_model=WarehouseRead)
def update_warehouse(
    warehouse_id: int,
    update: WarehouseUpdate,
    db: Session = Depends(get_db),
):
    warehouse = db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")

    if update.available_docks is not None:
        warehouse.available_docks = update.available_docks
    if update.incoming_trucks is not None:
        warehouse.incoming_trucks = update.incoming_trucks
    if update.avg_unload_time_min is not None:
        warehouse.avg_unload_time_min = update.avg_unload_time_min
    if update.queue_time_min is not None:
        warehouse.queue_time_min = update.queue_time_min
    if update.congestion_risk is not None:
        warehouse.congestion_risk = max(0.0, min(1.0, update.congestion_risk))

    warehouse.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(warehouse)
    return warehouse
