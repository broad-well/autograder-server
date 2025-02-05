import shutil
import tempfile
import traceback
import uuid
from io import FileIO
from typing import List, Tuple

import celery
from autograder_sandbox import AutograderSandbox, SandboxNotDestroyed, SandboxNotStopped
from autograder_sandbox.autograder_sandbox import CompletedCommand
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import send_mail
from django.conf import settings
from django.db import IntegrityError, transaction

import autograder.core.models as ag_models
from autograder.utils.retry import retry_should_recover

from .utils import add_files_to_sandbox, mark_submission_as_error, run_ag_command


@celery.shared_task(max_retries=1, acks_late=True)
def grade_deferred_mutation_test_suite(mutation_test_suite_pk, submission_pk):

    @retry_should_recover
    def _grade_deferred_mutation_test_suite_impl():
        try:
            grade_mutation_test_suite_impl(
                ag_models.MutationTestSuite.objects.get(pk=mutation_test_suite_pk),
                ag_models.Submission.objects.get(pk=submission_pk))
        except ObjectDoesNotExist:
            # This means that the suite was deleted, so we skip it.
            pass

    try:
        _grade_deferred_mutation_test_suite_impl()
    except Exception:
        print('Error grading deferred mutation test suite')
        traceback.print_exc()
        mark_submission_as_error(submission_pk, traceback.format_exc())


def grade_mutation_test_suite_impl(mutation_test_suite: ag_models.MutationTestSuite,
                                   submission: ag_models.Submission):
    sandbox = AutograderSandbox(
        name='submission{}-suite{}-{}'.format(
            submission.pk, mutation_test_suite.pk, uuid.uuid4().hex),
        environment_variables={
            'usernames': ' '.join(submission.group.member_names)
        },
        allow_network_access=mutation_test_suite.allow_network_access,
        docker_image=mutation_test_suite.sandbox_docker_image.tag)
    print(mutation_test_suite.sandbox_docker_image.to_dict())
    print(sandbox.docker_image)
    try:
        with sandbox:
            add_files_to_sandbox(sandbox, mutation_test_suite, submission)

            if mutation_test_suite.use_setup_command:
                print('Running setup for', mutation_test_suite.name)
                setup_run_result = run_ag_command(mutation_test_suite.setup_command, sandbox)
                if setup_run_result.return_code != 0:
                    _save_results(
                        mutation_test_suite,
                        submission, setup_run_result,
                        student_tests=[],
                        discarded_tests=[],
                        invalid_tests=[],
                        timed_out_tests=[],
                        bugs_exposed=[]
                    )
                    return
            else:
                setup_run_result = None

            get_test_names_result = run_ag_command(
                mutation_test_suite.get_student_test_names_command, sandbox)

            if get_test_names_result.return_code != 0:
                _save_results(
                    mutation_test_suite,
                    submission,
                    setup_run_result,
                    student_tests=[],
                    discarded_tests=[],
                    invalid_tests=[],
                    timed_out_tests=[],
                    bugs_exposed=[],
                    get_test_names_run_result=get_test_names_result
                )
                return

            if mutation_test_suite.test_name_discovery_whitespace_handling == 'newline':
                student_tests = ([
                    line.strip() for line in
                    get_test_names_result.stdout.read().decode(
                        errors='backslashreplace').splitlines()
                ])
            else:
                student_tests = (
                    get_test_names_result.stdout.read().decode(errors='backslashreplace').split())

            discarded_tests: List[str] = []
            if len(student_tests) > mutation_test_suite.max_num_student_tests:
                discarded_tests = student_tests[mutation_test_suite.max_num_student_tests:]
                student_tests = student_tests[:mutation_test_suite.max_num_student_tests]

            valid_tests: List[str] = []
            invalid_tests: List[str] = []
            timed_out_tests: List[str] = []

            validity_check_stdout = tempfile.TemporaryFile()
            validity_check_stderr = tempfile.TemporaryFile()
            for test in student_tests:
                validity_cmd = mutation_test_suite.student_test_validity_check_command
                concrete_cmd = validity_cmd.cmd.replace(
                    ag_models.MutationTestSuite.STUDENT_TEST_NAME_PLACEHOLDER, test)

                validity_run_result = run_ag_command(validity_cmd, sandbox,
                                                     cmd_str_override=concrete_cmd)
                line = '\n------ {} ------\n'.format(test).encode()
                validity_check_stdout.write(line)
                validity_check_stderr.write(line)
                shutil.copyfileobj(validity_run_result.stdout, validity_check_stdout)
                shutil.copyfileobj(validity_run_result.stderr, validity_check_stderr)

                if validity_run_result.return_code == 0:
                    valid_tests.append(test)
                else:
                    invalid_tests.append(test)

                if validity_run_result.timed_out:
                    timed_out_tests.append(test)

            run_individual_tests = (
                ag_models.MutationTestSuite.STUDENT_TEST_NAME_PLACEHOLDER
                in mutation_test_suite.grade_buggy_impl_command.cmd
            )
            if run_individual_tests:
                exposed_bugs, buggy_impls_stdout, buggy_impls_stderr = (
                    _run_individual_tests_against_mutants(
                        sandbox, mutation_test_suite, valid_tests
                    )
                )
            else:
                exposed_bugs, buggy_impls_stdout, buggy_impls_stderr = (
                    _run_test_batches_against_mutants(
                        sandbox, mutation_test_suite, valid_tests
                    )
                )

            _save_results(
                mutation_test_suite,
                submission,
                setup_run_result,
                student_tests, discarded_tests,
                invalid_tests, timed_out_tests, exposed_bugs,
                get_test_names_run_result=get_test_names_result,
                validity_check_stdout=validity_check_stdout,
                validity_check_stderr=validity_check_stderr,
                buggy_impls_stdout=buggy_impls_stdout,
                buggy_impls_stderr=buggy_impls_stderr
            )
            _mocking_hook_sandbox_teardown_error()
    except (SandboxNotStopped, SandboxNotDestroyed) as e:
        # If either of these exceptions were thrown, we know that the
        # suite finished grading (these exceptions can only be thrown
        # when the sandbox is being torn down).
        # Rather than marking the submission with error status,
        # we proceed as normal and send an urgent email to the sysadmin.
        send_mail(
            subject=f'[Autograder.io] {type(e).__name__} error on autograder',
            message=f'Error encountered when tearing down sandbox with ID {sandbox.name}. '
                    'If the exception in the subject is SandboxNotStopped, this is urgent.\n\n'
                    '(UMmich DCO): Go to the monitoring site to figure out which machine '
                    f'this sandbox is running on, then try running "docker kill {sandbox.name}" '
                    'on that machine.\n\n'
                    'The full error is below: \n\n'
                    + traceback.format_exc(),
            from_email=settings.EMAIL_FROM_ADDR,
            recipient_list=settings.ERROR_NOTIFICATION_EMAIL_ADDRS,
            fail_silently=True
        )


