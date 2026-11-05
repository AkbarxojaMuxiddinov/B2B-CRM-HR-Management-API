from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from .models import Attendance, Payroll, User


def previous_month(today):
    if today.month == 1:
        return today.year - 1, 12
    return today.year, today.month - 1


def month_dates(year, month):
    first_day = date(year, month, 1)
    last_day = date(year, month, monthrange(year, month)[1])
    return first_day, last_day


def working_dates(start_date, end_date):
    if start_date > end_date:
        return []
    return [
        start_date + timedelta(days=offset)
        for offset in range((end_date - start_date).days + 1)
        if (start_date + timedelta(days=offset)).weekday() < 5
    ]


@shared_task
def generate_monthly_payrolls(year=None, month=None):
    if (year is None) != (month is None):
        raise ValueError('year va month birga berilishi kerak.')

    if year is None:
        year, month = previous_month(timezone.localdate())

    month_start, month_end = month_dates(year, month)
    employees = list(User.objects.filter(is_active=True))
    attendance_by_employee = {}
    attendance_records = Attendance.objects.filter(
        employee__in=employees,
        date__range=(month_start, month_end),
    ).only('employee_id', 'date')
    for attendance in attendance_records:
        if attendance.date.weekday() < 5:
            attendance_by_employee.setdefault(attendance.employee_id, set()).add(
                attendance.date
            )

    created = 0
    skipped = 0
    cent = Decimal('0.01')

    for employee in employees:
        hired_date = timezone.localtime(employee.hired_at).date()
        period_start = max(month_start, hired_date)
        scheduled_days = working_dates(period_start, month_end)
        if not scheduled_days:
            skipped += 1
            continue

        attended_days = len(
            attendance_by_employee.get(employee.pk, set()).intersection(
                scheduled_days
            )
        )
        total_amount = (
            employee.base_salary * Decimal(attended_days) / Decimal(len(scheduled_days))
        ).quantize(cent, rounding=ROUND_HALF_UP)

        with transaction.atomic():
            _, was_created = Payroll.objects.get_or_create(
                employee=employee,
                month=month_start,
                defaults={
                    'bonus': Decimal('0.00'),
                    'fine': Decimal('0.00'),
                    'total_amount': total_amount,
                    'status': Payroll.Status.PENDING,
                },
            )

        if was_created:
            created += 1
        else:
            skipped += 1

    return {
        'month': month_start.isoformat(),
        'created': created,
        'skipped': skipped,
    }
