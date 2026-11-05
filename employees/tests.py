from datetime import date, datetime, time, timedelta
from decimal import Decimal
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Attendance, Payroll, User
from .tasks import generate_monthly_payrolls


class JWTAuthenticationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='auth-user',
            password='StrongPass123!',
            position='Analyst',
        )

    def test_token_pair_authenticates_user(self):
        response = self.client.post(
            reverse('token_obtain_pair'),
            {'username': 'auth-user', 'password': 'StrongPass123!'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {response.data['access']}"
        )
        protected_response = self.client.get('/api/v1/users/')

        self.assertEqual(protected_response.status_code, status.HTTP_200_OK)

    def test_refresh_token_returns_new_access_token(self):
        token_response = self.client.post(
            reverse('token_obtain_pair'),
            {'username': 'auth-user', 'password': 'StrongPass123!'},
            format='json',
        )
        refresh_response = self.client.post(
            reverse('token_refresh'),
            {'refresh': token_response.data['refresh']},
            format='json',
        )

        self.assertEqual(refresh_response.status_code, status.HTTP_200_OK)
        self.assertIn('access', refresh_response.data)

    def test_user_creation_hashes_password_for_jwt_login(self):
        User.objects.create_user(
            username='hr-user',
            password='HrPass123!',
            position='HR Manager',
            role=User.Role.HR,
        )
        token_response = self.client.post(
            reverse('token_obtain_pair'),
            {'username': 'hr-user', 'password': 'HrPass123!'},
            format='json',
        )
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {token_response.data['access']}"
        )

        create_response = self.client.post(
            '/api/v1/users/',
            {
                'username': 'new-user',
                'password': 'DifferentStrong123!',
                'position': 'Recruiter',
            },
            format='json',
        )

        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        created_user = User.objects.get(username='new-user')
        self.assertNotEqual(created_user.password, 'DifferentStrong123!')
        self.assertTrue(created_user.check_password('DifferentStrong123!'))

        login_response = self.client.post(
            reverse('token_obtain_pair'),
            {'username': 'new-user', 'password': 'DifferentStrong123!'},
            format='json',
        )

        self.assertEqual(login_response.status_code, status.HTTP_200_OK)

    def test_employee_user_list_only_contains_own_profile(self):
        other_user = User.objects.create_user(
            username='other-user',
            password='OtherPass123!',
            position='Designer',
        )
        self.client.force_authenticate(user=self.user)

        response = self.client.get('/api/v1/users/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([item['id'] for item in response.data], [self.user.id])
        self.assertNotEqual(self.user.id, other_user.id)

    def test_hr_cannot_create_admin_role(self):
        hr_user = User.objects.create_user(
            username='hr-user',
            password='HrPass123!',
            position='HR Manager',
            role=User.Role.HR,
        )
        self.client.force_authenticate(user=hr_user)

        response = self.client.post(
            '/api/v1/users/',
            {
                'username': 'new-admin',
                'password': 'AdminPass123!',
                'position': 'Administrator',
                'role': User.Role.ADMIN,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_employee_can_only_create_own_attendance(self):
        other_user = User.objects.create_user(
            username='other-employee',
            password='OtherPass123!',
            position='Designer',
        )
        self.client.force_authenticate(user=self.user)

        own_response = self.client.post(
            '/api/v1/attendance/',
            {'employee': self.user.id},
            format='json',
        )
        other_response = self.client.post(
            '/api/v1/attendance/',
            {'employee': other_user.id},
            format='json',
        )

        self.assertEqual(own_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(other_response.status_code, status.HTTP_403_FORBIDDEN)

    @patch('employees.views.attendance_now')
    def test_check_in_records_time_and_marks_late(self, mocked_now):
        mocked_now.return_value = datetime(
            2026, 11, 5, 9, 1, tzinfo=ZoneInfo('Asia/Tashkent')
        )
        self.client.force_authenticate(user=self.user)

        response = self.client.post('/api/v1/attendance/check_in/')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['check_in'], '09:01:00')
        self.assertTrue(response.data['is_late'])

    @patch('employees.views.attendance_now')
    def test_check_in_at_start_time_is_not_late(self, mocked_now):
        mocked_now.return_value = datetime(
            2026, 11, 5, 9, 0, tzinfo=ZoneInfo('Asia/Tashkent')
        )
        self.client.force_authenticate(user=self.user)

        response = self.client.post('/api/v1/attendance/check_in/')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertFalse(response.data['is_late'])

    @patch('employees.views.attendance_now')
    def test_check_out_records_time_after_check_in(self, mocked_now):
        self.client.force_authenticate(user=self.user)
        mocked_now.return_value = datetime(
            2026, 11, 5, 9, 0, tzinfo=ZoneInfo('Asia/Tashkent')
        )
        check_in_response = self.client.post('/api/v1/attendance/check_in/')
        mocked_now.return_value = datetime(
            2026, 11, 5, 17, 30, tzinfo=ZoneInfo('Asia/Tashkent')
        )

        check_out_response = self.client.post('/api/v1/attendance/check_out/')

        self.assertEqual(check_in_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(check_out_response.status_code, status.HTTP_200_OK)
        self.assertEqual(check_out_response.data['check_out'], '17:30:00')

    @patch('employees.views.attendance_now')
    def test_duplicate_check_in_is_rejected(self, mocked_now):
        mocked_now.return_value = datetime(
            2026, 11, 5, 9, 0, tzinfo=ZoneInfo('Asia/Tashkent')
        )
        self.client.force_authenticate(user=self.user)
        self.client.post('/api/v1/attendance/check_in/')

        response = self.client.post('/api/v1/attendance/check_in/')

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)


class MonthlyPayrollTaskTests(TestCase):
    def setUp(self):
        self.employee = User.objects.create_user(
            username='payroll-user',
            password='PayrollPass123!',
            position='Analyst',
            base_salary=Decimal('2200.00'),
        )
        self.employee.hired_at = datetime(2025, 12, 15, tzinfo=ZoneInfo('UTC'))
        self.employee.save(update_fields=['hired_at'])

    def test_payroll_is_prorated_by_attended_weekdays(self):
        attended_weekdays = []
        current_day = date(2026, 1, 1)
        while current_day <= date(2026, 1, 31) and len(attended_weekdays) < 11:
            if current_day.weekday() < 5:
                attended_weekdays.append(current_day)
            current_day += timedelta(days=1)

        Attendance.objects.bulk_create(
            [
                Attendance(employee=self.employee, date=day, check_in=time(9, 0))
                for day in attended_weekdays
            ]
        )

        result = generate_monthly_payrolls.run(2026, 1)

        payroll = Payroll.objects.get(employee=self.employee, month=date(2026, 1, 1))
        self.assertEqual(payroll.total_amount, Decimal('1100.00'))
        self.assertEqual(payroll.status, Payroll.Status.PENDING)
        self.assertEqual(result, {'month': '2026-01-01', 'created': 1, 'skipped': 0})

    def test_repeated_run_does_not_duplicate_or_overwrite_payroll(self):
        generate_monthly_payrolls.run(2026, 1)
        payroll = Payroll.objects.get(employee=self.employee, month=date(2026, 1, 1))
        payroll.total_amount = Decimal('1234.56')
        payroll.status = Payroll.Status.PAID
        payroll.save(update_fields=['total_amount', 'status'])

        result = generate_monthly_payrolls.run(2026, 1)

        payroll.refresh_from_db()
        self.assertEqual(Payroll.objects.filter(employee=self.employee).count(), 1)
        self.assertEqual(payroll.total_amount, Decimal('1234.56'))
        self.assertEqual(payroll.status, Payroll.Status.PAID)
        self.assertEqual(result, {'month': '2026-01-01', 'created': 0, 'skipped': 1})

    def test_payroll_task_includes_hr_staff(self):
        hr_user = User.objects.create_user(
            username='payroll-hr',
            password='PayrollHr123!',
            position='HR Manager',
            role=User.Role.HR,
            base_salary=Decimal('3000.00'),
        )
        hr_user.hired_at = datetime(2025, 12, 15, tzinfo=ZoneInfo('UTC'))
        hr_user.save(update_fields=['hired_at'])

        result = generate_monthly_payrolls.run(2026, 1)

        self.assertEqual(result['created'], 2)
        self.assertTrue(
            Payroll.objects.filter(employee=hr_user, month=date(2026, 1, 1)).exists()
        )

    @patch('employees.tasks.timezone.localdate', return_value=date(2026, 2, 2))
    def test_task_without_period_uses_previous_month(self, mocked_localdate):
        result = generate_monthly_payrolls.run()

        self.assertEqual(result['month'], '2026-01-01')
