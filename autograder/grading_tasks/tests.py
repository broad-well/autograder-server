import subprocess
import time
from unittest import mock

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.urlresolvers import reverse

from rest_framework import status
from rest_framework.test import APIClient

import autograder.core.models as ag_models
import autograder.utils.testing.model_obj_builders as obj_build
import autograder.utils.testing as test_ut
import autograder.utils.testing.generic_data as gen_data

from . import tasks


class _MockException(Exception):
    pass


class TasksTestCase(test_ut.UnitTestBase):
    def setUp(self):
        super().setUp()

        self.group = obj_build.build_submission_group()
        self.project = self.group.project

        impl_h = ag_models.UploadedFile.objects.validate_and_create(
            file_obj=SimpleUploadedFile('impl.h', _IMPL_H),
            project=self.project)

        needs_files_test = ag_models.UploadedFile.objects.validate_and_create(
            file_obj=SimpleUploadedFile('needs_files_test.py',
                                        _NEEDS_FILES_TEST),
            project=self.project)

        unit_test = ag_models.UploadedFile.objects.validate_and_create(
            file_obj=SimpleUploadedFile('unit_test.cpp', _UNIT_TEST),
            project=self.project)

        impl_cpp = ag_models.ExpectedStudentFilePattern.objects.validate_and_create(
            pattern='impl.cpp',
            project=self.project)

        test_star_cpp = ag_models.ExpectedStudentFilePattern.objects.validate_and_create(
            pattern='test*.cpp', min_num_matches=1, max_num_matches=4,
            project=self.project)

        self.compiled_test = ag_models.AutograderTestCaseFactory.validate_and_create(
            'compiled_and_run_test_case', name='compiley', compiler='g++',
            expected_return_code=0, points_for_correct_return_code=1,
            feedback_configuration=ag_models.FeedbackConfig.create_with_max_fdbk(),
            project=self.project)
        self.compiled_test.test_resource_files.add(impl_h)
        self.compiled_test.project_files_to_compile_together.add(unit_test)
        self.compiled_test.student_files_to_compile_together.add(impl_cpp)

        self.interpreted_test = ag_models.AutograderTestCaseFactory.validate_and_create(
            'interpreted_test_case', name='interprety', interpreter='python3',
            entry_point_filename=needs_files_test.name,
            expected_return_code=0, points_for_correct_return_code=1,
            feedback_configuration=ag_models.FeedbackConfig.create_with_max_fdbk(),
            project=self.project)
        self.interpreted_test.test_resource_files.add(needs_files_test)
        self.interpreted_test.student_resource_files.add(test_star_cpp)

        test_files = [SimpleUploadedFile('test{}.cpp'.format(i), b'waaaa')
                      for i in range(2)]
        self.submission = ag_models.Submission.objects.validate_and_create(
            test_files + [SimpleUploadedFile('impl.cpp', _IMPL_CPP)],
            submission_group=self.group)

    def test_grade_submission_no_deferred(self):
        print(self.submission.pk)
        tasks.grade_submission(self.submission.pk)
        tasks.check_for_finished_deferreds()

        self.submission.refresh_from_db()
        self.assertEqual(2, self.submission.basic_score)

        self.assertEqual(ag_models.Submission.GradingStatus.finished_grading,
                         self.submission.status)

    def test_grade_submission_some_deferred(self):
        self.compiled_test.validate_and_update(deferred=True)
        tasks.grade_submission(self.submission.pk)
        tasks.check_for_finished_deferreds()

        self.submission.refresh_from_db()
        self.assertEqual(2, self.submission.basic_score)
        self.assertEqual(ag_models.Submission.GradingStatus.finished_grading,
                         self.submission.status)

    def test_grade_submission_all_deferred(self):
        self._mark_all_as_deferred()
        tasks.grade_submission(self.submission.pk)
        tasks.check_for_finished_deferreds()

        self.submission.refresh_from_db()
        self.assertEqual(2, self.submission.basic_score)
        self.assertEqual(ag_models.Submission.GradingStatus.finished_grading,
                         self.submission.status)

    def test_grade_submission_removed_from_queue(self):
        self.compiled_test.validate_and_update(deferred=True)
        self.submission.status = ag_models.Submission.GradingStatus.removed_from_queue
        self.submission.save()
        tasks.grade_submission(self.submission.pk)
        tasks.check_for_finished_deferreds()

        self.submission.refresh_from_db()
        self.assertEqual(ag_models.Submission.GradingStatus.removed_from_queue,
                         self.submission.status)

    @mock.patch('autograder.grading_tasks.tasks.grade_ag_test_impl.mocking_hook')
    def test_non_deferred_retry_on_error(self, impl_mock):
        impl_mock.side_effect = TasksTestCase._SideEffectSequence([
            _MockException('retry me I am an error'),
            lambda: None,
            _MockException('retry me I am an error'),
            lambda: None])
        tasks.grade_submission(self.submission.pk)

        self.submission.refresh_from_db()
        self.assertEqual(ag_models.Submission.GradingStatus.waiting_for_deferred,
                         self.submission.status)
        self.assertEqual(2, self.submission.basic_score)

    @mock.patch('autograder.grading_tasks.tasks.grade_ag_test_impl')
    def test_non_deferred_max_num_retries_exceeded(self, impl_mock):
        impl_mock.side_effect = [
            subprocess.CalledProcessError(42, ['waaaluigi'])
            for i in range(settings.AG_TEST_MAX_RETRIES + 1)]
        with self.assertRaises(subprocess.CalledProcessError):
            tasks.grade_submission(self.submission.pk)

        self.submission.refresh_from_db()
        self.assertEqual(ag_models.Submission.GradingStatus.error,
                         self.submission.status)
        self.assertEqual(0, self.submission.basic_score)

    @mock.patch('autograder.grading_tasks.tasks.grade_ag_test_impl.mocking_hook')
    def test_deferred_retry_on_called_process_error(self, impl_mock):
        self.interpreted_test.validate_and_update(deferred=True)
        self.compiled_test.delete()
        impl_mock.side_effect = TasksTestCase._SideEffectSequence([
            _MockException('errorrr'),
            lambda: None])
        tasks.grade_submission(self.submission.pk)

        self.submission.refresh_from_db()
        self.assertEqual(1, self.submission.basic_score)
        self.assertEqual(ag_models.Submission.GradingStatus.waiting_for_deferred,
                         self.submission.status)

    @mock.patch('autograder.grading_tasks.tasks.grade_ag_test_impl')
    def test_deferred_ag_test_max_retries_exceeded(self, impl_mock):
        impl_mock.side_effect = [
            subprocess.CalledProcessError(42, ['waaaluigi'])
            for i in range(settings.AG_TEST_MAX_RETRIES + 1)]
        with self.assertRaises(subprocess.CalledProcessError):
            tasks.grade_ag_test(self.compiled_test.pk, self.submission.pk)

    def _mark_all_as_deferred(self):
        self.compiled_test.validate_and_update(deferred=True)
        self.interpreted_test.validate_and_update(deferred=True)
        for test in self.project.autograder_test_cases.all():
            self.assertTrue(test.deferred)

    class _SideEffectSequence:
        '''
        In some situations, we want to pass a mix of values, exceptions,
        and callables to the side_effects parameter of a mock object.
        This class enables that.
        '''

        def __init__(self, side_effects):
            self._side_effects = side_effects
            self._iter = iter(self._side_effects)

        def __call__(self, *args, **kwargs):
            print(args, kwargs)
            next_item = next(self._iter)
            try:
                return next_item(*args, **kwargs)
            except TypeError as e:
                print(e)

            try:
                raise next_item
            except TypeError as e:
                print(e)

            return next_item


