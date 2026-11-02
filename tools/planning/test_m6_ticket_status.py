"""Pure lifecycle integrity checks for M6 ticket dependencies."""

import unittest

from tools.planning.validate_m6_tickets import validate_status_dependencies


class TicketStatusTest(unittest.TestCase):
    def test_completed_ticket_cannot_depend_on_unfinished_ticket(self):
        tickets = {
            "M6-T001": {"status": "in_progress", "depends_on": []},
            "M6-T002": {"status": "done", "depends_on": ["M6-T001"]},
        }
        self.assertEqual(
            ["M6-T002: completed_dependency_not_done"],
            validate_status_dependencies(tickets),
        )

    def test_in_progress_ticket_may_depend_on_unfinished_ticket(self):
        tickets = {
            "M6-T001": {"status": "in_progress", "depends_on": []},
            "M6-T002": {"status": "in_progress", "depends_on": ["M6-T001"]},
        }
        self.assertEqual([], validate_status_dependencies(tickets))

    def test_completed_ticket_with_completed_dependency_is_valid(self):
        tickets = {
            "M6-T001": {"status": "done", "depends_on": []},
            "M6-T002": {"status": "done", "depends_on": ["M6-T001"]},
        }
        self.assertEqual([], validate_status_dependencies(tickets))
