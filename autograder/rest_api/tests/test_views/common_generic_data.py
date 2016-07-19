'''
The classes defined here serve as mixins for adding members to a class
that yield data commonly used in the REST API view test cases. Note that
database objects are not created until the first time they are accessed
per test case.
'''

import random
import copy

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.urlresolvers import reverse

from rest_framework.test import APIClient

import autograder.core.models as ag_models

import autograder.core.tests.dummy_object_utils as obj_ut


class Client:
    def setUp(self):
        super().setUp()
        self.client = APIClient()


class Superuser:
    @property
    def superuser(self):
        if not hasattr(self, '_superuser'):
            self._superuser = obj_ut.create_dummy_user(is_superuser=True)

        return self._superuser


class Course:
    @property
    def course(self):
        if not hasattr(self, '_course'):
            self._course = obj_ut.build_course()

        return self._course

    @property
    def admin(self):
        if not hasattr(self, '_admin'):
            self._admin = obj_ut.create_dummy_user()
            self.course.administrators.add(self._admin)

        return self._admin

    @property
    def staff(self):
        if not hasattr(self, '_staff'):
            self._staff = obj_ut.create_dummy_user()
            self.course.staff.add(self._staff)

        return self._staff

    @property
    def enrolled(self):
        if not hasattr(self, '_enrolled'):
            self._enrolled = obj_ut.create_dummy_user()
            self.course.enrolled_students.add(self._enrolled)

        return self._enrolled

    @property
    def nobody(self):
        if not hasattr(self, '_nobody'):
            self._nobody = obj_ut.create_dummy_user()

        return self._nobody


class Project(Course):
    def get_proj_url(self, project):
        return reverse('project-detail', kwargs={'pk': project.pk})

    def get_patterns_url(self, project):
        return reverse('project-expected-patterns-list',
                       kwargs={'project_pk': project.pk})

    def get_uploaded_files_url(self, project):
        return reverse('project-uploaded-files-list',
                       kwargs={'project_pk': project.pk})

    def get_groups_url(self, project):
        return reverse('project-groups-list',
                       kwargs={'project_pk': project.pk})

    def get_invitations_url(self, project):
        return reverse('project-group-invitations-list',
                       kwargs={'project_pk': project.pk})

    def get_ag_tests_url(self, project):
        return reverse('project-ag-tests-list',
                       kwargs={'project_pk': project.pk})

    @property
    def project(self):
        if not hasattr(self, '_project'):
            self._project = ag_models.Project.objects.validate_and_create(
                name='spammy' + random.choice('qewiurqelrhjk'),
                course=self.course)

        return self._project

    @property
    def visible_public_project(self):
        if not hasattr(self, '_visible_public_project'):
            self._visible_public_project = (
                ag_models.Project.objects.validate_and_create(
                    name='visible_public_project',
                    course=self.course,
                    visible_to_students=True,
                    allow_submissions_from_non_enrolled_students=True))

        return self._visible_public_project

    @property
    def visible_private_project(self):
        if not hasattr(self, '_visible_private_project'):
            self._visible_private_project = (
                ag_models.Project.objects.validate_and_create(
                    name='visible_private_project',
                    course=self.course,
                    visible_to_students=True,
                    allow_submissions_from_non_enrolled_students=False))

        return self._visible_private_project

    @property
    def hidden_public_project(self):
        if not hasattr(self, '_hidden_public_project'):
            self._hidden_public_project = (
                ag_models.Project.objects.validate_and_create(
                    name='hidden_public_project',
                    course=self.course,
                    visible_to_students=False,
                    allow_submissions_from_non_enrolled_students=True))

        return self._hidden_public_project

    @property
    def hidden_private_project(self):
        if not hasattr(self, '_hidden_private_project'):
            self._hidden_private_project = (
                ag_models.Project.objects.validate_and_create(
                    name='hidden_private_project',
                    course=self.course,
                    visible_to_students=False,
                    allow_submissions_from_non_enrolled_students=False))

        return self._hidden_private_project

    @property
    def visible_projects(self):
        return [self.visible_public_project, self.visible_private_project]

    @property
    def hidden_projects(self):
        return [self.hidden_public_project, self.hidden_private_project]

    @property
    def public_projects(self):
        return [self.visible_public_project, self.hidden_public_project]

    @property
    def projects_hidden_from_non_enrolled(self):
        return [self.visible_private_project] + self.hidden_projects

    @property
    def all_projects(self):
        return self.visible_projects + self.hidden_projects


