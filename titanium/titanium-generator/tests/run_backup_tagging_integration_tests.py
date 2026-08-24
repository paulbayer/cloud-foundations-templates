#!/usr/bin/env python3
"""
Run integration tests for backup and tagging policies.
This script validates the complete workflow from Titanium.yaml to modified templates.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from titanium_generator.config_parser import TitaniumConfigParser
from titanium_generator.processors.organization_processor import SimpleOrganizationProcessor
from titanium_generator.mcp_tools.process_templates import process_all_templates
import tempfile
import shutil


def test_parse_backup_policies():
    """Test parsing Titanium.yaml with backup policies."""
    print("\n" + "=" * 80)
    print("Test: Parse Backup Policies")
    print("=" * 80)
    
    config_path = Path(__file__).parent / "test_data" / "test_backup_policies.yaml"
    parser = TitaniumConfigParser()
    config = parser.parse_file(str(config_path))
    
    assert 'organization' in config, "Config should have organization section"
    assert 'backupPolicies' in config['organization'], "Organization should have backupPolicies"
    assert len(config['organization']['backupPolicies']) == 2, "Should have 2 backup policies"
    
    daily_backup = config['organization']['backupPolicies'][0]
    assert daily_backup['name'] == 'DailyBackup', "First policy should be DailyBackup"
    assert daily_backup['description'] == 'Daily backups with 30-day retention'
    
    print("✅ Successfully parsed backup policies from Titanium.yaml")
    return True


def test_parse_tagging_policies():
    """Test parsing Titanium.yaml with tagging policies."""
    print("\n" + "=" * 80)
    print("Test: Parse Tagging Policies")
    print("=" * 80)
    
    config_path = Path(__file__).parent / "test_data" / "test_tagging_policies.yaml"
    parser = TitaniumConfigParser()
    config = parser.parse_file(str(config_path))
    
    assert 'organization' in config
    assert 'taggingPolicies' in config['organization']
    assert len(config['organization']['taggingPolicies']) == 2
    
    required_tags = config['organization']['taggingPolicies'][0]
    assert required_tags['name'] == 'RequiredTags'
    
    print("✅ Successfully parsed tagging policies from Titanium.yaml")
    return True


def test_extract_backup_policies():
    """Test extracting backup policy items from organization processor."""
    print("\n" + "=" * 80)
    print("Test: Extract Backup Policies")
    print("=" * 80)
    
    config_path = Path(__file__).parent / "test_data" / "test_backup_policies.yaml"
    parser = TitaniumConfigParser()
    config = parser.parse_file(str(config_path))
    
    processor = SimpleOrganizationProcessor('organization')
    processor.set_full_config(config)
    items = processor.extract_items(config['organization'])
    
    backup_items = [item for item in items if item['type'] == 'backup_policy']
    assert len(backup_items) == 2, f"Should have 2 backup policy items, got {len(backup_items)}"
    
    daily_item = next((item for item in backup_items if item['name'] == 'DailyBackup'), None)
    assert daily_item is not None, "Should find DailyBackup item"
    assert daily_item['enabled'] is True
    
    print(f"✅ Successfully extracted {len(backup_items)} backup policy items")
    return True


def test_generate_backup_policy_parameters():
    """Test parameter generation for backup policies."""
    print("\n" + "=" * 80)
    print("Test: Generate Backup Policy Parameters")
    print("=" * 80)
    
    config_path = Path(__file__).parent / "test_data" / "test_backup_policies.yaml"
    parser = TitaniumConfigParser()
    config = parser.parse_file(str(config_path))
    
    processor = SimpleOrganizationProcessor('organization')
    processor.set_full_config(config)
    items = processor.extract_items(config['organization'])
    
    backup_items = [item for item in items if item['type'] == 'backup_policy']
    daily_item = next(item for item in backup_items if item['name'] == 'DailyBackup')
    
    parameters = processor.generate_parameter_updates([daily_item])
    
    assert 'tDeployDailyBackup' in parameters, "Should have tDeployDailyBackup parameter"
    assert parameters['tDeployDailyBackup'] == 'true'
    
    print(f"✅ Successfully generated {len(parameters)} parameters for DailyBackup policy")
    return True


def test_end_to_end_backup_policies():
    """Test complete end-to-end flow for backup policies."""
    print("\n" + "=" * 80)
    print("Test: End-to-End Backup Policies")
    print("=" * 80)
    
    config_path = Path(__file__).parent / "test_data" / "test_backup_policies.yaml"
    temp_dir = tempfile.mkdtemp()
    
    try:
        result = process_all_templates(
            str(config_path),
            temp_dir,
            sections=['organization']
        )
        
        assert result['success'] is True, "Template processing should succeed"
        
        backup_template_path = Path(temp_dir) / 'organization' / '03-organizations-stack-mgmt-backup-policies.yaml'
        assert backup_template_path.exists(), "Backup policies template should be generated"
        
        with open(backup_template_path, 'r') as f:
            template_text = f.read()
        
        assert 'tDeployDailyBackup:' in template_text
        assert 'Daily backups with 30-day retention' in template_text
        
        print("✅ End-to-end backup policies workflow completed successfully")
        return True
        
    finally:
        shutil.rmtree(temp_dir)


def test_end_to_end_tagging_policies():
    """Test complete end-to-end flow for tagging policies."""
    print("\n" + "=" * 80)
    print("Test: End-to-End Tagging Policies")
    print("=" * 80)
    
    config_path = Path(__file__).parent / "test_data" / "test_tagging_policies.yaml"
    temp_dir = tempfile.mkdtemp()
    
    try:
        result = process_all_templates(
            str(config_path),
            temp_dir,
            sections=['organization']
        )
        
        assert result['success'] is True
        
        tagging_template_path = Path(temp_dir) / 'organization' / '04-organizations-stack-mgmt-tagging-policies.yaml'
        assert tagging_template_path.exists()
        
        with open(tagging_template_path, 'r') as f:
            template_text = f.read()
        
        assert 'tDeployRequiredTags:' in template_text
        
        print("✅ End-to-end tagging policies workflow completed successfully")
        return True
        
    finally:
        shutil.rmtree(temp_dir)


def main():
    """Run all integration tests."""
    
    print("=" * 80)
    print("Backup and Tagging Policies - Integration Test Suite")
    print("=" * 80)
    
    tests = [
        (test_parse_backup_policies, "Parse Backup Policies"),
        (test_parse_tagging_policies, "Parse Tagging Policies"),
        (test_extract_backup_policies, "Extract Backup Policies"),
        (test_generate_backup_policy_parameters, "Generate Parameters"),
        (test_end_to_end_backup_policies, "End-to-End Backup"),
        (test_end_to_end_tagging_policies, "End-to-End Tagging"),
    ]
    
    results = {}
    
    for test_func, test_name in tests:
        try:
            success = test_func()
            results[test_name] = success
        except Exception as e:
            print(f"❌ {test_name} FAILED: {e}")
            import traceback
            traceback.print_exc()
            results[test_name] = False
    
    print("\n" + "=" * 80)
    print("INTEGRATION TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for success in results.values() if success)
    total = len(results)
    
    for test_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print("=" * 80)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 80)
    
    if passed == total:
        print("\n🎉 All integration tests PASSED!")
        return 0
    else:
        print(f"\n❌ {total - passed} test(s) failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())
