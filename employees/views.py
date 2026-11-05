from datetime import time

from django.conf import settings
from django.utils.dateparse import parse_time
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Attendance, Department, Payroll, User
from .permissions import RoleBasedPermission
from .serializers import (
    AttendanceSerializer,
    DepartmentSerializer,
    PayrollSerializer,
    UserSerializer,
)
from .utils import attendance_now


class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    permission_classes = [RoleBasedPermission]


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.select_related('department').all()
    serializer_class = UserSerializer
    permission_classes = [RoleBasedPermission]

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.role == User.Role.HR:
            return queryset.exclude(role=User.Role.ADMIN)
        if self.request.user.role == User.Role.EMPLOYEE:
            return queryset.filter(pk=self.request.user.pk)
        return queryset


class AttendanceViewSet(viewsets.ModelViewSet):
    queryset = Attendance.objects.select_related('employee').all()
    serializer_class = AttendanceSerializer
    permission_classes = [RoleBasedPermission]

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.role == User.Role.HR:
            return queryset.exclude(employee__role=User.Role.ADMIN)
        if self.request.user.role == User.Role.EMPLOYEE:
            return queryset.filter(employee=self.request.user)
        return queryset

    @action(detail=False, methods=['post'], url_path='check_in')
    def check_in(self, request):
        now = attendance_now()
        start_time = parse_time(settings.ATTENDANCE_START_TIME) or time(9, 0)
        check_in_time = now.time().replace(tzinfo=None)
        attendance, created = Attendance.objects.get_or_create(
            employee=request.user,
            date=now.date(),
            defaults={
                'check_in': check_in_time,
                'is_late': check_in_time > start_time,
            },
        )
        if not created:
            return Response(
                {'detail': 'Bugun uchun check-in allaqachon bajarilgan.'},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(
            self.get_serializer(attendance).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=['post'], url_path='check_out')
    def check_out(self, request):
        now = attendance_now()
        try:
            attendance = Attendance.objects.get(
                employee=request.user,
                date=now.date(),
            )
        except Attendance.DoesNotExist:
            return Response(
                {'detail': 'Avval check-in bajarish kerak.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        if attendance.check_out is not None:
            return Response(
                {'detail': 'Bugun uchun check-out allaqachon bajarilgan.'},
                status=status.HTTP_409_CONFLICT,
            )
        attendance.check_out = now.time().replace(tzinfo=None)
        attendance.save(update_fields=['check_out'])
        return Response(self.get_serializer(attendance).data)


class PayrollViewSet(viewsets.ModelViewSet):
    queryset = Payroll.objects.select_related('employee').all()
    serializer_class = PayrollSerializer
    permission_classes = [RoleBasedPermission]

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.role == User.Role.HR:
            return queryset.exclude(employee__role=User.Role.ADMIN)
        if self.request.user.role == User.Role.EMPLOYEE:
            return queryset.filter(employee=self.request.user)
        return queryset
