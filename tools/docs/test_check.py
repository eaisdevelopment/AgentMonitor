"""Real-checkout tests for repository documentation validation."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from check import check_repository  # noqa: E402


class DocumentationCheckTests(unittest.TestCase):
    def test_real_repository_documentation_is_internally_resolvable(self) -> None:
        self.assertEqual([], check_repository(REPOSITORY_ROOT))

    def test_ignores_vendor_markdown_with_broken_link(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "README.md").write_text("# Project\n", encoding="utf-8")
            (root / "docs/product").mkdir(parents=True)
            (root / "docs/plans").mkdir()
            (root / "docs/product/requirements.md").write_text(
                "# Requirements\n\nNFR-DOC-001\n", encoding="utf-8"
            )
            (root / "docs/product/v1-acceptance-criteria.md").write_text(
                "# Acceptance criteria\n\nAC-TEST-001\n", encoding="utf-8"
            )
            (root / "docs/plans/contract-baseline.toml").write_text(
                '[[contracts]]\nid = "CTR-FND-001"\n', encoding="utf-8"
            )
            (root / "docs/project.md").write_text(
                "# Project documentation\n\n[Repository](../README.md)\n",
                encoding="utf-8",
            )
            vendor_markdown = root / "frontend/node_modules/vendor/README.md"
            vendor_markdown.parent.mkdir(parents=True)
            vendor_markdown.write_text(
                "[Broken vendor link](missing.md)\n", encoding="utf-8"
            )

            self.assertEqual([], check_repository(root))


if __name__ == "__main__":
    unittest.main()
