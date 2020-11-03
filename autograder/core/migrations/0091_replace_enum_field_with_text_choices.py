# Generated by Django 3.1.2 on 2020-10-30 19:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0090_replace_string_array_field_with_pg_array_and_char_field'),
    ]

    operations = [
        migrations.AlterField(
            model_name='agtestcommand',
            name='expected_return_code',
            field=models.TextField(choices=[('none', 'None'), ('zero', 'Zero'), ('nonzero', 'Nonzero')], default='none', help_text="Specifies the command's expected return code."),
        ),
        migrations.AlterField(
            model_name='agtestcommand',
            name='expected_stderr_source',
            field=models.TextField(choices=[('none', 'None'), ('text', 'Text'), ('instructor_file', 'Instructor File')], default='none', help_text="Specifies what kind of source this command's stderr should be compared to."),
        ),
        migrations.AlterField(
            model_name='agtestcommand',
            name='expected_stdout_source',
            field=models.TextField(choices=[('none', 'None'), ('text', 'Text'), ('instructor_file', 'Instructor File')], default='none', help_text="Specifies what kind of source this command's stdout should be compared to."),
        ),
        migrations.AlterField(
            model_name='agtestcommand',
            name='stdin_source',
            field=models.TextField(choices=[('none', 'None'), ('text', 'Text'), ('instructor_file', 'Instructor File'), ('setup_stdout', 'Setup Stdout'), ('setup_stderr', 'Setup Stderr')], default='none', help_text='Specifies what kind of source stdin will be redirected from.'),
        ),
        migrations.AlterField(
            model_name='buildsandboxdockerimagetask',
            name='status',
            field=models.TextField(blank=True, choices=[('queued', 'Queued'), ('in_progress', 'In Progress'), ('done', 'Done'), ('failed', 'Failed'), ('image_invalid', 'Image Invalid'), ('cancelled', 'Cancelled'), ('internal_error', 'Internal Error')], default='queued', help_text='The status of the build.'),
        ),
        migrations.AlterField(
            model_name='course',
            name='semester',
            field=models.TextField(blank=True, choices=[('Fall', 'Fall'), ('Winter', 'Winter'), ('Spring', 'Spring'), ('Summer', 'Summer')], default=None, null=True),
        ),
        migrations.AlterField(
            model_name='downloadtask',
            name='download_type',
            field=models.TextField(choices=[('all_scores', 'All Scores'), ('final_graded_submission_scores', 'Final Graded Submission Scores'), ('all_submission_files', 'All Submission Files'), ('final_graded_submission_files', 'Final Graded Submission Files')]),
        ),
        migrations.AlterField(
            model_name='project',
            name='ultimate_submission_policy',
            field=models.TextField(blank=True, choices=[('most_recent', 'Most Recent'), ('best_basic_score', 'Best With Normal Fdbk'), ('best', 'Best')], default='most_recent', help_text='The "ultimate" submission for a group is the one\n            that will be used for final grading. This field specifies\n            how the ultimate submission should be determined.'),
        ),
    ]
