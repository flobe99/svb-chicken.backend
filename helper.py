from models import *
from fastapi import HTTPException
from datetime import datetime, timedelta


def check_slot_limit(order: OrderChicken, db):
    errors = []
    print(order.date)
    matching_slot = db.query(SlotDB).filter(
        SlotDB.range_start <= order.date,
        SlotDB.range_end >= order.date
    ).first()


    if not matching_slot:
        errors.append({
            "code": LimitCode.SLOT,
            "detail": "Bestellzeit liegt außerhalb der verfügbaren Slots"
        })

    if not _is_quarter_hour(order.date):
        errors.append({
            "code": LimitCode.TIME,
            "detail": "Uhrzeit muss auf eine Viertelstunde liegen (z. B. 12:15)"
        })

    config = db.query(ConfigChickenDB).first()
    if not config:
        raise HTTPException(status_code=500, detail="Keine Mengen-Konfiguration gefunden")

    slot_start = order.date.replace(minute=(order.date.minute // 15) * 15, second=0, microsecond=0)
    slot_end = slot_start + timedelta(minutes=15)

    orders_in_slot = db.query(OrderChickenDB).filter(
        OrderChickenDB.date >= slot_start,
        OrderChickenDB.date < slot_end
    ).all()   
    
    if order.chicken > 0:
        used_chicken = sum(o.chicken for o in orders_in_slot)
        if used_chicken + order.chicken > config.chicken:
            errors.append({
                "code": LimitCode.CHICKEN,
                "detail": "Maximale Hähnchenmenge für dieses Zeitfenster überschritten."
            })

    if order.nuggets > 0:
        used_nuggets = sum(o.nuggets for o in orders_in_slot)
        if used_nuggets + order.nuggets > config.nuggets:
            errors.append({
                "code": LimitCode.NUGGETS,
                "detail": "Maximale Nuggetsmenge für dieses Zeitfenster überschritten."
            })

    if order.fries > 0:
        used_fries = sum(o.fries for o in orders_in_slot)
        if used_fries + order.fries > config.fries:
            errors.append({
                "code": LimitCode.FRIES,
                "detail": "Maximale Pommesmenge für dieses Zeitfenster überschritten."
            })

    if errors:
        raise HTTPException(status_code=400, detail={"success": False, "errors": errors})

def _is_quarter_hour(dt: datetime) -> bool:
    return dt.minute in [0, 15, 30, 45]