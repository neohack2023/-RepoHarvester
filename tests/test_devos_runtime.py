import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.validate_devos import (
    ROOT,
    find_source_leaks,
    load_branches,
    load_project,
    sha256_file,
    validate,
)


class RepoHarvesterDevOSTests(unittest.TestCase):
    def test_project_identity(self):
        project = load_project()
        self.assertEqual(project["scope_key"], "repo-harvester")
        self.assertEqual(project["repository"], "neohack2023/-RepoHarvester")
        self.assertEqual(
            project["default_agent"], "REPOHARVESTER-DEV-ORCHESTRATOR"
        )

    def test_feature_cells_are_routable(self):
        branches = {row["branch_key"] for row in load_branches()}
        self.assertTrue({"code-units", "relationships", "storage"} <= branches)

    def test_installation_validates(self):
        count, errors = validate()
        self.assertGreaterEqual(count, 6)
        self.assertEqual(errors, [])

    def test_governance_hash_is_line_ending_stable(self):
        with tempfile.TemporaryDirectory() as directory:
            lf = Path(directory) / "lf.json"
            crlf = Path(directory) / "crlf.json"
            lf.write_bytes(b'{\n  "state": "active"\n}\n')
            crlf.write_bytes(b'{\r\n  "state": "active"\r\n}\r\n')
            self.assertEqual(sha256_file(lf), sha256_file(crlf))

    def test_source_project_terms_do_not_leak(self):
        portability = load_project()["portability"]
        self.assertEqual(
            find_source_leaks(
                ROOT,
                portability["forbidden_source_terms"],
                portability["allowed_provenance_paths"],
            ),
            [],
        )

    def test_reflection_tools_support_direct_execution(self):
        for script in ("diagnostic_reflection.py", "delta_reflection.py"):
            result = subprocess.run(
                [sys.executable, str(ROOT / "tools" / script), "--help"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
