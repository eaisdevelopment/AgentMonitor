"""Real-checkout tests for repository documentation validation."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from check import check_repository  # noqa: E402


class DocumentationCheckTests(unittest.TestCase):
    def test_real_repository_documentation_is_internally_resolvable(self) -> None:
        self.assertEqual([], check_repository(REPOSITORY_ROOT))


if __name__ == "__main__":
    unittest.main()
