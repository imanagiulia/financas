from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.categories import router as categories_router
from app.api.v1.transactions import router as transactions_router
from app.api.v1.fixed_expenses import router as fixed_expenses_router
from app.api.v1.debts import router as debts_router
from app.api.v1.investments import router as investments_router
from app.api.v1.settings import router as settings_router
from app.api.v1.reports import router as reports_router
from app.api.v1.cron import router as cron_router

api_router = APIRouter(prefix="/api")


@api_router.get("/health", tags=["health"])
def health_check():
    return {"status": "ok"}


api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(dashboard_router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(categories_router, prefix="/categories", tags=["categories"])
api_router.include_router(transactions_router, prefix="/transactions", tags=["transactions"])
api_router.include_router(fixed_expenses_router, prefix="/fixed-expenses", tags=["fixed-expenses"])
api_router.include_router(debts_router, prefix="/debts", tags=["debts"])
api_router.include_router(investments_router, prefix="/investments", tags=["investments"])
api_router.include_router(settings_router, prefix="/settings", tags=["settings"])
api_router.include_router(reports_router, prefix="/reports", tags=["reports"])
api_router.include_router(cron_router, prefix="/cron", tags=["cron"])
