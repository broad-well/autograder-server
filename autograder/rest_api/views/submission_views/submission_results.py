from django.utils import timezone

from rest_framework import viewsets, mixins, permissions

import autograder.core.models as ag_models
import autograder.rest_api.serializers as ag_serializers

from ..permission_components import user_can_view_group
from ..load_object_mixin import build_load_object_mixin


class _Permissions(permissions.BasePermission):
    def has_object_permission(self, request, view, submission):
        return user_can_view_group(request.user, submission.submission_group)


class SubmissionResultsViewset(
        build_load_object_mixin(ag_models.Submission, pk_key='submission_pk'),
        mixins.ListModelMixin,
        viewsets.GenericViewSet):
    serializer_class = ag_serializers.AGTestResultSerializer
    permission_classes = (permissions.IsAuthenticated, _Permissions)

    def get_queryset(self):
        submission = self.get_object()
        group = submission.submission_group
        project = group.project
        course = project.course

        user = self.request.user

        student_view = self.request.query_params.get('student_view', False)
        is_group_member = group.members.filter(pk=user.pk).exists()
        if (course.is_course_staff(user) and
                not (student_view and is_group_member)):
            return submission.results.all()

        deadline_past = (project.closing_time is None or
                         timezone.now() > project.closing_time)
        if (deadline_past and not project.hide_ultimate_submission_fdbk and
                submission == group.ultimate_submission):
            return submission.results.filter(
                test_case__visible_in_ultimate_submission=True)

        if submission.is_past_daily_limit:
            return submission.results.filter(
                test_case__visible_in_past_limit_submission=True)

        return submission.results.filter(test_case__visible_to_students=True)
