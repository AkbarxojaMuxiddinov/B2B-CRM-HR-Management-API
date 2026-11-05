from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DepartmentViewSet, UserViewSet, AttendanceViewSet, PayrollViewSet

router = DefaultRouter()
router.register(r'departments', DepartmentViewSet)
router.register(r'users', UserViewSet)
router.register(r'attendance', AttendanceViewSet)
router.register(r'payrolls', PayrollViewSet)

urlpatterns = [
    path('', include(router.urls)),
]