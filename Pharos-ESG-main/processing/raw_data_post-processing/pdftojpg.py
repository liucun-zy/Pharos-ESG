#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A utility script to convert PDF files into a series of JPEG images.

This script provides functionality to batch-process a directory of PDF files,
converting each page of every PDF into a separate JPG image. It preserves the
original directory structure in the specified output location.

Features include:
- Batch conversion of all PDFs within a source directory tree.
- Preservation of the relative directory structure.
- An interactive command-line interface to preview, test, and run the process.
"""

import sys
import traceback
from pathlib import Path
from typing import List

import fitz  # PyMuPDF


def convert_pdf_to_images(
    pdf_path: Path, source_base_dir: Path, output_base_dir: Path
) -> None:
    """
    Converts a single PDF file into a directory of JPEG images.

    Each page of the PDF is saved as a separate image. The images are stored
    in a subdirectory named after the PDF file (e.g., 'document_pages').

    Args:
        pdf_path: The absolute path to the PDF file.
        source_base_dir: The root directory of the source files, used to
                         calculate the relative path for the output.
        output_base_dir: The root directory where the output will be saved.
    
    Raises:
        Exception: If the PDF file cannot be opened or processed.
    """
    try:
        # Determine the relative path to maintain the directory structure
        relative_path = pdf_path.parent.relative_to(source_base_dir)
        
        # Create a specific output directory for the images of this PDF
        output_dir = output_base_dir / relative_path / f"{pdf_path.stem}_pages"
        output_dir.mkdir(parents=True, exist_ok=True)

        doc = fitz.open(pdf_path)
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            pix = page.get_pixmap()
            img_path = output_dir / f"page_{page_num + 1}.jpg"
            pix.save(str(img_path))
        doc.close()
        
        print(f"[INFO] Converted '{pdf_path.name}' to {len(doc)} images in: {output_dir}")

    except Exception as e:
        print(f"[ERROR] Failed to process {pdf_path.name}: {e}")
        raise


def run_batch_conversion(source_dir: Path, output_dir: Path) -> None:
    """
    Scans a directory and converts all found PDF files to images.

    Args:
        source_dir: The source directory to search for PDF files recursively.
        output_dir: The base directory to store the output images.
    """
    print(f"Starting batch conversion from: {source_dir}")
    print(f"Output will be saved to: {output_dir}")
    print("-" * 60)
    
    # Use rglob to recursively find all PDF files
    pdf_files = list(source_dir.rglob("*.pdf"))
    total_files = len(pdf_files)
    
    if total_files == 0:
        print("[INFO] No PDF files found in the source directory.")
        return

    success_count = 0
    error_count = 0

    for i, pdf_path in enumerate(pdf_files):
        print(f"--> Processing file {i + 1}/{total_files}: {pdf_path.name}")
        try:
            convert_pdf_to_images(pdf_path, source_dir, output_dir)
            success_count += 1
        except Exception:
            error_count += 1

    print("-" * 60)
    print("Batch conversion complete!")
    print(f"Summary: {success_count} successful, {error_count} failed.")


def preview_operations(source_dir: Path) -> List[Path]:
    """
    Scans and lists the PDF files that will be processed.

    Args:
        source_dir: The source directory to scan.
    
    Returns:
        A list of paths to the PDF files found.
    """
    print("--- Operation Preview ---")
    print(f"Source Directory: {source_dir}")
    
    pdf_files = sorted(list(source_dir.rglob("*.pdf")))
    total_found = len(pdf_files)
    
    print(f"Found {total_found} PDF file(s):")
    # Display the first 10 files for a brief preview
    for pdf_file in pdf_files[:10]:
        print(f"  - {pdf_file.relative_to(source_dir)}")
    
    if total_found > 10:
        print(f"  ... and {total_found - 10} more.")
        
    return pdf_files


def run_single_test(source_dir: Path, output_dir: Path) -> bool:
    """
    Runs a conversion test on the first PDF file found.

    Args:
        source_dir: The directory to search for a test PDF.
        output_dir: The base directory for the output.

    Returns:
        True if the test was successful, False otherwise.
    """
    print("--- Single File Test Mode ---")
    
    # Find the first PDF file to use for the test
    try:
        test_pdf_path = next(source_dir.rglob("*.pdf"))
    except StopIteration:
        print("[ERROR] No PDF files found in the source directory to run a test.")
        return False

    print(f"Found test file: {test_pdf_path}")
    
    try:
        convert_pdf_to_images(test_pdf_path, source_dir, output_dir)
        print("[SUCCESS] Test conversion completed successfully.")
        return True
    except Exception:
        print("[ERROR] Test conversion failed.")
        traceback.print_exc()
        return False


def main() -> None:
    """
    Main function to run the interactive command-line tool.
    """
    print("=" * 60)
    print("PDF to JPEG Conversion Utility")
    print("=" * 60)

    # --- Configuration ---
    # Define source and output directories here.
    SOURCE_DIRECTORY = Path(r"E:\US_Preprocess\success1")
    OUTPUT_DIRECTORY = Path(r"E:\US_Preprocess\success1_jpg_output")
    
    if not SOURCE_DIRECTORY.is_dir():
        print(f"[ERROR] Source directory does not exist: {SOURCE_DIRECTORY}")
        sys.exit(1)
        
    OUTPUT_DIRECTORY.mkdir(exist_ok=True)

    # --- Main Menu ---
    pdf_files_to_process = preview_operations(SOURCE_DIRECTORY)
    
    if not pdf_files_to_process:
        print("\nNo PDF files found. Exiting.")
        sys.exit(0)

    while True:
        print("\n" + "=" * 60)
        print("Please choose an option:")
        print("1. Run Test (converts one PDF file)")
        print("2. Run Full Conversion")
        print("3. Exit")
        
        choice = input("\nEnter your choice (1/2/3): ").strip()

        if choice == "1":
            run_single_test(SOURCE_DIRECTORY, OUTPUT_DIRECTORY)
        
        elif choice == "2":
            confirm = input(
                f"This will convert {len(pdf_files_to_process)} PDF files. "
                "Are you sure? (y/N): "
            ).strip().lower()
            if confirm == 'y':
                run_batch_conversion(SOURCE_DIRECTORY, OUTPUT_DIRECTORY)
                break
            else:
                print("Operation cancelled.")
        
        elif choice == "3":
            print("Exiting program.")
            break
            
        else:
            print("Invalid choice. Please enter 1, 2, or 3.")


if __name__ == "__main__":
    main()