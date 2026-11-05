from rest_framework.permissions import BasePermission, SAFE_METHODS

from .models import Attendance, Department, Payroll, User


class RoleBasedPermission(BasePermission):
    read_actions = {'list', 'retrieve'}
    write_actions = {'create', 'update', 'partial_update', 'destroy'}

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        model = view.queryset.model
        action = getattr(view, 'action', None)

        if model == Attendance and action in {'check_in', 'check_out'}:
            return True

        if user.role == User.Role.ADMIN:
            return True

        if user.role == User.Role.HR:
            if model == User:
                if action not in self.read_actions | self.write_actions:
                    return False
                return request.data.get('role') != User.Role.ADMIN
            return model in {Department, Attendance, Payroll} and action in (
                self.read_actions | self.write_actions
            )

        if user.role == User.Role.EMPLOYEE:
            if model == Department or model == User or model == Payroll:
                return action in self.read_actions
            if model == Attendance:
                if action in self.read_actions:
                    return True
                return (
                    action == 'create'
                    and str(request.data.get('employee', '')) == str(user.pk)
                )

        return False

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.role == User.Role.ADMIN:
            return True

        if isinstance(obj, Department):
            return user.role == User.Role.HR or (
                user.role == User.Role.EMPLOYEE and request.method in SAFE_METHODS
            )

        if isinstance(obj, User):
            if user.role == User.Role.HR:
                return obj.role != User.Role.ADMIN and request.data.get(
                    'role', obj.role
                ) != User.Role.ADMIN
            return (
                user.role == User.Role.EMPLOYEE
                and obj.pk == user.pk
                and request.method in SAFE_METHODS
            )

        if isinstance(obj, (Attendance, Payroll)):
            if user.role == User.Role.HR:
                return obj.employee.role != User.Role.ADMIN
            return (
                user.role == User.Role.EMPLOYEE
                and obj.employee_id == user.pk
                and request.method in SAFE_METHODS
            )

        return False
