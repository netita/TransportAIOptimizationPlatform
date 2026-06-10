import logging
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Truck, TruckStatusEnum
from app.schemas import TruckRead, TruckUpdate

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/live", response_model=List[TruckRead])
def get_live_trucks(db: Session = Depends(get_db)):
    try:
        trucks = db.query(Truck).all()
        return trucks
    except Exception as e:
        logger.error(f"Error fetching live trucks: {e}")
        return []


@router.get("/{truck_id}", response_model=TruckRead)
def get_truck(truck_id: str, db: Session = Depends(get_db)):
    truck = db.query(Truck).filter(Truck.truck_id == truck_id).first()
    if not truck:
        raise HTTPException(status_code=404, detail="Truck not found")
    return truck


@router.post("/update")
def update_truck_positions(updates: List[TruckUpdate], db: Session = Depends(get_db)):
    try:
        updated_count = 0
        for u in updates:
            truck = db.query(Truck).filter(Truck.truck_id == u.truck_id).first()
            if truck:
                truck.lat = u.lat
                truck.lon = u.lon
                truck.speed_kmh = u.speed_kmh
                truck.heading = u.heading
                truck.status = u.status
                if u.current_shipment_id is not None:
                    truck.current_shipment_id = u.current_shipment_id
                truck.last_updated = datetime.utcnow()
                updated_count += 1
        db.commit()
        return {"updated": updated_count, "total": len(updates)}
    except Exception as e:
        logger.error(f"Error updating truck positions: {e}")
        return {"updated": 0, "total": len(updates), "error": str(e)}
