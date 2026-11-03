"""Pure policy for binding local admission to unchanged source."""

import unittest

from tools.automation.implementations import auto_m6_local_admit as admission
from tools.automation.implementations.auto_m6_local_admit import same_source


class LocalAdmissionBindingTest(unittest.TestCase):
    def test_changed_source_is_not_admitted(self):
        self.assertFalse(same_source("before", "after"))

    def test_unchanged_source_is_admitted(self):
        self.assertTrue(same_source("same", "same"))

    def test_failed_test_output_retains_only_declared_ids(self):
        known = "backend/tests/example.py::test_observation"
        output = (
            f"FAILED {known}[private parameter] - arbitrary detail\n"
            "FAILED backend/tests/unknown.py::test_other - private detail\n"
            "ollama_installation_discovery_invalid\n"
        ).encode()
        tests, codes = admission.safe_failure_summary(output, frozenset({known}))
        self.assertEqual(tests, (known,))
        self.assertEqual(codes, ("ollama_installation_discovery_invalid",))

    def test_unknown_output_and_oversized_output_are_not_echoed(self):
        self.assertEqual(
            admission.safe_failure_summary(b"private detail", frozenset()), ((), ())
        )
        self.assertEqual(
            admission.safe_failure_summary(b"x" * 2_097_153, frozenset()), ((), ())
        )

    def test_declared_ids_exclude_nested_functions_and_parameter_values(self):
        ids = admission.declared_test_ids(
            {
                "backend/tests/example.py": (
                    "def test_observation():\n    def test_nested(): pass\n"
                ),
            }
        )
        self.assertEqual(ids, frozenset({"backend/tests/example.py::test_observation"}))
