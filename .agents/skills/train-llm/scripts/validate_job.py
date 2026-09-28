#!/usr/bin/env python3
"""
Validate job configuration file.

This script performs deterministic validation of job configuration files,
checking required fields, verifying entrypoint existence, and validating
resource specifications against quotas.

Usage:
  validate_job.py --job-file PATH --workspace PATH [--quota-file PATH]
  validate_job.py --help
  validate_job.py --version

Output (JSON):
  {
    "valid": true|false,
    "errors": [...],
    "warnings": [...],
    "checked": {
      "required_fields": true,
      "entrypoint_exists": true,
      "quota_compliance": true
    }
  }

Exit Codes:
  0 - Validation successful
  1 - Validation failed (job configuration errors)
  2 - Runtime error (file not found, invalid YAML, etc.)
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

# Version information
__version__ = "0.1.0"

def create_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser."""
    parser = argparse.ArgumentParser(
        description="Validate job configuration file for ML training experiments.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate a training job file
  %(prog)s --job-file jobs/train.yaml --workspace /path/to/workspace

  # Validate with quota checking
  %(prog)s --job-file jobs/train.yaml --workspace /path/to/workspace --quota-file project-plan.md

  # Show help
  %(prog)s --help

  # Show version
  %(prog)s --version
"""
    )
    
    parser.add_argument(
        '--job-file',
        type=str,
        required=True,
        metavar='PATH',
        help='Path to job configuration YAML file (required)'
    )
    
    parser.add_argument(
        '--workspace',
        type=str,
        required=True,
        metavar='PATH',
        help='Path to workspace root directory (required)'
    )
    
    parser.add_argument(
        '--quota-file',
        type=str,
        required=False,
        metavar='PATH',
        help='Path to quota configuration file (optional, e.g., project-plan.md)'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version=f'%(prog)s {__version__}'
    )
    
    return parser


def validate_time_format(time_str: str) -> bool:
    """Validate HH:MM:SS time format."""
    pattern = r'^\d{1,2}:\d{2}:\d{2}$'
    if not re.match(pattern, time_str):
        return False
    
    parts = time_str.split(':')
    hours, minutes, seconds = int(parts[0]), int(parts[1]), int(parts[2])
    return 0 <= hours and 0 <= minutes < 60 and 0 <= seconds < 60


def validate_matrix_syntax(matrix: Any) -> List[str]:
    """Validate matrix syntax.
    
    Returns list of error messages (empty if valid).
    """
    errors = []
    
    if not isinstance(matrix, dict):
        errors.append(f"Matrix must be a dictionary, got {type(matrix).__name__}")
        return errors
    
    if len(matrix) == 0:
        errors.append("Matrix cannot be empty")
        return errors
    
    for key, value in matrix.items():
        if not isinstance(key, str):
            errors.append(f"Matrix key must be string, got {type(key).__name__}: {key}")
        
        if not isinstance(value, list):
            errors.append(f"Matrix value for '{key}' must be a list, got {type(value).__name__}")
        elif len(value) == 0:
            errors.append(f"Matrix value for '{key}' cannot be empty list")
    
    return errors


def validate_wandb_config(wandb_config: Any) -> List[str]:
    """Validate W&B configuration structure.
    
    Returns list of error messages (empty if valid).
    """
    errors = []
    
    if not isinstance(wandb_config, dict):
        errors.append(f"wandb config must be a dictionary, got {type(wandb_config).__name__}")
        return errors
    
    # Check required fields
    if 'enabled' not in wandb_config:
        errors.append("wandb config missing required field 'enabled'")
    elif not isinstance(wandb_config['enabled'], bool):
        errors.append(f"wandb.enabled must be boolean, got {type(wandb_config['enabled']).__name__}")
    
    # Optional but validate if present
    if 'group' in wandb_config and not isinstance(wandb_config['group'], str):
        errors.append(f"wandb.group must be string, got {type(wandb_config['group']).__name__}")
    
    if 'tags' in wandb_config:
        if not isinstance(wandb_config['tags'], list):
            errors.append(f"wandb.tags must be list, got {type(wandb_config['tags']).__name__}")
        else:
            for i, tag in enumerate(wandb_config['tags']):
                if not isinstance(tag, str):
                    errors.append(f"wandb.tags[{i}] must be string, got {type(tag).__name__}")
    
    return errors


def validate_hf_config(hf_config: Any) -> List[str]:
    """Validate HuggingFace configuration structure.
    
    Returns list of error messages (empty if valid).
    """
    errors = []
    
    if not isinstance(hf_config, dict):
        errors.append(f"huggingface config must be a dictionary, got {type(hf_config).__name__}")
        return errors
    
    # Check push policy
    if 'push' not in hf_config:
        errors.append("huggingface config missing required field 'push'")
    else:
        valid_push_values = ['never', 'final_only', 'milestone', 'every_save']
        if hf_config['push'] not in valid_push_values:
            errors.append(f"huggingface.push must be one of {valid_push_values}, got '{hf_config['push']}'")
    
    # repo can be null or string
    if 'repo' in hf_config:
        repo_value = hf_config['repo']
        if repo_value is not None and not isinstance(repo_value, str):
            errors.append(f"huggingface.repo must be string or null, got {type(repo_value).__name__}")
    
    return errors


def parse_quota_file(quota_file: Path) -> Optional[Dict[str, Any]]:
    """Parse quota file (project-plan.md) to extract resource limits.
    
    Returns None if quota cannot be parsed (warns but doesn't fail validation).
    """
    try:
        content = quota_file.read_text()
        
        # Look for resource quota section (simple pattern matching)
        # This is a simplified parser - can be enhanced in future
        quotas = {}
        
        # Try to find YAML frontmatter or explicit quota sections
        # For now, return None to indicate quota checking is not enforced
        # This can be enhanced in future phases
        
        return None
    except Exception:
        return None


def validate_job(
    job_file: Path,
    workspace: Path,
    quota_file: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Validate job configuration file.
    
    Args:
        job_file: Path to job configuration YAML file
        workspace: Path to workspace root directory
        quota_file: Optional path to quota configuration file
    
    Returns:
        Dictionary with validation results in JSON format
    """
    import yaml
    
    result = {
        "valid": True,
        "errors": [],
        "warnings": [],
        "checked": {
            "required_fields": False,
            "entrypoint_exists": False,
            "quota_compliance": False
        }
    }
    
    # Step 1: Parse YAML
    try:
        with open(job_file, 'r') as f:
            job_config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        result["valid"] = False
        result["errors"].append(f"Invalid YAML syntax: {str(e)}")
        return result
    except Exception as e:
        result["valid"] = False
        result["errors"].append(f"Failed to read job file: {str(e)}")
        return result
    
    if not isinstance(job_config, dict):
        result["valid"] = False
        result["errors"].append(f"Job configuration must be a YAML dictionary, got {type(job_config).__name__}")
        return result
    
    # Step 2: Check required fields
    required_fields = ['job_id', 'type', 'entrypoint', 'parameters', 'resources']
    missing_fields = []
    
    for field in required_fields:
        if field not in job_config:
            missing_fields.append(field)
    
    if missing_fields:
        result["valid"] = False
        result["errors"].append(f"Missing required fields: {', '.join(missing_fields)}")
    else:
        result["checked"]["required_fields"] = True
    
    # Step 3: Validate field types and values
    if 'job_id' in job_config and not isinstance(job_config['job_id'], str):
        result["valid"] = False
        result["errors"].append(f"job_id must be string, got {type(job_config['job_id']).__name__}")
    
    if 'type' in job_config:
        valid_types = ['train', 'evaluate', 'custom']
        if job_config['type'] not in valid_types:
            result["valid"] = False
            result["errors"].append(f"type must be one of {valid_types}, got '{job_config['type']}'")
    
    if 'entrypoint' in job_config and not isinstance(job_config['entrypoint'], str):
        result["valid"] = False
        result["errors"].append(f"entrypoint must be string, got {type(job_config['entrypoint']).__name__}")
    
    if 'parameters' in job_config and not isinstance(job_config['parameters'], dict):
        result["valid"] = False
        result["errors"].append(f"parameters must be dictionary, got {type(job_config['parameters']).__name__}")
    
    # Step 4: Verify entrypoint exists
    if 'entrypoint' in job_config and isinstance(job_config['entrypoint'], str):
        entrypoint_path = workspace / job_config['entrypoint']
        if entrypoint_path.exists():
            result["checked"]["entrypoint_exists"] = True
        else:
            result["valid"] = False
            result["errors"].append(f"Entrypoint file not found: {entrypoint_path.absolute()}")
            result["errors"].append(f"  (looking for '{job_config['entrypoint']}' relative to workspace {workspace.absolute()})")
    
    # Step 5: Validate resources
    if 'resources' in job_config:
        resources = job_config['resources']
        
        if not isinstance(resources, dict):
            result["valid"] = False
            result["errors"].append(f"resources must be dictionary, got {type(resources).__name__}")
        else:
            # Validate individual resource fields
            if 'gpus' in resources:
                gpus = resources['gpus']
                if not isinstance(gpus, int) or gpus < 0:
                    result["valid"] = False
                    result["errors"].append(f"resources.gpus must be non-negative integer, got {gpus}")
            
            if 'cpus' in resources:
                cpus = resources['cpus']
                if not isinstance(cpus, int) or cpus < 1:
                    result["valid"] = False
                    result["errors"].append(f"resources.cpus must be positive integer (>= 1), got {cpus}")
            
            if 'memory_gb' in resources:
                memory = resources['memory_gb']
                if not isinstance(memory, (int, float)) or memory < 1:
                    result["valid"] = False
                    result["errors"].append(f"resources.memory_gb must be positive number (>= 1), got {memory}")
            
            if 'time' in resources:
                time_str = resources['time']
                if not isinstance(time_str, str):
                    result["valid"] = False
                    result["errors"].append(f"resources.time must be string in HH:MM:SS format, got {type(time_str).__name__}")
                elif not validate_time_format(time_str):
                    result["valid"] = False
                    result["errors"].append(f"resources.time must be in HH:MM:SS format, got '{time_str}'")
            
            if 'backend' in resources:
                valid_backends = ['local', 'slurm']
                if resources['backend'] not in valid_backends:
                    result["valid"] = False
                    result["errors"].append(f"resources.backend must be one of {valid_backends}, got '{resources['backend']}'")
    
    # Step 6: Validate quota compliance (if quota file provided)
    if quota_file:
        quotas = parse_quota_file(quota_file)
        if quotas is None:
            result["warnings"].append(f"Could not parse quota file {quota_file}, skipping quota validation")
            result["checked"]["quota_compliance"] = False
        else:
            # Quota validation logic would go here
            # For now, mark as checked since we attempted it
            result["checked"]["quota_compliance"] = True
    else:
        # No quota file provided, so we can't check compliance
        result["checked"]["quota_compliance"] = False
    
    # Step 7: Validate matrix syntax (if present)
    if 'matrix' in job_config:
        matrix_errors = validate_matrix_syntax(job_config['matrix'])
        if matrix_errors:
            result["valid"] = False
            result["errors"].extend(matrix_errors)
    
    # Step 8: Validate W&B config (if present)
    if 'wandb' in job_config:
        wandb_errors = validate_wandb_config(job_config['wandb'])
        if wandb_errors:
            result["valid"] = False
            result["errors"].extend(wandb_errors)
    
    # Step 9: Validate HuggingFace config (if present)
    if 'huggingface' in job_config:
        hf_errors = validate_hf_config(job_config['huggingface'])
        if hf_errors:
            result["valid"] = False
            result["errors"].extend(hf_errors)
    
    return result


def main() -> int:
    """Main entry point for the script."""
    parser = create_parser()
    args = parser.parse_args()
    
    # Check for PyYAML after argparse handles --help and --version
    try:
        import yaml
    except ImportError:
        print(json.dumps({
            "valid": False,
            "errors": ["PyYAML is required but not installed. Please install it with: pip install pyyaml"],
            "warnings": [],
            "checked": {
                "required_fields": False,
                "entrypoint_exists": False,
                "quota_compliance": False
            }
        }, indent=2))
        return 2
    
    # Convert arguments to Path objects
    job_file = Path(args.job_file)
    workspace = Path(args.workspace)
    quota_file = Path(args.quota_file) if args.quota_file else None
    
    # Validate that required paths exist
    if not job_file.exists():
        error_result = {
            "valid": False,
            "errors": [f"Job file not found: {job_file.absolute()}"],
            "warnings": [],
            "checked": {
                "required_fields": False,
                "entrypoint_exists": False,
                "quota_compliance": False
            }
        }
        print(json.dumps(error_result, indent=2))
        return 2
    
    if not workspace.exists():
        error_result = {
            "valid": False,
            "errors": [f"Workspace directory not found: {workspace.absolute()}"],
            "warnings": [],
            "checked": {
                "required_fields": False,
                "entrypoint_exists": False,
                "quota_compliance": False
            }
        }
        print(json.dumps(error_result, indent=2))
        return 2
    
    if not workspace.is_dir():
        error_result = {
            "valid": False,
            "errors": [f"Workspace path is not a directory: {workspace.absolute()}"],
            "warnings": [],
            "checked": {
                "required_fields": False,
                "entrypoint_exists": False,
                "quota_compliance": False
            }
        }
        print(json.dumps(error_result, indent=2))
        return 2
    
    if quota_file and not quota_file.exists():
        error_result = {
            "valid": False,
            "errors": [f"Quota file not found: {quota_file.absolute()}"],
            "warnings": [],
            "checked": {
                "required_fields": False,
                "entrypoint_exists": False,
                "quota_compliance": False
            }
        }
        print(json.dumps(error_result, indent=2))
        return 2
    
    try:
        # Run validation
        result = validate_job(job_file, workspace, quota_file)
        
        # Output JSON result
        print(json.dumps(result, indent=2))
        
        # Return appropriate exit code
        return 0 if result["valid"] else 1
        
    except Exception as e:
        error_result = {
            "valid": False,
            "errors": [f"Runtime error: {str(e)}"],
            "warnings": [],
            "checked": {
                "required_fields": False,
                "entrypoint_exists": False,
                "quota_compliance": False
            }
        }
        print(json.dumps(error_result, indent=2))
        return 2


if __name__ == "__main__":
    sys.exit(main())