_NEEDS_FILES_TEST = b'''
import os
import fnmatch

def main():
    num_files = len(fnmatch.filter(os.listdir('.'), 'test*.cpp'))
    if num_files != 2:
        print('booooo')
        raise SystemExit(1)

    print('yay')


if __name__ == '__main__':
    main()
'''

_UNIT_TEST = b'''
#include "impl.h"

#include <iostream>
#include <cassert>

using namespace std;

int main()
{
    assert(spam() == 42);
    cout << "yay!" << endl;
}
'''

_IMPL_H = b'''
#ifndef IMPL_H
#define IMPL_H

int spam();

#endif
'''

_IMPL_CPP = b'''
#include "impl.h"

int spam()
{
    return 42;
}
'''


class RaceConditionTestCase(gen_data.Project,
                            gen_data.Submission,
                            test_ut.UnitTestBase):
    def test_remove_from_queue_when_being_marked_as_being_graded_race_condition_prevented(self):
        group = self.admin_group(self.project)
        submission = self.build_submission(group)

        path = ('autograder.grading_tasks.tasks.ag_models'
                '.Submission.GradingStatus.removed_from_queue')

        @test_ut.sleeper_subtest(
            path,
            new_callable=mock.PropertyMock,
            return_value=(ag_models.Submission.GradingStatus.removed_from_queue))
        def do_request_and_wait():
            tasks.grade_submission(submission.pk)

        subtest = do_request_and_wait()

        print('sending remove from queue request')
        client = APIClient()
        client.force_authenticate(
            submission.submission_group.members.first())
        response = client.post(reverse('submission-remove-from-queue',
                                       kwargs={'pk': submission.pk}))
        subtest.join()
        submission.refresh_from_db()
        self.assertNotEqual(
            ag_models.Submission.GradingStatus.removed_from_queue,
            submission.status)
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)

        time_waited = 0
        while (submission.status !=
                ag_models.Submission.GradingStatus.finished_grading):
            tasks.check_for_finished_deferreds()
            print(submission.status)
            if time_waited > 10:
                self.fail('spent too long waiting')
            time.sleep(2)
            time_waited += 2
            submission.refresh_from_db()

    def test_mark_as_waiting_for_deferred_and_finished_grading_at_same_time_race_prevented(self):
        group = self.admin_group(self.project)
        submission = self.build_submission(group)

        path = 'autograder.grading_tasks.tasks.mark_as_finished.mocking_hook'

        @test_ut.sleeper_subtest(path)
        def do_mark_as_finished():
            tasks.mark_as_finished([], submission.pk)
            submission.refresh_from_db()
            self.assertEqual(
                ag_models.Submission.GradingStatus.finished_grading,
                submission.status)

        subtest = do_mark_as_finished()
        tasks.mark_as_waiting_for_deferred(submission.pk)
        subtest.join()
        submission.refresh_from_db()
        self.assertEqual(
            ag_models.Submission.GradingStatus.finished_grading,
            submission.status)
