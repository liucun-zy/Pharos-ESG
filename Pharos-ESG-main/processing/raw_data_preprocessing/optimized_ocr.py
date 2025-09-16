#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Optimized OCR and PDF processing module for Table of Contents (TOC) extraction.

This script identifies and extracts Table of Contents pages from PDF files.
It leverages PaddleOCR for robust text recognition, with support for GPU
acceleration. The primary workflow involves:
1.  Scanning the initial pages of a PDF.
2.  Using a hybrid approach of text layer extraction and OCR to detect TOC pages.
3.  Extracting the identified TOC pages as high-resolution images.
4.  Saving a new version of the PDF with the TOC pages removed.

This module is designed for batch processing of PDF documents and includes
detailed progress tracking and logging.

Dependencies:
- paddlepaddle-gpu>=3.1.0
- paddleocr>=3.1.0
- PyMuPDF (fitz)
- Pillow
- numpy
- tqdm
"""

import contextlib
import io
import logging
import os
import re
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import fitz  # PyMuPDF
import numpy as np
from PIL import Image
from tqdm import tqdm

# ==============================================================================
# Configure Logging
# ==============================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


# ==============================================================================
# Utility Classes
# ==============================================================================
class SuppressOutput:
    """A context manager to suppress stdout and stderr.

    This is useful for silencing verbose output from external libraries
    that do not offer a programmatic way to control their logging.
    """

    def __enter__(self) -> "SuppressOutput":
        """Redirect stdout and stderr to a null device."""
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        sys.stdout = open(os.devnull, "w")
        sys.stderr = open(os.devnull, "w")
        return self

    def __exit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[BaseException],
        exc_tb: Optional[object],
    ) -> None:
        """Restore original stdout and stderr."""
        sys.stdout.close()
        sys.stderr.close()
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr


class ProgressTracker:
    """Tracks and logs the progress of a batch processing task."""

    _LOG_HEADER = (
        "+--------------------------------------------------------------------+\n"
        "|               PDF Table of Contents Processing Log               |\n"
        "+--------------------------------------------------------------------+"
    )
    _SUMMARY_HEADER = (
        "+--------------------------------------------------------------------+\n"
        "|                         Processing Summary                         |\n"
        "+--------------------------------------------------------------------+"
    )
    _SUMMARY_FOOTER = (
        "+--------------------------------------------------------------------+"
    )

    def __init__(self, log_file_path: str):
        """Initializes the ProgressTracker.

        Args:
            log_file_path: The path to the log file.
        """
        self.log_file = log_file_path
        self.start_time = time.time()
        self.processed_count = 0
        self.success_count = 0
        self.failed_count = 0
        self.failed_files: List[str] = []
        self._initialize_log_file()

    def _initialize_log_file(self) -> None:
        """Creates and initializes the log file with a header."""
        with open(self.log_file, "w", encoding="utf-8") as f:
            f.write(f"{self._LOG_HEADER}\n")
            f.write(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("-" * 68 + "\n\n")

    def log_event(
        self, filename: str, status: str, details: str = ""
    ) -> None:
        """Logs a processing event for a single file.

        Args:
            filename: The name of the file being processed.
            status: The status of the processing (e.g., 'SUCCESS', 'FAILED').
            details: Additional details about the event.
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] [{status}] {filename}"
        if details:
            log_entry += f" | {details}"

        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(log_entry + "\n")

        self.processed_count += 1
        if status == "SUCCESS":
            self.success_count += 1
        elif status == "FAILED":
            self.failed_count += 1
            self.failed_files.append(filename)

    def get_summary(self) -> str:
        """Generates a formatted string of the current progress summary.

        Returns:
            A string containing the formatted summary.
        """
        elapsed_seconds = time.time() - self.start_time
        success_rate = (
            (self.success_count / self.processed_count * 100)
            if self.processed_count > 0
            else 0
        )
        files_per_minute = (
            (self.processed_count / elapsed_seconds * 60)
            if elapsed_seconds > 0
            else 0
        )

        summary = (
            f"\n{self._SUMMARY_HEADER}\n"
            f"| Processed Files: {self.processed_count:<4} | Successful: {self.success_count:<4} | Failed: {self.failed_count:<4}      |\n"
            f"| Success Rate:    {success_rate:>6.1f}%   | Elapsed Time: {elapsed_seconds:>7.1f}s            |\n"
            f"| Avg. Speed:      {files_per_minute:>6.1f} files/min                                   |\n"
            f"{self._SUMMARY_FOOTER}\n"
        )
        return summary

    def finalize(self, input_dir: str, output_dir: str) -> None:
        """Writes the final summary to the log file.

        Args:
            input_dir: The source directory for the processed files.
            output_dir: The base directory for the output files.
        """
        elapsed_seconds = time.time() - self.start_time
        success_rate = (
            (self.success_count / self.processed_count * 100)
            if self.processed_count > 0
            else 0
        )
        files_per_minute = (
            (self.processed_count / elapsed_seconds * 60)
            if elapsed_seconds > 0
            else 0
        )

        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write("\n" + "-" * 68 + "\n")
            f.write("Final Summary\n")
            f.write("-" * 68 + "\n")
            f.write(f"End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Elapsed Time: {elapsed_seconds:.1f} seconds\n")
            f.write(f"Input Directory: {input_dir}\n")
            f.write(f"Output Directory: {output_dir}\n")
            f.write(f"Total Files Processed: {self.processed_count}\n")
            f.write(f"Successful: {self.success_count}\n")
            f.write(f"Failed: {self.failed_count}\n")
            f.write(f"Success Rate: {success_rate:.1f}%\n")
            f.write(f"Average Speed: {files_per_minute:.1f} files/min\n")

            if self.failed_files:
                f.write("\nFailed Files List:\n")
                f.write("-" * 20 + "\n")
                for filename in self.failed_files:
                    f.write(f"- {filename}\n")
            f.write("\n" + "=" * 68 + "\n")
            f.write("Processing Complete\n")
            f.write("=" * 68 + "\n")


