#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Main execution script for the batch preprocessing module.

This script serves as the primary entry point to run the preprocessing pipeline
on a collection of JSON files.

Instructions:
1.  Modify the constants in the '--- Configuration ---' section below to match
    your environment, particularly `INPUT_DATA_ROOT`.
2.  Run the script from your terminal: `python run_preprocess.py`
3.  The script will automatically discover and process all valid JSON files.
4.  In case of any error (e.g., file not found, permission denied, processing
    failure), the script will stop immediately to allow for inspection.
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

# Ensure the module is in the Python path.
# This assumes the script is run from a location where Step3_preprocess_module is accessible.
try:
    from preprocess_module import PreprocessConfig, quick_preprocess
except ImportError:
    print("[ERROR] Could not import 'preprocess_module'.")
    print("Please ensure this script is placed correctly relative to the module or that the module is in your PYTHONPATH.")
    sys.exit(1)

# ==============================================================================
# --- Configuration ---
# Modify the paths and settings in this section to fit your needs.
# ==============================================================================

# The root directory where the script will start searching for JSON files.
INPUT_DATA_ROOT = Path(r"F:\output\mineru_output")

# A list of filenames or patterns to skip during file discovery.
SKIP_PATTERNS = [
    "preprocess_batch_log.json",
    "preprocess_config.json",
    "preprocess_report.json",
    "config.json",
    "log.json",
    "batch_log.json",
    "titles.json",
]

# --- Advanced Configuration ---
# Create and customize a configuration object for the pipeline.
# If `USE_CUSTOM_CONFIG` is set to False, a default config will be used.

USE_CUSTOM_CONFIG = True

def get_custom_config() -> PreprocessConfig:
    """Returns a customized PreprocessConfig instance."""
    config = PreprocessConfig()
    
    # Image directory settings
    config.main_images_dir = r"F:\output\md_jpg"
    config.auto_search_images = True
    config.image_folder_patterns = ["{base_name}"]

    # OCR settings
    config.ocr_engine = "easyocr"
    config.use_gpu = True
    config.easyocr_languages = ['ch_sim', 'en']
    config.min_text_length = 20
    # config.tesseract_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe" # Example for Tesseract

    return config

# ==============================================================================
# --- Main Application Logic ---
# ==============================================================================

def find_all_json_files(base_path: Path) -> List[Path]:
    """
    Recursively finds all valid JSON files in a directory, excluding specific patterns.

    Args:
        base_path: The root directory to search.

    Returns:
        A sorted list of Path objects for the found JSON files.
    """
    if not base_path.is_dir():
        print(f"[ERROR] Root directory not found: {base_path}")
        print("Please check the `INPUT_DATA_ROOT` configuration. Exiting.")
        sys.exit(1)

    print(f"[INFO] Scanning for JSON files in: {base_path}")
    json_files = []
    for json_file in sorted(base_path.rglob("*.json")):
        if json_file.name.startswith(('.', '~')):
            continue

        if any(json_file.name == pattern for pattern in SKIP_PATTERNS):
            print(f"[INFO] Skipping log/config file: {json_file.name}")
            continue
            
        json_files.append(json_file)
    
    return json_files

def _perform_pre_flight_checks(json_path: Path) -> None:
    """
    Performs critical checks before processing a file. Exits on failure.

    Args:
        json_path: The path to the JSON file to be processed.
    """
    output_dir = json_path.parent
    
    # 1. Check if input file exists
    if not json_path.is_file():
        print(f"[ERROR] Input file does not exist: {json_path}")
        sys.exit(1)
    
    # 2. Check if input file is readable and is valid JSON
    try:
        with json_path.open('r', encoding='utf-8') as f:
            json.load(f)
    except json.JSONDecodeError as e:
        print(f"[ERROR] Invalid JSON format in {json_path.name}: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Cannot read input file {json_path.name}: {e}")
        sys.exit(1)
        
    # 3. Check for write permissions in the output directory
    try:
        test_file = output_dir / ".permission_test"
        test_file.touch()
        test_file.unlink()
    except Exception as e:
        print(f"[ERROR] No write permission in output directory {output_dir}: {e}")
        sys.exit(1)

