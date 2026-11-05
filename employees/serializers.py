from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import Department, User, Attendance, Payroll


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = '__all__'


class UserSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source='department.name', read_only=True)
    password = serializers.CharField(
        write_only=True,
        required=False,
        style={'input_type': 'password'},
    )

    class Meta:
        model = User
        fields = [
            'id', 'username', 'first_name', 'last_name', 'email',
            'role', 'department', 'department_name', 'position',
            'phone', 'base_salary', 'hired_at', 'password',
        ]

    def validate(self, attrs):
        password = attrs.get('password')
        if not self.instance and not password:
            raise serializers.ValidationError({'password': 'Parol kiritilishi shart.'})
        if password:
            validate_password(password, user=self.instance)
        return attrs

    def create(self, validated_data):
        password = validated_data.pop('password')
        return User.objects.create_user(password=password, **validated_data)

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        instance = super().update(instance, validated_data)
        if password:
            instance.set_password(password)
            instance.save(update_fields=['password'])
        return instance

class AttendanceSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.username', read_only=True)

    class Meta:
        model = Attendance
        fields = '__all__'
        read_only_fields = ('date', 'check_in', 'is_late')


class PayrollSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.username', read_only=True)

    class Meta:
        model = Payroll
        fields = '__all__'