# ==============================================================================
# Core OCR and PDF Processing Classes
# ==============================================================================
class OptimizedOCR:
    """An optimized OCR handler using PaddleOCR."""

    def __init__(self, use_gpu: bool = True, lang: str = "ch"):
        """Initializes the OCR handler.

        Args:
            use_gpu: Whether to attempt using the GPU for acceleration.
            lang: The language model to use (e.g., 'ch' for Chinese, 'en').
        """
        self.use_gpu = use_gpu
        self.lang = lang
        self.ocr_engine = self._initialize_ocr()

    def _check_gpu_availability(self) -> bool:
        """Checks for CUDA-enabled GPU availability for PaddlePaddle.

        Returns:
            True if a compatible GPU is found, False otherwise.
        """
        try:
            import paddle

            logger.info(f"PaddlePaddle version: {paddle.__version__}")
            if not paddle.is_compiled_with_cuda():
                logger.warning("PaddlePaddle was not compiled with CUDA support.")
                return False

            gpu_count = paddle.device.cuda.device_count()
            if gpu_count > 0:
                logger.info(f"Found {gpu_count} CUDA-enabled device(s).")
                for i in range(gpu_count):
                    device_name = paddle.device.cuda.get_device_name(i)
                    logger.info(f"  GPU {i}: {device_name}")
                return True
            else:
                logger.warning("No CUDA-enabled devices found.")
                return False
        except ImportError:
            logger.warning("PaddlePaddle is not installed. GPU check skipped.")
            return False
        except Exception as e:
            logger.error(f"Error during GPU check: {e}. Defaulting to CPU.")
            return False

    def _initialize_ocr(self) -> Any:
        """Initializes and returns a PaddleOCR instance.

        Raises:
            ImportError: If PaddleOCR is not installed.
            Exception: If initialization fails for other reasons.

        Returns:
            An initialized PaddleOCR instance.
        """
        try:
            from paddleocr import PaddleOCR

            gpu_available = self._check_gpu_availability()
            use_gpu_flag = self.use_gpu and gpu_available

            mode = "GPU" if use_gpu_flag else "CPU"
            logger.info(f"Initializing PaddleOCR in {mode} mode...")

            with SuppressOutput():
                ocr_instance = PaddleOCR(
                    use_gpu=use_gpu_flag,
                    lang=self.lang,
                )
            logger.info(f"PaddleOCR {mode} mode initialized successfully.")
            return ocr_instance

        except ImportError:
            logger.error(
                "PaddleOCR is not installed. Please run: "
                "pip install 'paddleocr>=2.0.1'"
            )
            raise
        except Exception as e:
            logger.error(f"Failed to initialize PaddleOCR: {e}")
            raise

    def ocr_image(self, image_data: bytes) -> str:
        """Performs OCR on an in-memory image.

        Args:
            image_data: The byte content of the image.

        Returns:
            The recognized text as a single string.
        """
        try:
            # The result from ocr() is a list of lines, where each line is
            # a list containing the bounding box and a (text, confidence) tuple.
            # e.g., [[[[x1,y1]...], ('text', 0.99)], ...]
            result = self.ocr_engine.ocr(image_data, cls=True)
            if not result or not result[0]:
                return ""

            text_lines = [line[1][0] for line in result[0] if line and line[1]]
            return "\n".join(text_lines)

        except Exception as e:
            logger.error(f"OCR process failed: {e}")
            return ""


