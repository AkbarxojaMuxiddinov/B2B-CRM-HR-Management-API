from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

from .utils import current_attendance_time


class Department(models.Model):


  name = models.CharField(max_length=100, unique=True)
  description = models.TextField(blank=True, null=True)

  def __str__(self):
    return self.name


class User(AbstractUser):


  class Role(models.TextChoices):
    ADMIN = 'admin', 'Kompaniya admini'
    HR = 'HR', 'HR Menejer'
    EMPLOYEE = 'employee', 'Oddiy Xodim'

  role = models.CharField(
      max_length=20, choices=Role.choices, default=Role.EMPLOYEE
  )

  department = models.ForeignKey(
      Department,
      on_delete=models.SET_NULL,
      null=True,
      blank=True,
      related_name='employees',
  )
  position = models.CharField(
      max_length=100, help_text='Lavozimi (masalan: Backend Developer)'
  )

  phone = models.CharField(max_length=15, unique=True, null=True, blank=True)
  base_salary = models.DecimalField(
      max_digits=12,
      decimal_places=2,
      default=0.00,
      help_text='Asosiy oylik maoshi',
  )
  hired_at = models.DateTimeField(
      auto_now_add=True,
      help_text='Ishga kirgan sanasi',
  )

  def __str__(self):
    return f'{self.first_name} {self.last_name} ({self.position})'


class Attendance(models.Model):


  employee = models.ForeignKey(
      User, on_delete=models.CASCADE, related_name='attendances'
  )
  date = models.DateField(default=timezone.localdate, editable=False)
  check_in = models.TimeField(default=current_attendance_time, editable=False, help_text='Ishga kelgan vaqti')
  check_out = models.TimeField(null=True, blank=True, help_text='Ishdan ketgan vaqti')
  is_late = models.BooleanField(default=False, help_text='Kechikib kelganmi?')

  class Meta:
    unique_together = ('employee', 'date')

  def __str__(self):
    return f'{self.employee.username} - {self.date}'


class Payroll(models.Model):


  class Status(models.TextChoices):
    PENDING = 'pending', 'Kutilmoqda'
    PAID = 'paid', "To'landi"

  employee = models.ForeignKey(
      User, on_delete=models.CASCADE, related_name='payrolls'
  )
  month = models.DateField(help_text='Qaysi oy uchun (masalan: 2026-10-01)')
  bonus = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
  fine = models.DecimalField(
      max_digits=10,
      decimal_places=2,
      default=0.00,
      help_text='Kechikish uchun jarima',
  )
  total_amount = models.DecimalField(
      max_digits=12, decimal_places=2, help_text="Jami to'lanadigan summa"
  )
  status = models.CharField(
      max_length=20, choices=Status.choices, default=Status.PENDING
  )
  created_at = models.DateTimeField(auto_now_add=True)

  class Meta:
    constraints = [
        models.UniqueConstraint(
            fields=('employee', 'month'),
            name='unique_employee_payroll_month',
        )
    ]

  def __str__(self):
    return f'{self.employee.username} - {self.month.strftime("%B %Y")} ({self.total_amount}$)'
