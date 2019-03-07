# Generated by Django 2.0.1 on 2019-03-07 00:14

import sys

import autograder.core.fields
import autograder.core.models.ag_model_base
from autograder.core.constants import SupportedImages, DOCKER_IMAGE_IDS_TO_URLS
from django.db import migrations, models

import autograder_sandbox


def create_default_image(apps, schemea_editor):
    # The fixture autograder/core/fixture/default_sandbox_image.json handles
    # creating the default image during testing.
    if sys.argv[1] == 'test':
        return

    SandboxDockerImage = apps.get_model('core', 'SandboxDockerImage')
    SandboxDockerImage.objects.create(
        name='default',
        display_name='Default',
        tag=f'jameslp/autograder-sandbox:{autograder_sandbox.VERSION}'
    )


def migrate_legacy_images(apps, schema_editor):
    """
    Create a DB row for all images listed in constants.SupportedImages
    """
    SandboxDockerImage = apps.get_model('core', 'SandboxDockerImage')

    for image_name, image_tag in DOCKER_IMAGE_IDS_TO_URLS.items():
        print(image_name, image_tag)
        if image_name != SupportedImages.default:
            print(
                SandboxDockerImage.objects.create(
                    name=image_name.value, display_name=image_name.value, tag=image_tag))


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0035_instructor_file_ag_test_command_no_cascade'),
    ]

    operations = [
        migrations.CreateModel(
            name='SandboxDockerImage',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('last_modified', models.DateTimeField(auto_now=True)),
                ('name', autograder.core.fields.ShortStringField(help_text='A string uniquely identifying this sandbox image.\n                     This field is required and cannot be edited after\n                     creation.', max_length=255, strip=False, unique=True)),
                ('display_name', autograder.core.fields.ShortStringField(help_text='A human-readable name for this sandbox image.\n                     This field is required.', max_length=255, strip=False, unique=True)),
                ('tag', models.TextField(help_text="The full tag that can be used to fetch the image with\n                     the 'docker pull' command. This should include a specific\n                     version for the image, and the version number should be\n                     incremented every time the image is updated, otherwise\n                     the new version of the image may not be fetched.")),
            ],
            options={
                'abstract': False,
            },
            bases=(autograder.core.models.ag_model_base.ToDictMixin, models.Model),
        ),

        migrations.RunPython(create_default_image, reverse_code=lambda apps, schema_editor: None),
        migrations.RunPython(migrate_legacy_images, reverse_code=lambda apps, schema_editor: None),
    ]