def _mocking_hook_sandbox_teardown_error():
    pass


def _run_individual_tests_against_mutants(
    sandbox: AutograderSandbox,
    mutation_test_suite: ag_models.MutationTestSuite,
    valid_tests: List[str],
) -> Tuple[List[str], tempfile.TemporaryFile, tempfile.TemporaryFile]:
    exposed_bugs: List[str] = []
    buggy_impls_stdout = tempfile.TemporaryFile()
    buggy_impls_stderr = tempfile.TemporaryFile()
    for bug in mutation_test_suite.buggy_impl_names:
        for valid_test in valid_tests:
            cmd_str = mutation_test_suite.grade_buggy_impl_command.cmd.replace(
                ag_models.MutationTestSuite.STUDENT_TEST_NAME_PLACEHOLDER, valid_test
            ).replace(ag_models.MutationTestSuite.BUGGY_IMPL_NAME_PLACEHOLDER, bug)

            buggy_impl_run_result = run_ag_command(
                mutation_test_suite.grade_buggy_impl_command,
                sandbox,
                cmd_str_override=cmd_str
            )
            line = '\n----- Bug "{}" with Test "{}" -----\n'.format(bug, valid_test).encode()
            buggy_impls_stdout.write(line)
            buggy_impls_stderr.write(line)
            shutil.copyfileobj(buggy_impl_run_result.stdout, buggy_impls_stdout)
            shutil.copyfileobj(buggy_impl_run_result.stderr, buggy_impls_stderr)

            if buggy_impl_run_result.return_code != 0:
                exposed_bugs.append(bug)
                break

    return exposed_bugs, buggy_impls_stdout, buggy_impls_stderr