class TOCDetector:
    """Detects if a given text page is a Table of Contents."""

    _TOC_KEYWORDS = {
        'chinese': [
            '目录', '目錄', '目次', '索引', '章节目录', '章節目錄'
        ],
        'english': [
            'table of contents', 'contents', 'index'
        ]
    }

    _NON_TOC_KEYWORDS = [
        '季度', '年度', '报告', '報告', 'quarter', 'annual', 'report',
        '业绩', '業績', '表现', '表現'
    ]

    _CHAPTER_KEYWORDS = [
        'chapter', 'section', 'part', 'appendix', 'references',
        '章', '節', '部', '篇', '编', '編', '附录', '附錄', '参考文献'
    ]

    def __init__(self):
        """Initializes the TOCDetector."""
        self.all_toc_keywords = (
            self._TOC_KEYWORDS['chinese'] + self._TOC_KEYWORDS['english']
        )

    def is_toc_page(self, text: str) -> bool:
        """Determines if the given text represents a TOC page.

        Args:
            text: The text content of a single page.

        Returns:
            True if the page is likely a TOC, False otherwise.
        """
        if not text or len(text.strip()) < 20:
            return False

        text_lower = text.lower()
        
        # Rule 1: Strong keyword match
        if any(keyword in text_lower for keyword in self.all_toc_keywords):
            return True

        # Rule 2: Heuristic-based detection for pages without explicit titles
        return self._enhanced_toc_detection(text)

    def _enhanced_toc_detection(self, text: str) -> bool:
        """Applies a set of heuristics to detect a TOC page.

        This method scores a page based on common TOC patterns like line
        leaders (dots), chapter numbering, and page number alignment.

        Args:
            text: The text content of the page.

        Returns:
            True if the page scores high enough to be a TOC, False otherwise.
        """
        lines = text.split("\n")
        toc_indicators = 0
        lines_with_content = 0

        for line in lines:
            line = line.strip()
            if not line:
                continue
            lines_with_content += 1

            # Pattern: Dotted line leaders followed by a page number
            if re.search(r'\.{3,}\s*\d+$', line):
                toc_indicators += 2
            
            # Pattern: Standard chapter/section numbering (e.g., "1.1", "Chapter 1")
            if re.search(r'^\d+(\.\d+)*\s+', line) or re.search(r'^[A-Z]\.\s+', line):
                toc_indicators += 1
            
            # Pattern: Presence of common chapter-related keywords
            if any(kw in line.lower() for kw in self._CHAPTER_KEYWORDS):
                toc_indicators += 1

        # Avoid false positives by checking for common non-TOC report keywords
        if any(kw in text.lower() for kw in self._NON_TOC_KEYWORDS):
            return False

        if lines_with_content == 0:
            return False
        
        # Calculate a "TOC density" score
        toc_density = toc_indicators / lines_with_content
        
        # A page is considered a TOC if it has a high density of indicators,
        # or a significant absolute number of strong indicators.
        return toc_density > 0.5 and toc_indicators >= 5


