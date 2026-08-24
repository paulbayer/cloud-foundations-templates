"""
Process all CloudFormation templates MCP tool.

This tool processes all CloudFormation templates in a directory based on 
Titanium configuration using the simplified architecture.
"""

import os
import yaml
import re
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Set
from ..config_parser import TitaniumConfigParser
from ..processor_registry import ProcessorRegistry
from ..template_modifier import TemplateModifier
from ..automation_registry import AutomationRegistry, AutomationRegistryError
#from .enhanced_deployment_guide import EnhancedDeploymentGuideGenerator
from .llm_agent_guide import LLMAgentGuideGenerator

logger = logging.getLogger(__name__)


def _log_template_decisions(config: Dict[str, Any], skipped_templates: List[Dict[str, str]]) -> None:
    """
    Log template generation decisions.
    
    Args:
        config: Titanium configuration
        skipped_templates: List of skipped templates with reasons
    """
    is_control_tower_enabled = TitaniumConfigParser.get_control_tower_enabled(config)

    logger.info("=" * 80)
    logger.info("Template Generation Decisions")
    logger.info("=" * 80)
    logger.info(f"Control Tower Enabled: {is_control_tower_enabled}")
    logger.info(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("")

    # Log Config role decision (always generated)
    logger.info("Decision: GENERATE 01-config-stack-mgmt-role.yaml")
    logger.info("  Reason: Config role always generated - may be needed for management account Config setup")
    
    # Log any other skipped templates
    if skipped_templates:
        logger.info("")
        logger.info("Additional skipped templates:")
        for skipped in skipped_templates:
            logger.info(f"  - {skipped['name']}: {skipped['reason']}")
    
    logger.info("=" * 80)

def _log_categorized_summary(processing_results: Dict[str, Any]) -> None:
    """
    Log a categorized console summary grouping sections by automation status.

    Sections are split into two groups:
    - Fully automated (✓)
    - Manual / partially automated (📝)

    Args:
        processing_results: Dict mapping section names to their result dicts,
            each optionally containing an 'automation_status' sub-dict.
    """
    fully_automated = []
    needs_manual = []

    for section_name, result in processing_results.items():
        auto_status = result.get('automation_status')
        if auto_status is None:
            continue
        entry = {
            'name': section_name,
            'status': auto_status['status'],
            'indicator': auto_status['indicator'],
            'automated_percentage': auto_status.get('automated_percentage', 0),
            'manual_subsections': auto_status.get('manual_subsections', []),
            'templates_processed': result.get('templates_processed', 0),
        }
        if auto_status['status'] == 'fully_automated':
            fully_automated.append(entry)
        else:
            needs_manual.append(entry)

    logger.info("")
    logger.info("=" * 80)
    logger.info("Automation Status Summary")
    logger.info("=" * 80)

    if fully_automated:
        logger.info("")
        logger.info("Fully Automated Sections:")
        for entry in fully_automated:
            logger.info(
                "  %s %s  (%d templates generated)",
                entry['indicator'],
                entry['name'],
                entry['templates_processed'],
            )

    if needs_manual:
        logger.info("")
        logger.info("Manual / Partially Automated Sections:")
        for entry in needs_manual:
            pct = entry['automated_percentage']
            manual_subs = entry['manual_subsections']
            logger.info(
                "  %s %s  (%d%% automated, %d templates generated)",
                entry['indicator'],
                entry['name'],
                pct,
                entry['templates_processed'],
            )
            if manual_subs:
                logger.info(
                    "      Manual subsections: %s",
                    ", ".join(manual_subs),
                )

    total = len(fully_automated) + len(needs_manual)
    logger.info("")
    logger.info(
        "Total: %d sections  |  %d fully automated  |  %d need manual steps",
        total,
        len(fully_automated),
        len(needs_manual),
    )
    logger.info("=" * 80)



def _record_skipped(
    section_results: Dict[str, Any],
    skipped_templates: List[Dict[str, str]],
    template_name: str,
    template_path: Path,
    output_path: Path,
    skip_reason: str,
) -> None:
    """Record a skipped template in both the run-wide and per-section result sets."""
    logger.info(f"Skipping {template_name}: {skip_reason}")

    skipped_templates.append({
        'name': template_name,
        'reason': skip_reason,
    })

    section_results['files'].append({
        'name': template_name,
        'original_path': str(template_path),
        'output_path': str(output_path),
        'was_modified': False,
        'skipped': True,
        'skip_reason': skip_reason,
        'modifications': [],
        'size_bytes': 0,
        'validation': {},
    })


def _sort_templates_by_prefix(templates: List[Path]) -> List[Path]:
    """Sort templates by numerical prefix (0-, 1-, 2-, etc.) to ensure proper deployment order."""
    def get_numeric_prefix(path: Path) -> int:
        name = path.name
        if name and name[0].isdigit():
            # Extract number before first dash
            prefix = name.split('-')[0]
            return int(prefix) if prefix.isdigit() else 999
        return 999  # Non-numbered files go last
    
    return sorted(templates, key=get_numeric_prefix)


def process_all_templates(titanium_path: str, output_dir: str, sections: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Process all CloudFormation templates based on Titanium configuration using MCP server's embedded templates.
    
    Args:
        titanium_path: Path to the Titanium.yaml file
        output_dir: Output directory for modified templates
        sections: Optional list of sections to process (processes all if not specified)
        
    Returns:
        Dictionary with processing summary and results
    """
    try:
        # Processors register themselves at import time via processor_registry
        # (imported above), so no explicit per-call import is needed here.

        # Get MCP server's template directory
        template_dir = Path(__file__).parent / "templates"
        
        # Validate input paths
        if not os.path.exists(titanium_path):
            return {
                "success": False,
                "error": f"Titanium config file not found: {titanium_path}",
                "summary": {
                    "total_templates": 0,
                    "successfully_modified": 0,
                    "failed_modifications": 0
                }
            }
        
        if not os.path.exists(template_dir):
            return {
                "success": False,
                "error": f"MCP server template directory not found: {template_dir}",
                "summary": {
                    "total_templates": 0,
                    "successfully_modified": 0,
                    "failed_modifications": 0
                }
            }
        
        # Parse Titanium configuration
        parser = TitaniumConfigParser()
        config = parser.parse_file(titanium_path)
        available_sections = parser.get_available_sections(config)
        
        # Load automation registry for automation status tracking
        try:
            automation_registry = AutomationRegistry()
        except AutomationRegistryError as e:
            return {
                "success": False,
                "error": f"Automation registry error: {e}",
                "summary": {
                    "total_templates": 0,
                    "successfully_modified": 0,
                    "failed_modifications": 0
                }
            }
        
        # Determine sections to process
        if sections:
            # Validate requested sections
            invalid_sections = [s for s in sections if s not in available_sections]
            if invalid_sections:
                return {
                    "success": False,
                    "error": f"Invalid sections requested: {invalid_sections}. Available: {available_sections}",
                    "summary": {
                        "total_templates": 0,
                        "successfully_modified": 0,
                        "failed_modifications": 0
                    }
                }
            sections_to_process = sections
        else:
            sections_to_process = available_sections
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Discover and process templates
        processing_results = {}
        total_templates = 0
        successfully_modified = 0
        failed_modifications = 0
        modified_templates = []
        skipped_templates = []
        errors = []
        
        template_base = Path(template_dir)
        
        # Process each section directory
        for section_dir in sorted(template_base.iterdir()):
            if not section_dir.is_dir() or section_dir.name.startswith('.'):
                continue
                
            section_name = section_dir.name
            section_output_dir = Path(output_dir) / section_name
            section_output_dir.mkdir(exist_ok=True)
            
            # Find templates in this section and sort by numerical prefix
            templates = list(section_dir.glob('*.yaml')) + list(section_dir.glob('*.yml'))
            templates = _sort_templates_by_prefix(templates)
            total_templates += len(templates)
            
            if not templates:
                continue
            
            # Get processor and configuration for this section
            processor = None
            section_config = None
            
            # Map directory names to section types
            section_mapping = {
                'organization': 'organization',
                'security': 'security',
                'network': 'network',
                'bootstrap': 'bootstrap',
                'identity': 'identity', 
                'logging': 'logging',
                'accounts': 'accounts',
                'finance': 'cost_management',
                'cost': 'cost_management',
                'controltower': 'control_tower'
            }
            
            section_type = section_mapping.get(section_name.lower())
            
            if section_type and section_type in sections_to_process:
                processor = ProcessorRegistry.get_processor(section_type)
                section_config = parser.get_section_data(config, section_type)
            
            section_results = {
                'section': section_name,
                'section_type': section_type,
                'templates_found': len(templates),
                'templates_processed': 0,
                'templates_modified': 0,
                'processor_available': processor is not None,
                'config_available': section_config is not None,
                'files': [],
                'errors': []
            }
            
            # Process each template in this section
            for template_path in templates:
                template_name = template_path.name
                output_path = section_output_dir / template_name
                
                # Let the section's processor decide whether this template should
                # be generated for the current configuration (e.g. network skips
                # Network-account templates for minimal configs and picks the
                # correct TGW template). The orchestrator no longer hardcodes
                # per-section filenames — see SimpleProcessor.should_skip_template.
                skip_reason = (
                    processor.should_skip_template(template_name, section_config, config)
                    if processor and section_config
                    else None
                )
                if skip_reason:
                    _record_skipped(
                        section_results, skipped_templates,
                        template_name, template_path, output_path, skip_reason,
                    )
                    continue

                try:
                    # Read original template
                    with open(template_path, 'r', encoding='utf-8') as f:
                        original_content = f.read()
                    
                    modified_content = original_content
                    was_modified = False
                    modifications = []
                    
                    # Apply processor if available
                    if processor and section_config:
                        try:
                            # Set full config for processors that need access to other sections
                            if hasattr(processor, 'set_full_config'):
                                processor.set_full_config(config)
                            
                            # Process template with section configuration
                            modified_content = processor.process(original_content, section_config)
                            modifications = processor.get_modifications()
                            was_modified = len(modifications) > 0
                            
                        except Exception as e:
                            error_msg = f"Processing error for {template_name}: {str(e)}"
                            section_results['errors'].append(error_msg)
                            errors.append(error_msg)
                            modifications = [f"Error during processing: {str(e)}"]
                    
                    # Validate parameter naming convention in the modified template
                    validation_results = {}
                    if modified_content != original_content:
                        try:
                            modifier = TemplateModifier()
                            is_valid, validation_errors, parameter_classifications = modifier.validate_template_parameters(modified_content)
                            validation_results = {
                                'naming_convention_valid': is_valid,
                                'validation_errors': validation_errors,
                                'parameter_classifications': parameter_classifications
                            }
                            
                            if not is_valid:
                                error_msg = f"Parameter naming validation failed for {template_name}: {validation_errors}"
                                section_results['errors'].append(error_msg)
                                
                        except Exception as e:
                            validation_results = {
                                'naming_convention_valid': False,
                                'validation_errors': [f"Validation error: {str(e)}"],
                                'parameter_classifications': {}
                            }
                    
                    # Write output file
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(modified_content)
                    
                    # Record results
                    file_result = {
                        'name': template_name,
                        'original_path': str(template_path),
                        'output_path': str(output_path),
                        'was_modified': was_modified,
                        'modifications': modifications,
                        'size_bytes': len(modified_content),
                        'validation': validation_results
                    }
                    section_results['files'].append(file_result)
                    
                    section_results['templates_processed'] += 1
                    
                    if was_modified:
                        section_results['templates_modified'] += 1
                        successfully_modified += 1
                        modified_templates.append(str(output_path))
                    
                except Exception as e:
                    failed_modifications += 1
                    error_msg = f"Failed to process {template_name}: {str(e)}"
                    section_results['errors'].append(error_msg)
                    errors.append(error_msg)
            
            # Annotate section results with automation status from registry
            registry_key = section_type or section_name
            try:
                section_status = automation_registry.get_section_status(registry_key)
                manual_subsections = [
                    sub.name
                    for sub in section_status.subsections
                    if sub.status == "manual"
                ]
                section_results['automation_status'] = {
                    'status': section_status.status,
                    'automated_percentage': section_status.automated_percentage,
                    'indicator': '✓' if section_status.status == 'fully_automated' else '📝',
                    'manual_subsections': manual_subsections,
                }
            except KeyError:
                logger.warning(
                    "Section '%s' not found in automation registry; skipping annotation",
                    registry_key,
                )

            processing_results[section_name] = section_results
        
        # Log categorized automation status summary
        _log_categorized_summary(processing_results)

        # Generate processing report
        report_data = {
            'titanium_config_file': titanium_path,
            'template_directory': str(template_dir),
            'output_directory': output_dir,
            'sections_requested': sections_to_process,
            'available_sections': available_sections,
            'active_processors': ProcessorRegistry.get_supported_sections(),
            'summary': {
                'total_templates': total_templates,
                'successfully_modified': successfully_modified,
                'failed_modifications': failed_modifications,
                'sections_processed': len([r for r in processing_results.values() if r['templates_processed'] > 0])
            },
            'section_results': processing_results,
            'errors': errors,
            'modified_templates': modified_templates
        }
        
        # Save processing report
        report_path = Path(output_dir) / 'processing_report.yaml'
        with open(report_path, 'w', encoding='utf-8') as f:
            yaml.dump(report_data, f, default_flow_style=False, sort_keys=False)
        
        # Log template generation decisions
        _log_template_decisions(config, skipped_templates)
        
        # Generate LLM agent interactive deployment guide (includes Control Tower decision matrix)
        llm_agent_generator = LLMAgentGuideGenerator()
        llm_agent_guide_path = llm_agent_generator.generate_agent_guide(
            config, processing_results, output_dir
        )
        report_data['llm_agent_guide_path'] = str(llm_agent_guide_path)
        
        return {
            "success": True,
            "summary": {
                "total_templates": total_templates,
                "successfully_modified": successfully_modified,
                "failed_modifications": failed_modifications,
                "skipped_templates": total_templates - successfully_modified - failed_modifications
            },
            "modified_templates": modified_templates,
            "errors": errors,
            "report_path": str(report_path),
            "llm_agent_guide_path": str(llm_agent_guide_path),
            "metadata": {
                "sections_processed": list(processing_results.keys()),
                "active_processors": ProcessorRegistry.get_supported_sections(),
                "output_directory": output_dir,
                "processing_mode": "simplified_architecture",
                "guides_generated": {
                    "llm_agent_guide": str(llm_agent_guide_path),
                    "llm_agent_json": str(Path(output_dir) / 'llm_agent_steps.json')
                }
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "summary": {
                "total_templates": 0,
                "successfully_modified": 0,
                "failed_modifications": 1
            },
            "modified_templates": [],
            "errors": [str(e)],
            "report_path": None
        }
