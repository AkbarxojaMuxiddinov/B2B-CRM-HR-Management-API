import django.utils.timezone
import employees.utils
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('employees', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='attendance',
            name='check_in',
            field=models.TimeField(default=employees.utils.current_attendance_time, editable=False, help_text='Ishga kelgan vaqti'),
        ),
        migrations.AlterField(
            model_name='attendance',
            name='date',
            field=models.DateField(default=django.utils.timezone.localdate, editable=False),
        ),
    ]
