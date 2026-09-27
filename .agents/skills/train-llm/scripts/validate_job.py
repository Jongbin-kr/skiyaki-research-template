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
    
    # TODO: Implement validation logic in subsequent subtasks
    # This is just the CLI interface implementation for subtask 6.1
    
    return result


def main() -> int:
    """Main entry point for the script."""
    parser = create_parser()
    args = parser.parse_args()
    
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
