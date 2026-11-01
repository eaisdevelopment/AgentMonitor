"""Focused safety checks for the local inventory command."""

import unittest

from tools.discovery.m6_local_inventory import NoRedirect, read_json


class LocalInventoryPolicyTest(unittest.TestCase):
    def test_unapproved_source_is_rejected_before_io(self):
        with self.assertRaisesRegex(ValueError, "source_not_allowed"):
            read_json("/api/generate")

    def test_redirect_does_not_authorize_another_target(self):
        self.assertIsNone(NoRedirect().redirect_request(None, None, 302, "", {}, "https://example.com"))
