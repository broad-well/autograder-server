import os

from django.core.exceptions import ValidationError

from autograder.core.models import Course, LateDaysRemaining

import autograder.core.utils as core_ut
from autograder.utils.testing import UnitTestBase

import autograder.utils.testing.model_obj_builders as obj_build


class CourseTestCase(UnitTestBase):
    def test_valid_create_with_defaults(self):
        name = "eecs280"
        course = Course.objects.validate_and_create(name=name)

        course.refresh_from_db()

        self.assertEqual(name, course.name)
        self.assertEqual(0, course.num_late_days)

    def test_create_no_defaults(self):
        name = 'Waaaaaluigi'
        late_days = 2
        course = Course.objects.validate_and_create(
            name=name, num_late_days=late_days)

        course.refresh_from_db()

        self.assertEqual(name, course.name)
        self.assertEqual(late_days, course.num_late_days)

    def test_exception_on_empty_name(self):
        with self.assertRaises(ValidationError) as cm:
            Course.objects.validate_and_create(name='')
        self.assertTrue('name' in cm.exception.message_dict)

    def test_exception_on_null_name(self):
        with self.assertRaises(ValidationError) as cm:
            Course.objects.validate_and_create(name=None)
        self.assertTrue('name' in cm.exception.message_dict)

    def test_exception_on_non_unique_name(self):
        course = obj_build.build_course()
        with self.assertRaises(ValidationError) as cm:
            Course.objects.validate_and_create(name=course.name)
        self.assertTrue('name' in cm.exception.message_dict)

    def test_error_negative_late_days(self):
        with self.assertRaises(ValidationError) as cm:
            Course.objects.validate_and_create(name='steve', num_late_days=-1)
        self.assertIn('num_late_days', cm.exception.message_dict)

    def test_serializable_fields(self):
        expected_fields = [
            'pk',
            'name',
            'num_late_days',
            'last_modified',
        ]

        self.assertCountEqual(expected_fields,
                              Course.get_serializable_fields())

        course = obj_build.build_course()
        self.assertTrue(course.to_dict())

    def test_editable_fields(self):
        expected = ['name', 'num_late_days']
        self.assertCountEqual(expected, Course.get_editable_fields())


class LateDaysRemainingTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()
        self.course = obj_build.make_course()
        self.user = obj_build.make_user()

    def test_valid_create_with_defaults(self):
        num_late_days = 2
        self.course.validate_and_update(num_late_days=num_late_days)
        remaining = LateDaysRemaining.objects.validate_and_create(
            course=self.course,
            user=self.user,
        )

        self.assertEqual(self.course, remaining.course)
        self.assertEqual(self.user, remaining.user)
        self.assertEqual(num_late_days, remaining.late_days_remaining)

    def test_valid_create(self):
        late_days_remaining = 2
        remaining = LateDaysRemaining.objects.validate_and_create(
            course=self.course,
            user=self.user,
            late_days_remaining=late_days_remaining
        )

        self.assertEqual(self.course, remaining.course)
        self.assertEqual(self.user, remaining.user)
        self.assertEqual(late_days_remaining, remaining.late_days_remaining)

    def test_error_already_exists_for_user_and_course(self):
        LateDaysRemaining.objects.validate_and_create(
            course=self.course,
            user=self.user,
            late_days_remaining=1
        )

        with self.assertRaises(ValidationError):
            LateDaysRemaining.objects.validate_and_create(
                course=self.course,
                user=self.user,
                late_days_remaining=3
            )

    def test_error_negative_late_days_remaining(self):
        with self.assertRaises(ValidationError):
            LateDaysRemaining.objects.validate_and_create(
                course=self.course,
                user=self.user,
                late_days_remaining=-1
            )


class CourseFilesystemTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()
        self.COURSE_NAME = 'eecs280'

    def test_course_root_dir_created(self):
        course = Course(name=self.COURSE_NAME)

        self.assertFalse(
            os.path.exists(os.path.dirname(core_ut.get_course_root_dir(course))))

        course.save()
        expected_course_root_dir = core_ut.get_course_root_dir(course)

        self.assertTrue(os.path.isdir(expected_course_root_dir))


class CourseRolesTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()

        self.course = obj_build.build_course()
        self.user = obj_build.create_dummy_user()

    def test_is_admin(self):
        self.course = obj_build.build_course()
        self.user = obj_build.create_dummy_user()

        self.assertFalse(self.course.is_admin(self.user))

        self.course.admins.add(self.user)
        self.assertTrue(self.course.is_admin(self.user))

    def test_is_staff(self):
        self.assertFalse(self.course.is_staff(self.user))

        self.course.staff.add(self.user)
        self.assertTrue(self.course.is_staff(self.user))

    def test_admin_counts_as_staff(self):
        self.assertFalse(self.course.is_staff(self.user))

        self.course.admins.add(self.user)
        self.assertTrue(self.course.is_staff(self.user))

    def test_is_student(self):
        self.assertFalse(self.course.is_student(self.user))

        self.course.students.add(self.user)
        self.assertTrue(self.course.is_student(self.user))

    def test_is_handgrader(self):
        self.assertFalse(self.course.is_handgrader(self.user))

        self.course.handgraders.add(self.user)
        self.assertTrue(self.course.is_handgrader(self.user))
