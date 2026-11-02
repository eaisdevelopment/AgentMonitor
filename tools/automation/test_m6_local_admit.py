"""Pure policy for binding local admission to unchanged source."""

import unittest

from tools.automation.implementations.auto_m6_local_admit import same_source


class LocalAdmissionBindingTest(unittest.TestCase):
    def test_changed_source_is_not_admitted(self):
        self.assertFalse(same_source("before", "after"))

    def test_unchanged_source_is_admitted(self):
        self.assertTrue(same_source("same", "same"))
