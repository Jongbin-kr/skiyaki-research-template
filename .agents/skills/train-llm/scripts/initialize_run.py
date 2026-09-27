#!/usr/bin/env python3
"""
Initialize run directory and tracking metadata.

This script creates a run directory structure for a training or evaluation job,
generates a unique Run ID, and sets up initial tracking metadata.

Usage:
  initialize_run.py --job-file PATH --experiment-dir PATH [--dry-run] [--help] [--version]

Arguments:
  --job-file PATH         Path to the job configuration YAML file (required)
  --experiment-dir PATH   Path to the experiment directory (required)
  --dry-run               Preview operations without creating files
  --help                  Show this help message and exit
  --version               Show version information and exit

Output (JSON):
  {
    "status": "success" | "error",
    "message": "<human-readable summary>",
    "data": {
      "run_id": "<type>-<job-id>__<timestamp>",
      "run_dir": "<absolute-path>",
      "status": "initialized",
      "created_files": [...],
      "timestamp": "<ISO8601>"
    },
    "errors": [...],
    "warnings": [...]
  }

Exit Codes:
  0 - Success
  1 - Validation error (missing files, invalid configuration)
  2 - Runtime error (file system operations failed)
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Version information
__version__ = "0.1.0"


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Initialize run directory and tracking metadata for ML experiments.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Initialize a training run
  %(prog)s --job-file experiments/my-exp/jobs/train.yaml --experiment-dir experiments/my-exp

  # Preview initialization without creating files
  %(prog)s --job-file jobs/train.yaml --experiment-dir experiments/my-exp --dry-run

  # Show version
  %(prog)s --version
"""
    )
    
    parser.add_argument(
        "--job-file",
        type=str,
        required="--version" not in sys.argv and "--help" not in sys.argv,
        help="Path to the job configuration YAML file"
    )
    
    parser.add_argument(
        "--experiment-dir",
        type=str,
        required="--version" not in sys.argv and "--help" not in sys.argv,
        help="Path to the experiment directory"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview operations without creating files or directories"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Show version information and exit"
    )
    
    return parser.parse_args()


def output_json(
    status: str,
    message: str,
    data: Optional[Dict[str, Any]] = None,
    errors: Optional[List[str]] = None,
    warnings: Optional[List[str]] = None
) -> None:
    """Output structured JSON result to stdout."""
    result = {
        "status": status,
        "message": message,
        "data": data or {},
        "errors": errors or [],
        "warnings": warnings or []
    }
    print(json.dumps(result, indent=2))


def load_yaml(file_path: Path) -> Optional[Dict[str, Any]]:
    """
    Load and parse YAML file.
    
    Args:
        file_path: Path to YAML file
        
    Returns:
        Parsed YAML content as dictionary, or None if parsing fails
    """
    try:
        import yaml
    except ImportError:
        output_json(
            status="error",
            message="PyYAML is required but not installed. Install it with: pip install pyyaml",
            errors=["Missing dependency: PyYAML"]
        )
        sys.exit(2)
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = yaml.safe_load(f)
            return content
    except yaml.YAMLError as e:
        output_json(
            status="error",
            message=f"Invalid YAML in {file_path}: {e}",
            errors=[f"YAML parsing error: {e}"]
        )
        sys.exit(1)
    except Exception as e:
        output_json(
            status="error",
            message=f"Failed to read {file_path}: {e}",
            errors=[f"File read error: {e}"]
        )
        sys.exit(2)


def generate_run_id(job_config: Dict[str, Any]) -> str:
    """
    Generate a unique Run ID.
    
    Format: {type}-{job_id}__{YYYYMMDDTHHMMSS}
    
    Args:
        job_config: Parsed job configuration
        
    Returns:
        Generated run ID string
    """
    job_type = job_config.get("type", "unknown")
    job_id = job_config.get("job_id", "unknown")
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    
    return f"{job_type}-{job_id}__{timestamp}"


