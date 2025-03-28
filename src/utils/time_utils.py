from datetime import datetime
import pytz
from src.config.config import TIMEZONE, WEEKDAY_NAMES, MONTH_NAMES

def get_current_time():
    vietnam_tz = pytz.timezone(TIMEZONE)
    return datetime.now(vietnam_tz)

def format_date(current_time):
    return f"Hôm nay là {WEEKDAY_NAMES[current_time.weekday()]}, {current_time.day} {MONTH_NAMES[current_time.month]} năm {current_time.year}"

def format_time(current_time):
    return f"Bây giờ là {current_time.hour:02d}:{current_time.minute:02d}" 