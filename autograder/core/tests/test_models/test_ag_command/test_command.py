from django.core import exceptions
from django.test import SimpleTestCase

import autograder.core.models as ag_models
from autograder.core import constants
from autograder.utils.testing import UnitTestBase


class CommandTestCase(SimpleTestCase):
    def test_from_dict_default_values(self):
        cmd = ag_models.Command.from_dict({'cmd': 'cmdy'})

        self.assertEqual('cmdy', cmd.cmd)
        self.assertEqual('', cmd.name)
        self.assertEqual(constants.DEFAULT_SUBPROCESS_TIMEOUT, cmd.time_limit)
        self.assertEqual(constants.DEFAULT_STACK_SIZE_LIMIT, cmd.stack_size_limit)
        self.assertFalse(cmd.use_virtual_memory_limit)
        self.assertEqual(constants.DEFAULT_VIRTUAL_MEM_LIMIT, cmd.virtual_memory_limit)
        self.assertFalse(cmd.block_process_spawn)
        self.assertEqual(constants.DEFAULT_PROCESS_LIMIT, cmd.process_spawn_limit)

    def test_from_dict_non_default_values(self):
        cmd = ag_models.Command.from_dict({
            'cmd': 'cmdy',
            'name': 'steve',
            'time_limit': 5,
            'stack_size_limit': 15000,
            'use_virtual_memory_limit': False,
            'virtual_memory_limit': 200000,
            'block_process_spawn': True,
            'process_spawn_limit': 8,
        })

        self.assertEqual('cmdy', cmd.cmd)
        self.assertEqual('steve', cmd.name)
        self.assertEqual(5, cmd.time_limit)
        self.assertEqual(15000, cmd.stack_size_limit)
        self.assertFalse(cmd.use_virtual_memory_limit)
        self.assertEqual(200000, cmd.virtual_memory_limit)
        self.assertTrue(cmd.block_process_spawn)
        self.assertEqual(8, cmd.process_spawn_limit)

    def test_error_cmd_missing(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.Command.from_dict({})

        self.assertIn('cmd', cm.exception.message)

    def test_error_cmd_empty(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.Command.from_dict({'cmd': ''})

        self.assertIn('cmd', cm.exception.message)

    def test_error_time_limit_out_of_range(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.Command.from_dict({
                'cmd': 'cmdy',
                'time_limit': 0,
            })

        self.assertIn('time_limit', cm.exception.message)

        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.Command.from_dict({
                'cmd': 'cmdy',
                'time_limit': constants.MAX_SUBPROCESS_TIMEOUT + 1,
            })

        self.assertIn('time_limit', cm.exception.message)

    def test_error_stack_size_limit_out_of_range(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.Command.from_dict({
                'cmd': 'cmdy',
                'stack_size_limit': 0,
            })

        self.assertIn('stack_size_limit', cm.exception.message)

        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.Command.from_dict({
                'cmd': 'cmdy',
                'stack_size_limit': constants.MAX_STACK_SIZE_LIMIT + 1,
            })

        self.assertIn('stack_size_limit', cm.exception.message)

    def test_error_virtual_memory_limit_out_of_range(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.Command.from_dict({
                'cmd': 'cmdy',
                'virtual_memory_limit': 0,
            })

        self.assertIn('virtual_memory_limit', cm.exception.message)

    def test_error_process_spawn_limit_out_of_range(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.Command.from_dict({
                'cmd': 'cmdy',
                'process_spawn_limit': -1,
            })

        self.assertIn('process_spawn_limit', cm.exception.message)

        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.Command.from_dict({
                'cmd': 'cmdy',
                'process_spawn_limit': constants.MAX_PROCESS_LIMIT + 1,
            })

        self.assertIn('process_spawn_limit', cm.exception.message)

    def test_serialize(self):
        expected_fields = [
            'name',
            'cmd',
            'time_limit',
            'stack_size_limit',
            'use_virtual_memory_limit',
            'virtual_memory_limit',
            'block_process_spawn',
            'process_spawn_limit',
        ]

        cmd = ag_models.Command.from_dict({'cmd': 'cmdy'})
        self.assertCountEqual(expected_fields, cmd.to_dict().keys())

        update_dict = cmd.to_dict()
        cmd.update(update_dict)
