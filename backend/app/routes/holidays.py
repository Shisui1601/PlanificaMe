from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..utils.helpers import get_holiday
from ..schemas.schemas import HolidayResponse
from datetime import datetime, timedelta
from typing import List

router = APIRouter(prefix="/api/holidays", tags=["holidays"])


@router.get("/{date}", response_model=HolidayResponse)
def get_holiday_by_date(date: str, db: Session = Depends(get_db)):
    """Obtiene el feriado para una fecha específica (YYYY-MM-DD)"""
    holiday = get_holiday(date)
    if not holiday:
        raise HTTPException(status_code=404, detail="No es un feriado")
    return HolidayResponse(date=date, name=holiday)


@router.get("/by-month/{year}/{month}")
def get_holidays_by_month(year: int, month: int, db: Session = Depends(get_db)):
    """Obtiene todos los feriados de un mes"""
    holidays = []
    from app.utils.helpers import HOLIDAYS_DO
    
    for date_str, name in HOLIDAYS_DO.items():
        try:
            d = datetime.strptime(date_str, "%Y-%m-%d")
            if d.year == year and d.month == month:
                holidays.append(HolidayResponse(date=date_str, name=name))
        except:
            pass
    
    return {"holidays": holidays, "total": len(holidays)}


@router.get("/by-year/{year}")
def get_holidays_by_year(year: int, db: Session = Depends(get_db)):
    """Obtiene todos los feriados de un año"""
    holidays = []
    from app.utils.helpers import HOLIDAYS_DO
    
    for date_str, name in HOLIDAYS_DO.items():
        try:
            d = datetime.strptime(date_str, "%Y-%m-%d")
            if d.year == year:
                holidays.append(HolidayResponse(date=date_str, name=name))
        except:
            pass
    
    return {"holidays": sorted(holidays, key=lambda x: x.date), "total": len(holidays)}


@router.get("/")
def get_all_holidays(db: Session = Depends(get_db)):
    """Obtiene todos los feriados disponibles"""
    holidays = []
    from app.utils.helpers import HOLIDAYS_DO
    
    for date_str, name in HOLIDAYS_DO.items():
        holidays.append(HolidayResponse(date=date_str, name=name))
    
    return {"holidays": sorted(holidays, key=lambda x: x.date), "total": len(holidays)}
