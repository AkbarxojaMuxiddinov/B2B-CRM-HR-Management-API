from zoneinfo import ZoneInfo

from django.conf import settings
from django.utils import timezone


def attendance_now():
    return timezone.now().astimezone(ZoneInfo(settings.ATTENDANCE_TIME_ZONE))


def current_attendance_date():
    return attendance_now().date()


def current_attendance_time():
    return attendance_now().time().replace(tzinfo=None)