def create_run_metadata(
    run_id: str,
    job_file: Path,
    experiment_dir: Path,
    job_config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Create initial run metadata structure.
    
    Args:
        run_id: Generated run ID
        job_file: Path to job configuration file
        experiment_dir: Path to experiment directory
        job_config: Parsed job configuration
        
    Returns:
        Run metadata dictionary
    """
    return {
        "run_id": run_id,
        "job_file": str(job_file.resolve()),
        "experiment_id": experiment_dir.name,
        "status": "initialized",
        "created_at": datetime.now().isoformat(),
        "started_at": None,
        "completed_at": None,
        "exit_code": None,
        "metrics": {},
        "wandb_run_id": None,
        "checkpoint_path": None
    }


def initialize_run(
    job_file_path: Path,
    experiment_dir_path: Path,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Initialize run directory and tracking metadata.
    
    Args:
        job_file_path: Path to job configuration file
        experiment_dir_path: Path to experiment directory
        dry_run: If True, preview operations without creating files
        
    Returns:
        Dictionary with run initialization results
    """
    warnings = []
    created_files = []
    
    # Validate job file exists
    if not job_file_path.exists():
        output_json(
            status="error",
            message=f"Job file not found: {job_file_path}",
            errors=[f"File does not exist: {job_file_path.resolve()}"]
        )
        sys.exit(1)
    
    # Validate experiment directory exists
    if not experiment_dir_path.exists():
        output_json(
            status="error",
            message=f"Experiment directory not found: {experiment_dir_path}",
            errors=[f"Directory does not exist: {experiment_dir_path.resolve()}"]
        )
        sys.exit(1)
    
    if not experiment_dir_path.is_dir():
        output_json(
            status="error",
            message=f"Experiment path is not a directory: {experiment_dir_path}",
            errors=[f"Not a directory: {experiment_dir_path.resolve()}"]
        )
        sys.exit(1)
    
    # Load and validate job configuration
    job_config = load_yaml(job_file_path)
    
    if not job_config:
        output_json(
            status="error",
            message=f"Job file is empty or invalid: {job_file_path}",
            errors=["Empty or invalid job configuration"]
        )
        sys.exit(1)
    
    # Validate required fields
    required_fields = ["job_id", "type"]
    missing_fields = [field for field in required_fields if field not in job_config]
    
    if missing_fields:
        output_json(
            status="error",
            message=f"Missing required fields in job configuration: {', '.join(missing_fields)}",
            errors=[f"Missing required field: {field}" for field in missing_fields]
        )
        sys.exit(1)
    
    # Generate Run ID
    run_id = generate_run_id(job_config)
    
    # Define directory structure
    runs_dir = experiment_dir_path / "runs"
    run_dir = runs_dir / run_id
    logs_dir = run_dir / "logs"
    
    # Create run metadata
    run_metadata = create_run_metadata(
        run_id=run_id,
        job_file=job_file_path,
        experiment_dir=experiment_dir_path,
        job_config=job_config
    )
    
    if dry_run:
        # Preview mode - don't create files
        return {
            "run_id": run_id,
            "run_dir": str(run_dir.resolve()),
            "status": "preview",
            "created_files": [
                str(run_dir.resolve()),
                str(logs_dir.resolve()),
                str((run_dir / "run.yaml").resolve()),
                str((run_dir / "resolved-job.yaml").resolve())
            ],
            "timestamp": datetime.now().isoformat(),
            "dry_run": True
        }
    
    # Create directory structure
    try:
        run_dir.mkdir(parents=True, exist_ok=False)
        created_files.append(str(run_dir.resolve()))
    except FileExistsError:
        output_json(
            status="error",
            message=f"Run directory already exists: {run_dir}",
            errors=[f"Directory already exists: {run_dir.resolve()}"],
            warnings=["This may indicate a duplicate run or timestamp collision"]
        )
        sys.exit(2)
    except Exception as e:
        output_json(
            status="error",
            message=f"Failed to create run directory: {e}",
            errors=[f"Directory creation error: {e}"]
        )
        sys.exit(2)
    
    try:
        logs_dir.mkdir(parents=True, exist_ok=True)
        created_files.append(str(logs_dir.resolve()))
    except Exception as e:
        output_json(
            status="error",
            message=f"Failed to create logs directory: {e}",
            errors=[f"Directory creation error: {e}"]
        )
        sys.exit(2)
    
    # Write run.yaml
    try:
        import yaml
        run_yaml_path = run_dir / "run.yaml"
        with open(run_yaml_path, "w", encoding="utf-8") as f:
            yaml.dump(run_metadata, f, default_flow_style=False, sort_keys=False)
        created_files.append(str(run_yaml_path.resolve()))
    except Exception as e:
        output_json(
            status="error",
            message=f"Failed to write run.yaml: {e}",
            errors=[f"File write error: {e}"]
        )
        sys.exit(2)
    
    # Copy job file to resolved-job.yaml
    try:
        import yaml
        resolved_job_path = run_dir / "resolved-job.yaml"
        
        # For Phase 2, we simply copy the job config
        # Future phases will implement matrix resolution here
        with open(resolved_job_path, "w", encoding="utf-8") as f:
            yaml.dump(job_config, f, default_flow_style=False, sort_keys=False)
        created_files.append(str(resolved_job_path.resolve()))
        
        if "matrix" in job_config:
            warnings.append("Matrix parameter detected but not resolved (matrix resolution is planned for future phases)")
    except Exception as e:
        output_json(
            status="error",
            message=f"Failed to write resolved-job.yaml: {e}",
            errors=[f"File write error: {e}"]
        )
        sys.exit(2)
    
    return {
        "run_id": run_id,
        "run_dir": str(run_dir.resolve()),
        "status": "initialized",
        "created_files": created_files,
        "timestamp": datetime.now().isoformat(),
        "warnings": warnings
    }


def main() -> None:
    """Main entry point for the script."""
    args = parse_arguments()
    
    # Convert string paths to Path objects
    job_file_path = Path(args.job_file).resolve()
    experiment_dir_path = Path(args.experiment_dir).resolve()
    
    # Initialize run
    try:
        result = initialize_run(
            job_file_path=job_file_path,
            experiment_dir_path=experiment_dir_path,
            dry_run=args.dry_run
        )
        
        warnings = result.pop("warnings", [])
        
        output_json(
            status="success",
            message=f"Run initialized successfully: {result['run_id']}" if not args.dry_run else f"Dry-run preview for run: {result['run_id']}",
            data=result,
            warnings=warnings
        )
        sys.exit(0)
        
    except Exception as e:
        output_json(
            status="error",
            message=f"Unexpected error during run initialization: {e}",
            errors=[f"Runtime error: {e}"]
        )
        sys.exit(2)


if __name__ == "__main__":
    main()