def _validate_processing_result(result: Dict[str, Any], json_path: Path) -> None:
    """
    Inspects the result from the pipeline for any failures. Exits on failure.

    Args:
        result: The dictionary returned by the `quick_preprocess` function.
        json_path: The path of the file that was processed.
    """
    if not result:
        print(f"[ERROR] Processing returned an empty result for {json_path.name}.")
        sys.exit(1)

    if "error" in result or "exception" in result:
        error_msg = result.get("error") or result.get("exception")
        print(f"[ERROR] Pipeline returned an error for {json_path.name}: {error_msg}")
        sys.exit(1)
    
    if "processing_results" in result:
        for step, step_result in result["processing_results"].items():
            if isinstance(step_result, dict) and step_result.get("status") in ["failed", "error"]:
                error_msg = step_result.get('error', 'Unknown error')
                print(f"[ERROR] Step '{step}' failed for {json_path.name}: {error_msg}")
                sys.exit(1)

def process_one_file(json_path: Path, config: PreprocessConfig) -> Dict[str, Any]:
    """
    Manages the full lifecycle of processing a single JSON file.

    Args:
        json_path: Path to the JSON file.
        config: The PreprocessConfig instance to use.

    Returns:
        A dictionary containing the processing status and result.
    """
    output_dir = json_path.parent
    print(f"\n[INFO] Processing file: {json_path.name}")
    print(f"[INFO] Output directory: {output_dir}")

    _perform_pre_flight_checks(json_path)
    
    try:
        result = quick_preprocess(
            input_json_path=str(json_path),
            output_dir=str(output_dir),
            config=config
        )
        
        _validate_processing_result(result, json_path)
        
        print(f"[SUCCESS] Finished processing {json_path.name}.")
        return {"file": json_path.name, "status": "success", "result": result}

    except Exception as e:
        print(f"[FATAL] A critical error occurred while processing {json_path.name}: {e}")
        print(f"Error Type: {type(e).__name__}")
        sys.exit(1)


def main() -> None:
    """
    The main function to orchestrate the batch processing workflow.
    """
    print("=" * 80)
    print("Starting Batch ESG Report Preprocessing")
    print("=" * 80)
    
    config = get_custom_config() if USE_CUSTOM_CONFIG else PreprocessConfig()
    
    print(f"Input Root: {INPUT_DATA_ROOT}")
    print(f"Main Images Directory: {config.main_images_dir}")
    print("NOTE: The script will exit immediately upon any error.")
    print("-" * 80)

    # Validate main paths and config before starting
    if config.main_images_dir and not Path(config.main_images_dir).is_dir():
        print(f"[ERROR] Main images directory not found: {config.main_images_dir}")
        sys.exit(1)
        
    config_errors = config.validate()
    if config_errors:
        print("[ERROR] Configuration validation failed:")
        for error in config_errors:
            print(f"  - {error}")
        sys.exit(1)
    
    print("[SUCCESS] Configuration validated.")

    # Find files and process them
    json_files = find_all_json_files(INPUT_DATA_ROOT)
    if not json_files:
        print("[INFO] No JSON files found to process. Exiting.")
        sys.exit(0)
    
    print(f"[INFO] Found {len(json_files)} JSON file(s) to process.")
    print("-" * 80)

    results_log = []
    total = len(json_files)
    for i, file_path in enumerate(json_files, 1):
        print(f"----- Processing {i}/{total} -----")
        result = process_one_file(file_path, config)
        results_log.append(result)

    # Final summary and log saving
    print("\n" + "=" * 80)
    print("Batch Processing Complete!")
    print(f"  - Total Files: {total}")
    print(f"  - Successfully Processed: {len(results_log)}")
    print("=" * 80)

    log_file_path = INPUT_DATA_ROOT / "preprocess_batch_log.json"
    try:
        summary_data = {
            "batch_summary": {
                "input_root": str(INPUT_DATA_ROOT),
                "total_files_found": total,
                "files_processed": len(results_log),
            },
            "detailed_results": results_log
        }
        with log_file_path.open('w', encoding='utf-8') as f:
            json.dump(summary_data, f, ensure_ascii=False, indent=2)
        print(f"[INFO] Batch summary log saved to: {log_file_path}")
    except Exception as e:
        print(f"[ERROR] Failed to save batch summary log: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()