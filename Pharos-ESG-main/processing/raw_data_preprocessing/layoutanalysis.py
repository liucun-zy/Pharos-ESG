#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Processes PDF files using the MinerU library to generate JSON data and images.

This script is specifically configured to run a batch process on a directory
of PDFs. For each PDF, it invokes the MinerU parsing pipeline to extract
structured content into a `content_list.json` file and save any embedded
images to a designated folder.

The script intentionally disables the creation of Markdown (MD) files and other
intermediate build artifacts to maintain a clean output structure focused solely
on the JSON data and associated images.

Note:
    This script requires a local copy of the 'MinerU-master' library in the
    same directory. It uses dynamic imports to load the necessary modules.
"""

import importlib
import json
import os
import shutil
import sys
import traceback
from pathlib import Path
from typing import Dict, Any, List

# --- Dynamic Import of Local MinerU Library ---
# This section adds the local MinerU library to the Python path. This approach
# is used when the library is not installed as a standard package.
try:
    MINERU_PATH = Path(__file__).parent / "MinerU-master"
    if not MINERU_PATH.is_dir():
        raise ImportError(f"MinerU directory not found at: {MINERU_PATH}")
    sys.path.insert(0, str(MINERU_PATH))

    common_cli = importlib.import_module("mineru.cli.common")
    enum_class = importlib.import_module("mineru.utils.enum_class")

    # Extract required functions and classes from the imported modules
    do_parse = common_cli.do_parse
    read_fn = common_cli.read_fn
    MakeMode = enum_class.MakeMode

except ImportError as e:
    print(f"[ERROR] Failed to import MinerU library: {e}")
    print("[ERROR] Please ensure 'MinerU-master' is in the same directory.")
    sys.exit(1)


def process_single_pdf(
    pdf_path: Path, output_base_dir: Path, final_images_base_dir: Path
) -> Dict[str, Any]:
    """
    Processes a single PDF file using MinerU to generate JSON and images.

    Args:
        pdf_path: The path to the input PDF file.
        output_base_dir: The base directory for temporary MinerU outputs.
        final_images_base_dir: The base directory for the final extracted images.

    Returns:
        A dictionary containing the paths to the generated output files.

    Raises:
        Exception: Propagates exceptions that occur during MinerU processing.
    """
    try:
        # The parent directory name of the PDF is used to organize outputs
        pdf_parent_dir_name = pdf_path.parent.name
        pdf_stem = pdf_path.stem

        # Define temporary and final output directories
        temp_output_dir = output_base_dir / "mineru_output" / pdf_parent_dir_name
        final_images_dir = final_images_base_dir / pdf_parent_dir_name
        
        # Ensure directories exist
        temp_output_dir.mkdir(parents=True, exist_ok=True)
        final_images_dir.mkdir(parents=True, exist_ok=True)

        pdf_bytes = read_fn(pdf_path)

        # Invoke the MinerU parsing function with specific flags
        do_parse(
            output_dir=str(temp_output_dir),
            pdf_file_names=[pdf_stem],
            pdf_bytes_list=[pdf_bytes],
            p_lang_list=['ch'],
            backend="pipeline",
            parse_method="auto",
            formula_enable=True,
            table_enable=True,
            f_dump_content_list=True,    # Generate the final content_list.json
            f_dump_md=False,             # Do not generate a Markdown file
            f_draw_layout_bbox=False,    # Do not draw layout bounding boxes
            f_draw_span_bbox=False,      # Do not draw span bounding boxes
            f_dump_middle_json=False,    # Do not save intermediate JSON files
            f_dump_model_output=False,   # Do not save model outputs
            f_dump_orig_pdf=False,       # Do not save the original PDF
            f_make_md_mode=MakeMode.MM_MD,
        )

        # Define paths for the expected output files
        temp_auto_dir = temp_output_dir / pdf_stem / "auto"
        json_file_path = temp_auto_dir / "content_list.json"
        temp_images_dir = temp_auto_dir / "images"

        # Verify that the primary JSON output was created
        if not json_file_path.exists():
            print(f"[WARNING] JSON file was not generated for: {pdf_path.name}")
            return {"json_path": None, "images_dir": None}

        # Handle the extracted images directory
        final_images_path = None
        if temp_images_dir.exists() and temp_images_dir.is_dir():
            # Move the images from the temporary location to the final destination
            print(f"[INFO] Moving images from {temp_images_dir} to {final_images_dir}")
            shutil.move(str(temp_images_dir), str(final_images_dir))
            final_images_path = final_images_dir
        else:
            print(f"[INFO] No images directory was generated for: {pdf_path.name}")

        # Clean up the temporary directory, keeping only the JSON file
        for item in temp_auto_dir.iterdir():
            if item.name != "content_list.json":
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)
        
        return {"json_path": json_file_path, "images_dir": final_images_path}

    except Exception as e:
        print(f"[ERROR] An error occurred while processing {pdf_path.name}: {e}")
        traceback.print_exc()
        raise


def run_batch_processing(input_dir: Path, output_base_dir: Path, images_base_dir: Path) -> None:
    """
    Finds and processes all PDFs within subdirectories of a given base directory.

    Args:
        input_dir: The root directory containing subfolders with PDF files.
        output_base_dir: The base directory for storing JSON outputs.
        images_base_dir: The base directory for storing extracted image folders.
    """
    print("=" * 80)
    print("Starting Batch PDF Processing...")
    print(f"Mode:         Generate JSON and Images only")
    print(f"Input Dir:    {input_dir}")
    print(f"JSON Output:  {output_base_dir / 'mineru_output'}")
    print(f"Image Output: {images_base_dir}")
    print("=" * 80)

    pdf_paths: List[Path] = sorted(list(input_dir.glob("*/*.pdf")))
    total_files = len(pdf_paths)
    
    if total_files == 0:
        print("[WARNING] No PDF files found in the subdirectories of the input directory.")
        return

    success_count = 0
    error_count = 0

    for i, pdf_path in enumerate(pdf_paths):
        print("-" * 60)
        print(f"[INFO] Processing file {i + 1}/{total_files}: {pdf_path}")
        try:
            result = process_single_pdf(pdf_path, output_base_dir, images_base_dir)
            
            if result.get("json_path"):
                print(f"[SUCCESS] JSON created: {result['json_path']}")
                success_count += 1
            else:
                print(f"[ERROR] Failed to generate JSON for {pdf_path.name}")
                error_count += 1

        except Exception:
            error_count += 1
            print(f"[ERROR] A critical error stopped processing for: {pdf_path.name}")
            continue # Continue to the next file

    print("\n" + "=" * 80)
    print("Batch Processing Complete!")
    print(f"Summary: {success_count} succeeded, {error_count} failed out of {total_files} total files.")
    print("=" * 80)


if __name__ == "__main__":
    # --- Configuration ---
    # Define the root directories for input and output.
    # Using pathlib.Path for robust and cross-platform path handling.
    
    # Base directory containing subfolders, where each subfolder has PDFs.
    BASE_INPUT_DIR = Path(r"/Users/liucun/Desktop/ICLR_code/test")
    
    # Base directory where all outputs (JSON, images) will be stored.
    BASE_OUTPUT_DIR = Path(r"/Users/liucun/Desktop/ICLR_code/test")
    
    # Specific directory for final extracted image folders.
    # This can be the same as BASE_OUTPUT_DIR or a different location.
    FINAL_IMAGES_DIR = BASE_OUTPUT_DIR / "md_jpg"

    run_batch_processing(
        input_dir=BASE_INPUT_DIR,
        output_base_dir=BASE_OUTPUT_DIR,
        images_base_dir=FINAL_IMAGES_DIR,
    )