class Group(Course):
    def setUp(self):
        super().setUp()
        # For caching
        self._invitations = {
            # <project pk>: {
            #   <label>: <invitation object>
            # }
        }

        self._groups = {
            # <project pk>: {
            #   <label>: <group object>
            # }
        }

    def invitation_url(self, invitation):
        return reverse('group-invitation-detail', kwargs={'pk': invitation.pk})

    def admin_group_invitation(self, project):
        label = '_admin_group_invitation'
        return self._build_invitation(project, self.admin, label)

    def staff_group_invitation(self, project):
        label = '_staff_group_invitation'
        return self._build_invitation(project, self.staff, label)

    def enrolled_group_invitation(self, project):
        label = '_enrolled_group_invitation'
        return self._build_invitation(project, self.enrolled, label)

    def non_enrolled_group_invitation(self, project):
        label = '_non_enrolled_group_invitation'
        return self._build_invitation(project, self.nobody, label)

    def _build_invitation(self, project, user_to_clone, label):
        if project.max_group_size < 3:
            project.validate_and_update(max_group_size=3)

        invitation = self._get_cached_invitation(project, label)
        if invitation is not None:
            return invitation

        invitees = [self.clone_user(user_to_clone) for i in range(2)]
        invitation = ag_models.SubmissionGroupInvitation.objects.validate_and_create(
            user_to_clone, invitees, project=project)

        self._store_invitation(project, label, invitation)
        return invitation

    # -------------------------------------------------------------------------

    def group_url(self, group):
        return reverse('group-detail', kwargs={'pk': group.pk})

    def admin_group(self, project):
        return self._build_group(project, self.admin, 'admin_group')

    def staff_group(self, project):
        return self._build_group(project, self.staff, 'staff_group')

    def enrolled_group(self, project):
        return self._build_group(project, self.enrolled, 'enrolled_group')

    def non_enrolled_group(self, project):
        return self._build_group(project, self.nobody, 'non_enrolled_group')

    def all_groups(self, project):
        return [self.admin_group(project), self.staff_group(project),
                self.enrolled_group(project), self.non_enrolled_group(project)]

    def at_least_enrolled_groups(self, project):
        return [self.admin_group(project), self.staff_group(project),
                self.enrolled_group(project)]

    def non_staff_groups(self, project):
        return [self.enrolled_group(project), self.non_enrolled_group(project)]

    def staff_groups(self, project):
        return [self.admin_group(project), self.staff_group(project)]

    def _build_group(self, project, user_to_clone, label):
        if project.max_group_size < 3:
            project.validate_and_update(max_group_size=3)

        group = self._get_cached_group(project, label)
        if group is not None:
            return group

        members = ([user_to_clone] +
                   [self.clone_user(user_to_clone) for i in range(2)])
        group = ag_models.SubmissionGroup.objects.validate_and_create(
            members, project=project)
        self._store_group(project, label, group)
        return group

    # -------------------------------------------------------------------------

    def clone_user(self, user):
        new_user = copy.copy(user)
        new_user.pk = None
        new_user.username = obj_ut.get_unique_id()
        new_user.save()
        new_user.courses_is_admin_for.add(*user.courses_is_admin_for.all())
        new_user.courses_is_staff_for.add(*user.courses_is_staff_for.all())
        new_user.courses_is_enrolled_in.add(*user.courses_is_enrolled_in.all())

        return new_user

    def _get_cached_invitation(self, project, label):
        try:
            return self._invitations[project.pk][label]
        except KeyError:
            return None

    def _store_invitation(self, project, label, invitation):
        if project.pk not in self._invitations:
            self._invitations[project.pk] = {}
            self._invitations[project.pk][label] = invitation

    def _get_cached_group(self, project, label):
        try:
            return self._groups[project.pk][label]
        except KeyError:
            return None

    def _store_group(self, project, label, group):
        if project.pk not in self._groups:
            self._groups[project.pk] = {}

        self._groups[project.pk][label] = group


# Note that submissions are not cached because they are not required to be
# unique
class Submission(Group):
    def admin_submission(self, project):
        return self.build_submission(self.admin_group(project))

    def staff_submission(self, project):
        return self.build_submission(self.staff_group(project))

    def enrolled_submission(self, project):
        return self.build_submission(self.enrolled_group(project))

    def non_enrolled_submission(self, project):
        return self.build_submission(self.non_enrolled_group(project))

    def all_submissions(self, project):
        return [self.build_submission(group)
                for group in self.all_groups(project)]

    def at_least_enrolled_submissions(self, project):
        return [self.build_submission(group)
                for group in self.at_least_enrolled_groups(project)]

    def non_staff_submissions(self, project):
        return [self.build_submission(group)
                for group in self.non_staff_groups(project)]

    def staff_submissions(self, project):
        return [self.build_submission(group)
                for group in self.staff_groups(project)]

    @property
    def files_to_submit(self):
        return [
            SimpleUploadedFile('spam.cpp', b'steve'),
            SimpleUploadedFile('egg.txt', b'stave'),
            SimpleUploadedFile('sausage.txt', b'stove')
        ]

    def add_expected_patterns(self, project):
        if project.expected_student_file_patterns.count():
            return

        ag_models.ExpectedStudentFilePattern.objects.validate_and_create(
            pattern='spam.cpp', project=project)
        ag_models.ExpectedStudentFilePattern.objects.validate_and_create(
            pattern='*.txt', project=project, max_num_matches=3)

    def build_submission(self, group):
        self.add_expected_patterns(group.project)

        return ag_models.Submission.objects.validate_and_create(
            self.files_to_submit, submission_group=group,
            submitter=group.members.first().username)

    def build_submissions(self, group):
        submissions = []
        for i in range(group.members.count()):
            submissions.append(self.build_submission(group))

        return submissions
