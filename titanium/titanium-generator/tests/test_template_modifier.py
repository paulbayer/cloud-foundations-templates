"""
Unit tests for TemplateModifier class.

Tests parameter naming validation and classification for Titanium Generator.
"""

import unittest
from titanium_generator.template_modifier import TemplateModifier


class TestTemplateModifierParameterPatterns(unittest.TestCase):
    """Test parameter pattern matching and validation."""

    def setUp(self):
        """Set up test fixtures."""
        self.modifier = TemplateModifier()

    def test_backup_policy_deploy_parameter(self):
        """Test backup policy deployment toggle parameters."""
        test_params = [
            "tDeployWeeklyBackup",
            "tDeployDailyBackup",
            "tDeployMonthlyBackup",
        ]

        for param in test_params:
            with self.subTest(param=param):
                classification = self.modifier.classify_parameter(param)
                self.assertEqual(classification, "titanium", f"Parameter {param} should be classified as 'titanium'")

    def test_backup_policy_description_parameter(self):
        """Test backup policy description parameters."""
        test_params = [
            "tWeeklyBackupDescription",
            "tDailyBackupDescription",
            "tMonthlyBackupDescription",
        ]

        for param in test_params:
            with self.subTest(param=param):
                classification = self.modifier.classify_parameter(param)
                self.assertEqual(classification, "titanium", f"Parameter {param} should be classified as 'titanium'")

    def test_backup_policy_targets_parameter(self):
        """Test backup policy targets parameters."""
        test_params = [
            "uWeeklyBackupTargets",
            "uDailyBackupTargets",
            "uMonthlyBackupTargets",
        ]

        for param in test_params:
            with self.subTest(param=param):
                classification = self.modifier.classify_parameter(param)
                self.assertEqual(classification, "user", f"Parameter {param} should be classified as 'user'")

    def test_tagging_policy_deploy_parameter(self):
        """Test tagging policy deployment toggle parameters."""
        test_params = [
            "tDeployRequiredTags",
            "tDeployOptionalTags",
            "tDeployDataClassification",
        ]

        for param in test_params:
            with self.subTest(param=param):
                classification = self.modifier.classify_parameter(param)
                self.assertEqual(classification, "titanium", f"Parameter {param} should be classified as 'titanium'")

    def test_tagging_policy_description_parameter(self):
        """Test tagging policy description parameters."""
        test_params = [
            "tRequiredTagsDescription",
            "tOptionalTagsDescription",
            "tDataClassificationDescription",
        ]

        for param in test_params:
            with self.subTest(param=param):
                classification = self.modifier.classify_parameter(param)
                self.assertEqual(classification, "titanium", f"Parameter {param} should be classified as 'titanium'")

    def test_tagging_policy_targets_parameter(self):
        """Test tagging policy targets parameters."""
        test_params = [
            "uRequiredTagsTargets",
            "uOptionalTagsTargets",
            "uDataClassificationTargets",
        ]

        for param in test_params:
            with self.subTest(param=param):
                classification = self.modifier.classify_parameter(param)
                self.assertEqual(classification, "user", f"Parameter {param} should be classified as 'user'")

    def test_validate_backup_policy_parameters(self):
        """Test validation of backup policy parameters."""
        test_params = {
            "tDeployWeeklyBackups": {"Type": "String"},
            "tWeeklyBackupsDescription": {"Type": "String"},
            "uWeeklyBackupsTargets": {"Type": "CommaDelimitedList"},
        }

        errors = self.modifier.validate_parameter_naming(test_params)
        self.assertEqual(len(errors), 0, f"Backup policy parameters should validate without errors. Got: {errors}")

    def test_validate_tagging_policy_parameters(self):
        """Test validation of tagging policy parameters."""
        test_params = {
            "tDeployRequiredTags": {"Type": "String"},
            "tRequiredTagsDescription": {"Type": "String"},
            "uRequiredTagsTargets": {"Type": "CommaDelimitedList"},
        }

        errors = self.modifier.validate_parameter_naming(test_params)
        self.assertEqual(len(errors), 0, f"Tagging policy parameters should validate without errors. Got: {errors}")

    def test_validate_mixed_policy_parameters(self):
        """Test validation of mixed backup and tagging policy parameters."""
        test_params = {
            "tDeployWeeklyBackups": {"Type": "String"},
            "tWeeklyBackupsDescription": {"Type": "String"},
            "uWeeklyBackupsTargets": {"Type": "CommaDelimitedList"},
            "tDeployRequiredTags": {"Type": "String"},
            "tRequiredTagsDescription": {"Type": "String"},
            "uRequiredTagsTargets": {"Type": "CommaDelimitedList"},
        }

        errors = self.modifier.validate_parameter_naming(test_params)
        self.assertEqual(len(errors), 0, f"Mixed policy parameters should validate without errors. Got: {errors}")

    def test_classification_is_by_prefix_not_suffix(self):
        """Classification is determined by the t/u first character, not a suffix pattern."""
        # Any 't'-prefixed name classifies as titanium (no per-suffix allowlist).
        self.assertEqual(self.modifier.classify_parameter("tWeeklyBackupsDesc"), "titanium")
        # Any 'u'-prefixed name classifies as user.
        self.assertEqual(self.modifier.classify_parameter("uSomethingArbitrary"), "user")
        # Names without a t/u prefix remain unknown.
        self.assertEqual(self.modifier.classify_parameter("DeployControlTower"), "unknown")


class TestFormatParameterValue(unittest.TestCase):
    """Boolean defaults must be quoted (Type: String params); numbers must not (#62)."""

    def setUp(self):
        self.modifier = TemplateModifier()

    def test_boolean_defaults_are_quoted(self):
        # Type: String params with AllowedValues ["true","false"] need the quoted
        # string, else an unquoted YAML bool trips cfn-lint E2015.
        self.assertEqual(self.modifier._format_parameter_value("true"), '"true"')
        self.assertEqual(self.modifier._format_parameter_value("false"), '"false"')

    def test_boolean_defaults_are_quoted_case_insensitive(self):
        self.assertEqual(self.modifier._format_parameter_value("True"), '"True"')
        self.assertEqual(self.modifier._format_parameter_value("FALSE"), '"FALSE"')

    def test_numeric_defaults_stay_unquoted(self):
        # Type: Number params must keep numeric (unquoted) defaults.
        self.assertEqual(self.modifier._format_parameter_value("365"), "365")
        self.assertEqual(self.modifier._format_parameter_value("0"), "0")

    def test_plain_strings_are_quoted(self):
        self.assertEqual(self.modifier._format_parameter_value("Workloads"), '"Workloads"')


if __name__ == "__main__":
    unittest.main()
