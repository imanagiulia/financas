"""
Arquivo mantido para compatibilidade retroativa.
A implementacao agora reside em app.services.notification_service.
"""

from app.services.notification_service import (
    get_setting,
    send_email,
    check_and_send_daily_alerts,
    send_monthly_summary,
    _card,
    _fmt,
)

__all__ = [
    "get_setting",
    "send_email",
    "check_and_send_daily_alerts",
    "send_monthly_summary",
]