class PDFProcessor:
    """Handles the end-to-end processing of a single PDF file."""

    def __init__(self, use_gpu: bool = True, max_pages_to_check: int = 5):
        """Initializes the PDFProcessor.

        Args:
            use_gpu: Whether to enable GPU acceleration for OCR.
            max_pages_to_check: The number of initial pages to scan for a TOC.
        """
        self.ocr = OptimizedOCR(use_gpu=use_gpu)
        self.toc_detector = TOCDetector()
        self.max_pages = max_pages_to_check

    def find_toc_pages(self, pdf_path: str) -> List[int]:
        """Finds the page numbers of the TOC in a PDF.

        This method scans the first `max_pages_to_check` pages. It stops and
        returns the first page number that is identified as a TOC.

        Args:
            pdf_path: The path to the PDF file.

        Returns:
            A list containing the page number (0-indexed) of the first
            TOC page found, or an empty list if no TOC is found.
        """
        try:
            doc = fitz.open(pdf_path)
            num_pages_to_check = min(self.max_pages, len(doc))
            logger.info(f"Scanning first {num_pages_to_check} pages of '{Path(pdf_path).name}'...")

            for i in range(num_pages_to_check):
                page_num = i
                page = doc.load_page(page_num)

                # Step 1: Attempt detection using the fast text layer
                text = page.get_text("text")
                if self.toc_detector.is_toc_page(text):
                    logger.info(f"TOC found on page {page_num + 1} (via text layer).")
                    doc.close()
                    return [page_num]

                # Step 2: If text layer fails, use slower but more accurate OCR
                logger.info(f"Text layer on page {page_num + 1} is not a clear TOC. Performing OCR...")
                pix = page.get_pixmap(dpi=200)
                img_data = pix.tobytes("png")
                ocr_text = self.ocr.ocr_image(img_data)
                
                if self.toc_detector.is_toc_page(ocr_text):
                    logger.info(f"TOC found on page {page_num + 1} (via OCR).")
                    doc.close()
                    return [page_num]

            logger.warning(f"No TOC found within the first {num_pages_to_check} pages.")
            doc.close()
            return []
        except Exception as e:
            logger.error(f"Error finding TOC pages in '{pdf_path}': {e}")
            return []

    def process_pdf(
        self, pdf_path: str, output_dir: str
    ) -> Dict[str, Any]:
        """Processes a single PDF to find and extract its TOC.

        Args:
            pdf_path: The path to the source PDF file.
            output_dir: The directory to save output files.

        Returns:
            A dictionary containing the results of the operation.
        """
        result = {
            "success": False,
            "toc_pages": [],
            "image_paths": [],
            "output_pdf": "",
            "error": "",
        }
        try:
            toc_pages = self.find_toc_pages(pdf_path)
            if not toc_pages:
                result["error"] = "TOC page not found."
                return result

            # Extract TOC pages as images
            image_paths = self._extract_toc_images(pdf_path, toc_pages, output_dir)
            
            # Create a new PDF without the TOC pages
            pdf_name = Path(pdf_path).stem
            output_pdf_path = os.path.join(output_dir, f"{pdf_name}_no_toc.pdf")
            
            if self._remove_pages_and_save(pdf_path, toc_pages, output_pdf_path):
                result.update({
                    "success": True,
                    "toc_pages": toc_pages,
                    "image_paths": image_paths,
                    "output_pdf": output_pdf_path,
                })
            else:
                result["error"] = "Failed to remove TOC pages and save new PDF."

        except Exception as e:
            logger.error(f"Failed to process PDF '{pdf_path}': {e}", exc_info=True)
            result["error"] = str(e)
            
        return result

    def _extract_toc_images(
        self, pdf_path: str, page_numbers: List[int], output_dir: str
    ) -> List[str]:
        """Renders specified pages to high-resolution images.

        Args:
            pdf_path: Path to the source PDF.
            page_numbers: A list of 0-indexed page numbers to extract.
            output_dir: Directory to save the images.

        Returns:
            A list of paths to the created image files.
        """
        image_paths = []
        try:
            doc = fitz.open(pdf_path)
            for page_num in page_numbers:
                page = doc.load_page(page_num)
                # Render at high resolution (300 DPI)
                pix = page.get_pixmap(dpi=300)
                image_path = os.path.join(output_dir, f"toc_page_{page_num + 1}.png")
                pix.save(image_path)
                image_paths.append(image_path)
                logger.info(f"Saved TOC image: {image_path}")
            doc.close()
        except Exception as e:
            logger.error(f"Failed to extract TOC images from '{pdf_path}': {e}")
        return image_paths

    def _remove_pages_and_save(
        self, pdf_path: str, pages_to_delete: List[int], output_path: str
    ) -> bool:
        """Deletes specified pages from a PDF and saves the result.

        Args:
            pdf_path: Path to the source PDF.
            pages_to_delete: A list of 0-indexed page numbers to delete.
            output_path: The path to save the modified PDF.

        Returns:
            True if successful, False otherwise.
        """
        try:
            doc = fitz.open(pdf_path)
            # Delete pages in reverse order to avoid index shifting issues
            for page_num in sorted(pages_to_delete, reverse=True):
                doc.delete_page(page_num)
            doc.save(output_path)
            doc.close()
            logger.info(f"Saved modified PDF (no TOC): {output_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to remove pages from '{pdf_path}': {e}")
            return False

