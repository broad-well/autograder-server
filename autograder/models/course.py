import os

from django.db import models
from django.core import validators

from autograder.models.model_validatable_on_save import ModelValidatableOnSave

import autograder.shared.global_constants as gc
import autograder.shared.utilities as ut


class Course(ModelValidatableOnSave):
    """
    Represents a programming course for which students will be submitting
    code to an autograder.

    Primary key: name

    Fields:
        name -- The name of this course.
                Must be unique, non-empty and non-null.

    Overridden member functions:
        save()
    """
    # unique_together = ('name')

    name = models.CharField(
        max_length=gc.MAX_CHAR_FIELD_LEN, primary_key=True,
        validators=[
            validators.MinLengthValidator(
                1, "Course names must be non-empty")])

    # -------------------------------------------------------------------------
    # -------------------------------------------------------------------------

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        course_root_dir = ut.get_course_root_dir(self)
        if not os.path.isdir(course_root_dir):
            # Since the database is in charge or validating the uniqueness
            # of this course, we can assume at this point that creating
            # the course directory will succeed. If for some reason it fails,
            # this will be considered a more severe error, and the OSError
            # thrown by os.makedirs will be handled at a higher level.

            # print('creating: ' + course_root_dir)
            os.makedirs(course_root_dir)

    # -------------------------------------------------------------------------

    # def validate_fields(self):
    #     if not self.name:
    #         raise ValueError(
    #             "Course name must be non-null and non-empty.")