def _run_test_batches_against_mutants(
    sandbox: AutograderSandbox,
    mutation_test_suite: ag_models.MutationTestSuite,
    valid_tests: List[str],
) -> Tuple[List[str], tempfile.TemporaryFile, tempfile.TemporaryFile]:
    exposed_bugs: List[str] = []
    buggy_impls_stdout = tempfile.TemporaryFile()
    buggy_impls_stderr = tempfile.TemporaryFile()
    for bug in mutation_test_suite.buggy_impl_names:
        cmd_str = mutation_test_suite.grade_buggy_impl_command.cmd.replace(
            ag_models.MutationTestSuite.ALL_STUDENT_TEST_NAMES_PLACEHOLDER,
            ' '.join([f'"{test_name}"' for test_name in valid_tests])
        ).replace(ag_models.MutationTestSuite.BUGGY_IMPL_NAME_PLACEHOLDER, bug)

        buggy_impl_run_result = run_ag_command(
            mutation_test_suite.grade_buggy_impl_command, sandbox, cmd_str_override=cmd_str)

        line = f'\n----- Bug "{bug}" with all_valid_tests -----\n'.encode()
        buggy_impls_stdout.write(line)
        buggy_impls_stderr.write(line)
        shutil.copyfileobj(buggy_impl_run_result.stdout, buggy_impls_stdout)
        shutil.copyfileobj(buggy_impl_run_result.stderr, buggy_impls_stderr)

        if buggy_impl_run_result.return_code != 0:
            exposed_bugs.append(bug)

    return exposed_bugs, buggy_impls_stdout, buggy_impls_stderr


@retry_should_recover
def _save_results(mutation_test_suite: ag_models.MutationTestSuite,
                  submission: ag_models.Submission,
                  setup_run_result: CompletedCommand,
                  student_tests: List[str],
                  discarded_tests: List[str],
                  invalid_tests: List[str],
                  timed_out_tests: List[str],
                  bugs_exposed: List[str],
                  get_test_names_run_result: CompletedCommand = None,
                  validity_check_stdout: FileIO = None,
                  validity_check_stderr: FileIO = None,
                  buggy_impls_stdout: FileIO = None,
                  buggy_impls_stderr: FileIO = None):
    try:
        with transaction.atomic():
            result_kwargs = {
                'student_tests': student_tests,
                'discarded_tests': discarded_tests,
                'invalid_tests': invalid_tests,
                'timed_out_tests': timed_out_tests,
                'bugs_exposed': bugs_exposed
            }
            result = ag_models.MutationTestSuiteResult.objects.update_or_create(
                defaults=result_kwargs,
                mutation_test_suite=mutation_test_suite,
                submission=submission)[0]  # type: ag_models.MutationTestSuiteResult

            if setup_run_result is not None:
                setup_result = ag_models.AGCommandResult.objects.validate_and_create(
                    return_code=setup_run_result.return_code,
                    timed_out=setup_run_result.timed_out,
                    stdout_truncated=setup_run_result.stdout_truncated,
                    stderr_truncated=setup_run_result.stderr_truncated
                )  # type: ag_models.AGCommandResult

                with open(setup_result.stdout_filename, 'wb') as f:
                    shutil.copyfileobj(setup_run_result.stdout, f)

                with open(setup_result.stderr_filename, 'wb') as f:
                    shutil.copyfileobj(setup_run_result.stderr, f)

                result.setup_result = setup_result
                result.save()

            if get_test_names_run_result is not None:
                result.get_test_names_result.return_code = get_test_names_run_result.return_code
                result.get_test_names_result.timed_out = get_test_names_run_result.timed_out
                result.get_test_names_result.save()
                with open(result.get_test_names_result.stdout_filename, 'wb') as f:
                    get_test_names_run_result.stdout.seek(0)
                    shutil.copyfileobj(get_test_names_run_result.stdout, f)
                with open(result.get_test_names_result.stderr_filename, 'wb') as f:
                    get_test_names_run_result.stderr.seek(0)
                    shutil.copyfileobj(get_test_names_run_result.stderr, f)

            if validity_check_stdout is not None:
                validity_check_stdout.seek(0)
                with open(result.validity_check_stdout_filename, 'wb') as f:
                    shutil.copyfileobj(validity_check_stdout, f)
            if validity_check_stderr is not None:
                validity_check_stderr.seek(0)
                with open(result.validity_check_stderr_filename, 'wb') as f:
                    shutil.copyfileobj(validity_check_stderr, f)
            if buggy_impls_stdout is not None:
                buggy_impls_stdout.seek(0)
                with open(result.grade_buggy_impls_stdout_filename, 'wb') as f:
                    shutil.copyfileobj(buggy_impls_stdout, f)
            if buggy_impls_stderr is not None:
                buggy_impls_stderr.seek(0)
                with open(result.grade_buggy_impls_stderr_filename, 'wb') as f:
                    shutil.copyfileobj(buggy_impls_stderr, f)
    except IntegrityError:
        # The mutation test suite has likely been deleted, so do nothing
        pass
