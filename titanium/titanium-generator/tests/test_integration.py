#!/usr/bin/env python3
"""
Integration test script for template naming standardization.
Tests deployment guide generation with renamed templates.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from titanium_generator.mcp_tools.process_templates import process_all_templates

def main():
    """Run integration test for deployment guide generation."""
    
    # Use the sample Titanium.yaml file
    titanium_path = "/Users/amirasf/Documents/GenAI Thingies/deep-research-folder/landing-zone/Titanium_sample.yaml"
    
    # Output directory for test
    output_dir = str(Path(__file__).parent / "test_output")
    
    print("=" * 80)
    print("Integration Test: Deployment Guide Generation")
    print("=" * 80)
    print(f"Titanium Config: {titanium_path}")
    print(f"Output Directory: {output_dir}")
    print()
    
    # Process templates and generate deployment guide
    print("Processing templates and generating deployment guide...")
    result = process_all_templates(titanium_path, output_dir)
    
    print()
    print("=" * 80)
    print("Results:")
    print("=" * 80)
    print(f"Success: {result['success']}")
    print(f"Total Templates: {result['summary']['total_templates']}")
    print(f"Successfully Modified: {result['summary']['successfully_modified']}")
    print(f"Failed: {result['summary']['failed_modifications']}")
    print(f"Skipped: {result['summary']['skipped_templates']}")
    
    if result.get('llm_agent_guide_path'):
        print(f"\nLLM Agent Guide: {result['llm_agent_guide_path']}")
        
        # Read and display first 100 lines of the guide
        guide_path = Path(result['llm_agent_guide_path'])
        if guide_path.exists():
            print("\nFirst 100 lines of deployment guide:")
            print("-" * 80)
            with open(guide_path, 'r') as f:
                lines = f.readlines()[:100]
                print(''.join(lines))
            print("-" * 80)
            print(f"Total lines in guide: {len(open(guide_path).readlines())}")
    
    if result.get('errors'):
        print("\nErrors:")
        for error in result['errors']:
            print(f"  - {error}")
    
    print()
    print("=" * 80)
    print("Test completed!")
    print("=" * 80)
    
    return 0 if result['success'] else 1

if __name__ == '__main__':
    sys.exit(main())
