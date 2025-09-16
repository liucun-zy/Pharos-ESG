# preprocessing_module/utils.py

"""
Utility functions for the preprocessing module.

This module provides a collection of helper functions for common tasks such as
logging setup, path validation, safe file operations, performance timing, and
statistics tracking. These utilities are used across the module to ensure
consistency and reduce code duplication.
"""

import logging
import os
import shutil
import time
from contextlib import contextmanager
from functools import wraps
from pathlib import Path
from typing import Any, Dict, List, Optional


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    logger_name: str = "preprocess",
) -> logging.Logger:
    """Configures and returns a logger instance.

    Args:
        log_level: The logging level (e.g., "INFO", "DEBUG").
        log_file: Optional path to a file for log output.
        logger_name: The name of the logger.

    Returns:
        A configured logging.Logger instance.
    """
    logger = logging.getLogger(logger_name)
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Avoid adding duplicate handlers
    if logger.hasHandlers():
        logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def validate_paths(paths_to_check: Dict[str, str]) -> List[str]:
    """Validates a dictionary of file system paths.

    Args:
        paths_to_check: A dictionary where keys are descriptions and values are paths.

    Returns:
        A list of error messages for invalid paths.
    """
    errors = []
    for description, path_str in paths_to_check.items():
        if not path_str:
            errors.append(f"Path for '{description}' cannot be empty.")
            continue
        
        path_obj = Path(path_str)
        
        # For output paths, we only require the parent directory to exist.
        is_output = "output" in description.lower() or "输出" in description
        if is_output:
            if not path_obj.parent.exists():
                errors.append(f"Parent directory for output path '{description}' does not exist: {path_obj.parent}")
        # For input paths, the path itself must exist.
        else:
            if not path_obj.exists():
                errors.append(f"Input path for '{description}' does not exist: {path_str}")
    
    return errors


def ensure_directory(dir_path: str) -> Path:
    """Ensures a directory exists, creating it if necessary."""
    path = Path(dir_path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def safe_file_operation(operation_name: str):
    """A decorator for handling common file operation exceptions."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except FileNotFoundError as e:
                raise FileNotFoundError(f"{operation_name} failed: File not found - {e}")
            except PermissionError as e:
                raise PermissionError(f"{operation_name} failed: Permission denied - {e}")
            except Exception as e:
                raise RuntimeError(f"An unexpected error occurred during {operation_name}: {e}")
        return wrapper
    return decorator


@contextmanager
def timing_context(logger: logging.Logger, operation_name: str):
    """A context manager to log the duration of an operation."""
    logger.info(f"Starting: {operation_name}...")
    start_time = time.time()
    try:
        yield
    finally:
        elapsed_time = time.time() - start_time
        logger.info(f"Finished: {operation_name}. Duration: {elapsed_time:.2f} seconds.")


def get_file_stats(file_path: str) -> Dict[str, Any]:
    """Retrieves metadata statistics for a given file."""
    path = Path(file_path)
    if not path.exists():
        return {"exists": False}
    
    stat = path.stat()
    return {
        "exists": True,
        "size_bytes": stat.st_size,
        "size_mb": round(stat.st_size / (1024 * 1024), 2),
        "modified_time": time.ctime(stat.st_mtime),
    }


def backup_file(file_path: str, suffix: str = ".bak") -> Optional[str]:
    """Creates a backup of a file by copying it."""
    source_path = Path(file_path)
    if not source_path.exists():
        return None
    
    try:
        backup_path = source_path.with_suffix(source_path.suffix + suffix)
        shutil.copy2(source_path, backup_path)
        return str(backup_path)
    except Exception:
        return None


class ProcessingStats:
    """A class to track statistics for a processing job."""

    def __init__(self):
        self.stats: Dict[str, Any] = {
            "start_time": time.time(),
            "end_time": None,
            "duration_seconds": 0,
            "files_processed": 0,
            "ops_success": 0,
            "ops_failed": 0,
            "errors": [],
            "warnings": [],
        }

    def add_success(self) -> None:
        self.stats["ops_success"] += 1

    def add_failure(self, error_message: str) -> None:
        self.stats["ops_failed"] += 1
        self.stats["errors"].append(error_message)

    def add_warning(self, warning_message: str) -> None:
        self.stats["warnings"].append(warning_message)

    def increment_files_processed(self) -> None:
        self.stats["files_processed"] += 1

    def finish(self) -> None:
        self.stats["end_time"] = time.time()
        self.stats["duration_seconds"] = self.stats["end_time"] - self.stats["start_time"]

    def to_dict(self) -> Dict[str, Any]:
        return self.stats.copy()

    def summary(self) -> str:
        """Generates a human-readable summary string of the statistics."""
        if self.stats["end_time"] is None:
            self.finish()

        return (
            f"Processing Summary:\n"
            f"- Total Duration: {self.stats['duration_seconds']:.2f}s\n"
            f"- Files Processed: {self.stats['files_processed']}\n"
            f"- Successful Operations: {self.stats['ops_success']}\n"
            f"- Failed Operations: {self.stats['ops_failed']}\n"
            f"- Errors: {len(self.stats['errors'])}\n"
            f"- Warnings: {len(self.stats['warnings'])}"
        )