# ==============================================================================
# Main Execution Logic
# ==============================================================================
def _setup_directories(base_output_dir: str) -> Tuple[str, str, str]:
    """Creates necessary output directories.

    Args:
        base_output_dir: The root directory for all outputs.

    Returns:
        A tuple containing paths for success, failed, and log directories.
    """
    success_dir = os.path.join(base_output_dir, "success")
    failed_dir = os.path.join(base_output_dir, "failed")
    os.makedirs(success_dir, exist_ok=True)
    os.makedirs(failed_dir, exist_ok=True)
    log_file_path = os.path.join(base_output_dir, "processing_log.txt")
    return success_dir, failed_dir, log_file_path


def _initialize_processor() -> PDFProcessor:
    """Initializes the PDFProcessor after checking hardware."""
    # This function is kept separate to allow for more complex
    # initialization logic in the future, such as dynamic GPU selection.
    logger.info("Initializing PDF Processor...")
    # The GPU check is handled inside the PDFProcessor's constructor.
    return PDFProcessor(use_gpu=True, max_pages_to_check=4)


def run_batch_processing(input_dir: str, output_base_dir: str) -> None:
    """Runs the batch processing of all PDFs in a directory.

    Args:
        input_dir: The directory containing source PDF files.
        output_base_dir: The root directory for all output files and logs.
    """
    if not os.path.isdir(input_dir):
        logger.error(f"Input directory does not exist: {input_dir}")
        return

    success_dir, failed_dir, log_file = _setup_directories(output_base_dir)
    tracker = ProgressTracker(log_file)
    processor = _initialize_processor()
    
    pdf_files = [f for f in os.listdir(input_dir) if f.lower().endswith(".pdf")]
    if not pdf_files:
        logger.warning(f"No PDF files found in directory: {input_dir}")
        return

    print("\n" + "=" * 80)
    print("Starting PDF Table of Contents Extraction Process")
    print(f"Input Directory:  {input_dir}")
    print(f"Output Directory: {output_base_dir}")
    print(f"Log File:         {log_file}")
    print(f"Found {len(pdf_files)} PDF file(s) to process.")
    print("=" * 80)

    progress_bar = tqdm(
        pdf_files,
        desc="Processing PDFs",
        unit="file",
        bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]",
    )

    for pdf_filename in progress_bar:
        pdf_path = os.path.join(input_dir, pdf_filename)
        pdf_stem = Path(pdf_filename).stem
        
        try:
            pdf_output_dir = os.path.join(success_dir, pdf_stem)
            os.makedirs(pdf_output_dir, exist_ok=True)
            
            result = processor.process_pdf(pdf_path, pdf_output_dir)

            if result["success"]:
                toc_pages_str = ", ".join(str(p + 1) for p in result["toc_pages"])
                msg = f"TOC pages found: {toc_pages_str}"
                tracker.log_event(pdf_filename, "SUCCESS", msg)
                progress_bar.write(f"[SUCCESS] {pdf_filename}: {msg}")
            else:
                tracker.log_event(pdf_filename, "FAILED", result["error"])
                progress_bar.write(f"[FAILED]  {pdf_filename}: {result['error']}")
                shutil.move(pdf_output_dir, os.path.join(failed_dir, pdf_stem))
                
        except Exception as e:
            tracker.log_event(pdf_filename, "ERROR", str(e))
            progress_bar.write(f"[ERROR]   {pdf_filename}: An unexpected error occurred: {e}")
            if 'pdf_output_dir' in locals() and os.path.exists(pdf_output_dir):
                shutil.move(pdf_output_dir, os.path.join(failed_dir, pdf_stem))

    tracker.finalize(input_dir, output_base_dir)
    print("\n" + "=" * 80)
    print("Batch Processing Complete")
    print(tracker.get_summary())
    if tracker.failed_files:
        print("The following files failed processing:")
        for filename in tracker.failed_files:
            print(f"  - {filename}")
    print(f"Detailed log available at: {log_file}")
    print("=" * 80)


if __name__ == "__main__":
    # --- Configuration ---
    # For command-line execution, these paths should be replaced by
    # argument parsing (e.g., using argparse) for better flexibility.
    INPUT_DIRECTORY = r"/"
    OUTPUT_DIRECTORY = r"/"

    run_batch_processing(INPUT_DIRECTORY, OUTPUT_DIRECTORY)