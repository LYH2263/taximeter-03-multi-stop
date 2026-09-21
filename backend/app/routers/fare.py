from fastapi import APIRouter, HTTPException
from app.modules.multi_stop import MultiStopError
from app.schemas.fare import CompareRequest, FareRequest, MultiStopRequest
from app.services.taxi_service import TaxiService
router = APIRouter()
@router.post("/fare")
def post_fare(body: FareRequest):
    with TaxiService() as s:
        return s.fare(body.distance_km, body.slow_min, body.night, body.trip_id, body.persist)
@router.post("/compare")
def post_compare(body: CompareRequest):
    with TaxiService() as s:
        return s.compare(body.distance_km, body.slow_min, body.persist)
@router.post("/fare/multi")
def post_fare_multi(body: MultiStopRequest):
    with TaxiService() as s:
        try:
            return s.multi_fare([x.model_dump() for x in body.segments], body.night, body.persist)
        except MultiStopError as e:
            raise HTTPException(400, str(e))
