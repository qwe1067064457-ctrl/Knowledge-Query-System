from __future__ import annotations

import unittest

from helpers import BACKEND_DIR, TEST_TMP_ROOT, temp_workspace, write_group_meta

from memory_system.policy_loader import MemoryPolicyLoader


class MemoryPolicyLoaderTests(unittest.TestCase):
    @classmethod
    def tearDownClass(cls) -> None:
        try:
            TEST_TMP_ROOT.rmdir()
        except OSError:
            pass

    def test_load_policy_falls_back_to_default_when_group_meta_missing(self) -> None:
        with temp_workspace() as workspace:
            loader = MemoryPolicyLoader(workspace / "storage", package_dir=BACKEND_DIR / "memory_system")

            policy = loader.load_policy("law")

            self.assertIn("core", policy)
            self.assertIn("daily_log", policy)
            self.assertIn("domain_case", policy)
            self.assertTrue(policy["daily_log"]["checkpoint_enabled"])
            self.assertIn("enabled_memory_types", policy)

    def test_load_policy_deep_merges_group_override_into_default(self) -> None:
        with temp_workspace() as workspace:
            write_group_meta(
                workspace,
                "law",
                {
                    "enabled_memory_types": ["core", "daily_log"],
                    "core": {
                        "explicit_markers": ["ALWAYS", "DEFAULT"],
                        "min_candidate_length": 2,
                    },
                    "daily_log": {"checkpoint_enabled": False},
                },
            )
            loader = MemoryPolicyLoader(workspace / "storage", package_dir=BACKEND_DIR / "memory_system")

            policy = loader.load_policy("law")

            self.assertEqual(policy["enabled_memory_types"], ["core", "daily_log"])
            self.assertEqual(policy["core"]["explicit_markers"], ["ALWAYS", "DEFAULT"])
            self.assertEqual(policy["core"]["min_candidate_length"], 2)
            self.assertIn("max_candidate_length", policy["core"])
            self.assertFalse(policy["daily_log"]["checkpoint_enabled"])
            self.assertIn("completion_markers", policy["domain_case"])

    def test_load_policy_ignores_invalid_group_meta_json(self) -> None:
        with temp_workspace() as workspace:
            meta_path = workspace / "storage" / "groups" / "law" / "meta.json"
            meta_path.parent.mkdir(parents=True, exist_ok=True)
            meta_path.write_text("{not-valid-json", encoding="utf-8")
            loader = MemoryPolicyLoader(workspace / "storage", package_dir=BACKEND_DIR / "memory_system")

            policy = loader.load_policy("law")

            self.assertTrue(policy["daily_log"]["checkpoint_enabled"])
            self.assertIn("core", policy)
            self.assertIn("domain_case", policy)


if __name__ == "__main__":
    unittest.main()
