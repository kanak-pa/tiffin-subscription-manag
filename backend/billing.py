from datetime import date, timedelta
import calendar
from decimal import Decimal, ROUND_HALF_UP

def count_weekdays(start_date: date, end_date: date) -> int:
    count = 0
    curr = start_date
    while curr <= end_date:
        if curr.weekday() < 5:
            count += 1
        curr += timedelta(days=1)
    return count

def calculate_monthly_bill(sub, year: int, month: int) -> dict:
    _, last_day = calendar.monthrange(year, month)
    month_start = date(year, month, 1)
    month_end = date(year, month, last_day)

    total_weekdays = count_weekdays(month_start, month_end)

    paused_weekdays = 0
    for pause in sub.pause_logs:
        overlap_start = max(pause.pause_start, month_start)
        overlap_end = min(pause.pause_end, month_end)
        if overlap_start <= overlap_end:
            paused_weekdays += count_weekdays(overlap_start, overlap_end)

    served_weekdays = max(0, total_weekdays - paused_weekdays)

    if total_weekdays > 0:
        per_day_rate = sub.monthly_rate / Decimal(total_weekdays)
        total_bill = (per_day_rate * Decimal(served_weekdays)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    else:
        total_bill = Decimal('0.00')

    return {
        "customer_name": sub.user.name,
        "phone": sub.user.phone,
        "monthly_rate": sub.monthly_rate,
        "total_weekdays": total_weekdays,
        "days_paused": paused_weekdays,
        "days_served": served_weekdays,
        "final_bill": total_bill
    }