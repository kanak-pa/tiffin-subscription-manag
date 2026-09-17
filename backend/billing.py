import calendar
from datetime import date, timedelta

def calculate_monthly_bill(subscription, year: int, month: int):
    # Total days and weekdays in the given month
    _, total_days = calendar.monthrange(year, month)
    
    total_weekdays = 0
    for day in range(1, total_days + 1):
        # 0 = Monday, ..., 4 = Friday
        if date(year, month, day).weekday() < 5:
            total_weekdays += 1

    # Count paused weekdays for this subscription
    paused_weekdays = 0
    if hasattr(subscription, 'pause_logs') and subscription.pause_logs:
        for log in subscription.pause_logs:
            curr_date = log.pause_start
            while curr_date <= log.pause_end:
                if curr_date.year == year and curr_date.month == month:
                    if curr_date.weekday() < 5:
                        paused_weekdays += 1
                curr_date += timedelta(days=1)

    # Delivered weekdays
    delivered_weekdays = max(0, total_weekdays - paused_weekdays)
    
    # Calculate daily rate based on monthly rate / total weekdays
    daily_rate = subscription.monthly_rate / total_weekdays if total_weekdays > 0 else 0
    total_bill = round(delivered_weekdays * daily_rate, 2)

    return {
        "monthly_rate": subscription.monthly_rate,
        "total_weekdays": total_weekdays,
        "paused_weekdays": paused_weekdays,
        "delivered_days": delivered_weekdays,
        "total_bill": total_bill
    }