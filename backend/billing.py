import calendar
from datetime import date, timedelta
from typing import Dict, Any

def calculate_monthly_bill(subscription, year: int, month: int) -> Dict[str, Any]:
    _, days_in_month = calendar.monthrange(year, month)
    daily_rate = subscription.monthly_rate / days_in_month

    paused_days_count = 0
    month_start = date(year, month, 1)
    month_end = date(year, month, days_in_month)

    for log in subscription.pause_logs:
        # Check date overlap
        start = max(log.pause_start, month_start)
        end = min(log.pause_end, month_end)

        if start <= end:
            paused_days_count += (end - start).days + 1

    active_days = days_in_month - paused_days_count
    total_bill = round(active_days * daily_rate, 2)

    return {
        "days_in_month": days_in_month,
        "paused_days": paused_days_count,
        "active_days": active_days,
        "daily_rate": round(daily_rate, 2),
        "total_bill": total_bill
    }