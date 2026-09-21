from fastapi import APIRouter
from app.modules.multi_stop.router import router as multi_stop_router
from app.routers import dashboard, fare, history, settings, tariff, trips

api = APIRouter(prefix="/api")
for m in (dashboard, trips, tariff, fare, history, settings):
    api.include_router(m.router)
api.include_router(multi_stop_router)
