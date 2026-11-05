from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('employees', '0002_alter_attendance_check_in_alter_attendance_date'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='payroll',
            constraint=models.UniqueConstraint(fields=('employee', 'month'), name='unique_employee_payroll_month'),
        ),
    ]
