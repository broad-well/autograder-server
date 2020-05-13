# Generated by Django 2.0.1 on 2018-06-06 14:41

import autograder.core.fields
import autograder.core.models.ag_test.ag_test_command
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0018_remove_stdout_stderr_text_from_ag_test_suite_result'),
    ]

    operations = [
        migrations.AddField(
            model_name='agtestcommand',
            name='first_failed_test_normal_fdbk_config',
            field=autograder.core.fields.ValidatedJSONField(blank=True, default=None, help_text='When non-null, specifies feedback to be given when\n                     this command is in the first test case that failed\n                     within a suite.', null=True, serializable_class=autograder.core.models.ag_test.ag_test_command.AGTestCommandFeedbackConfig),
        ),
    ]
