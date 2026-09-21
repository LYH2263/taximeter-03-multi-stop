from fastapi import APIRouter

from app.modules.multi_stop.schemas import MultiStopRequest
from app.services.taxi_service import TaxiService

router = APIRouter()


@router.post("/fare/multi")
def post_multi_fare(body: MultiStopRequest):
    with TaxiService() as s:
        return s.multi_fare([seg.model_dump() for seg in body.segments], body.night, body.persist)
