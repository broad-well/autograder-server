# Generated by Django 2.2 on 2019-06-26 18:11

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0043_add_new_student_test_suite_command_fields'),
    ]

    operations = [
        migrations.AlterField(
            model_name='project',
            name='submission_limit_reset_time',
            field=models.TimeField(default=datetime.time, help_text='The time that marks the beginning and end of the 24\n            hour period during which submissions should be counted\n            towards the daily limit. Defaults to 00:00:00.'),
        ),
    ]
