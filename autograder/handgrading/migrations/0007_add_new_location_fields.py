# Generated by Django 2.2 on 2019-05-24 17:07

import autograder.core.fields
import autograder.handgrading.models
from django.db import migrations


def migrate_location_fields(apps, schema_editor):
    AppliedAnnotation = apps.get_model('handgrading', 'AppliedAnnotation')
    Comment = apps.get_model('handgrading', 'Comment')

    for applied_ann in AppliedAnnotation.objects.all():
        applied_ann.location.update({
            'filename': applied_ann.old_location.filename,
            'first_line': applied_ann.old_location.first_line,
            'last_line': applied_ann.old_location.last_line,
        })

        applied_ann.full_clean()
        applied_ann.save()

    for comm in Comment.objects.all():
        if comm.old_location is None:
            continue

        comm.location.update({
            'filename': comm.old_location.filename,
            'first_line': comm.old_location.first_line,
            'last_line': comm.old_location.last_line,
        })

        comm.full_clean()
        comm.save()


class Migration(migrations.Migration):

    dependencies = [
        ('handgrading', '0006_rename_old_location_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='appliedannotation',
            name='location',
            field=autograder.core.fields.ValidatedJSONField(default={'filename': 'PLACEHOLDER', 'first_line': 0, 'last_line': 0}, help_text='The source code location where the Annotation was applied.', serializable_class=autograder.handgrading.models.NewLocation),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='comment',
            name='location',
            field=autograder.core.fields.ValidatedJSONField(blank=True, default=None, help_text='When not None, specifies the source code location this comment\n                     applies to.', null=True, serializable_class=autograder.handgrading.models.NewLocation),
        ),

        migrations.RunPython(
            migrate_location_fields, lambda apps, schema_editor: None
        )
    ]
