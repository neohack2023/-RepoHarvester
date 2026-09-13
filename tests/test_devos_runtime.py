import unittest

from tools.validate_devos import load_branches, load_project, validate


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


if __name__ == "__main__":
    unittest.main()
