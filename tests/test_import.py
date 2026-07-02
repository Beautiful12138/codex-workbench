from __future__ import annotations

import re
import unittest

import codex_workbench


class ImportSmokeTests(unittest.TestCase):
    def test_version_is_semver_like(self) -> None:
        self.assertRegex(codex_workbench.__version__, re.compile(r"^\d+\.\d+\.\d+$"))


if __name__ == "__main__":
    unittest.main()
