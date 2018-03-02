import autograder.handgrading.models as hg_models
import autograder.handgrading.serializers as handgrading_serializers
import autograder.rest_api.permissions as ag_permissions
from django.db import transaction

from autograder.rest_api.views.ag_model_views import (
    AGModelGenericViewSet, ListCreateNestedModelView, TransactionRetrieveUpdateDestroyMixin,
)


class CriterionListCreateView(ListCreateNestedModelView):
    serializer_class = handgrading_serializers.CriterionSerializer
    permission_classes = [
        ag_permissions.is_admin_or_read_only_staff(
            lambda handgrading_rubric: handgrading_rubric.project.course)]

    pk_key = 'handgrading_rubric_pk'
    model_manager = hg_models.HandgradingRubric.objects.select_related('project__course')
    foreign_key_field_name = 'handgrading_rubric'
    reverse_foreign_key_field_name = 'criteria'

    @transaction.atomic()
    def create(self, request, *args, **kwargs):
        handgrading_rubric = self.get_object()

        # Create criterion first
        criterion_response = super().create(request=request)

        criterion = hg_models.Criterion.objects.get(**criterion_response.data)
        results = hg_models.HandgradingResult.objects.filter(handgrading_rubric=handgrading_rubric)

        # Create CriterionResult for every HandgradingResult with the same HandgradingRubric
        for result in results:
            hg_models.CriterionResult.objects.validate_and_create(
                selected=False,
                criterion=criterion,
                handgrading_result=result)

        return criterion_response


class CriterionDetailViewSet(TransactionRetrieveUpdateDestroyMixin, AGModelGenericViewSet):
    serializer_class = handgrading_serializers.CriterionSerializer
    permission_classes = [
        ag_permissions.is_admin_or_read_only_staff(
            lambda criterion: criterion.handgrading_rubric.project.course)
    ]
    model_manager = hg_models.Criterion.objects.select_related(
        'handgrading_rubric__project__course',
    )
