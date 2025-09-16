# preprocessing_module/processors.py

"""
Core processing units for the document preprocessing pipeline.

This module contains the implementation of the main processors, each responsible
for a specific step in the workflow:
- JsonToMarkdownProcessor: Converts structured JSON into a Markdown file.
- ImageLinkConverter: Transforms image file paths into standard Markdown links.
- ImageTextDetector: Uses OCR to detect and filter images without text.
"""

import json
import logging
import os
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List

import pytesseract
from PIL import Image

from .config import PreprocessConfig
from .utils import backup_file, get_file_stats, safe_file_operation, timing_context

# Dynamically import EasyOCR to handle optional dependency
try:
    import easyocr
except ImportError:
    easyocr = None


class BaseProcessor(ABC):
    """An abstract base class for all processor units."""

    def __init__(self, config: PreprocessConfig, logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.stats: Dict[str, Any] = {
            "processed_files": 0,
            "successful_operations": 0,
            "failed_operations": 0,
            "errors": [],
        }

    @abstractmethod
    def process(self, *args, **kwargs) -> Dict[str, Any]:
        """The main processing method to be implemented by subclasses."""
        raise NotImplementedError

    def get_stats(self) -> Dict[str, Any]:
        """Returns a copy of the processor's statistics."""
        return self.stats.copy()


class JsonToMarkdownProcessor(BaseProcessor):
    """Converts a structured JSON file to a Markdown document."""

    def __init__(self, config: PreprocessConfig, logger: logging.Logger):
        super().__init__(config, logger)
        self.logger.info("JsonToMarkdownProcessor initialized.")

    @safe_file_operation("JSON to Markdown conversion")
    def process(self, input_json_path: str, output_md_path: str) -> Dict[str, Any]:
        """
        Reads a JSON file, converts its content to Markdown, and saves it.

        Args:
            input_json_path: Path to the source JSON file.
            output_md_path: Path to the destination Markdown file.

        Returns:
            A dictionary containing the results of the operation.
        """
        with timing_context(self.logger, f"JSON to MD for {Path(input_json_path).name}"):
            with open(input_json_path, "r", encoding="utf-8") as f:
                content_objects = json.load(f)

            md_lines = self._generate_markdown_lines(content_objects)
            
            if Path(output_md_path).exists():
                backup_file(output_md_path)

            with open(output_md_path, "w", encoding="utf-8") as f:
                f.write("\n".join(md_lines).strip() + "\n")

            self.stats["processed_files"] += 1
            self.stats["successful_operations"] += 1
            
            return {
                "status": "success",
                "input_file": input_json_path,
                "output_file": output_md_path,
                "objects_processed": len(content_objects),
                "lines_generated": len(md_lines),
            }

    def _generate_markdown_lines(self, objects: List[Dict]) -> List[str]:
        """Helper to generate Markdown lines from content objects."""
        lines = []
        for obj in objects:
            prefix = f'<page_idx:{obj.get("page_idx", "N/A")}>' if self.config.add_page_markers else ""
            obj_type = obj.get("type", "")

            if prefix: lines.append(prefix)

            if obj_type in ["image", "table"]:
                lines.append(obj.get("img_path", ""))
                if obj_type == "table" and obj.get("table_body"):
                    if self.config.preserve_html_tables:
                        lines.append(obj["table_body"].strip())
            elif obj_type == "text":
                text = obj.get("text", "").strip()
                level = obj.get("text_level", 0)
                lines.append(f"{'#' * level} {text}" if level else text)
            
            lines.extend(["", ""]) # Add spacing
        return lines


class ImageLinkConverter(BaseProcessor):
    """Converts plain text image paths in a Markdown file to Markdown image links."""

    def __init__(self, config: PreprocessConfig, logger: logging.Logger):
        super().__init__(config, logger)
        self.logger.info("ImageLinkConverter initialized.")

    @safe_file_operation("Image link conversion")
    def process(self, md_file_path: str, images_dir: str) -> Dict[str, Any]:
        """
        Scans a Markdown file and converts text paths to ![]() image links.

        Args:
            md_file_path: Path to the Markdown file to process.
            images_dir: The directory where the image files are located.

        Returns:
            A dictionary containing the results of the operation.
        """
        with timing_context(self.logger, f"Link conversion for {Path(md_file_path).name}"):
            md_path = Path(md_file_path)
            original_content = md_path.read_text(encoding="utf-8")
            
            lines = original_content.split("\n")
            new_lines = []
            converted_count = 0
            
            for line in lines:
                stripped_line = line.strip()
                if any(stripped_line.lower().endswith(ext) for ext in self.config.supported_image_extensions):
                    image_path = Path(images_dir) / Path(stripped_line).name
                    if not self.config.validate_image_existence or image_path.exists():
                        new_lines.append(f"![]({stripped_line})")
                        converted_count += 1
                    else:
                        self.logger.warning(f"Image file not found, link not converted: {image_path}")
                        new_lines.append(line)
                else:
                    new_lines.append(line)
            
            new_content = "\n".join(new_lines)
            
            if new_content != original_content:
                backup_file(md_file_path)
                md_path.write_text(new_content, encoding="utf-8")

            self.stats.update({"processed_files": 1, "successful_operations": converted_count})
            return {
                "status": "success",
                "file_path": md_file_path,
                "converted_links": converted_count,
            }


class ImageTextDetector(BaseProcessor):
    """Uses OCR to detect and filter out images that contain no significant text."""

    def __init__(self, config: PreprocessConfig, logger: logging.Logger):
        super().__init__(config, logger)
        self.logger.info(f"ImageTextDetector initialized with engine: {config.ocr_engine}.")
        self.ocr_reader = self._initialize_ocr_engine()

    def _initialize_ocr_engine(self):
        """Initializes the configured OCR engine."""
        if self.config.ocr_engine == "easyocr":
            if easyocr is None:
                raise ImportError("EasyOCR is selected but not installed. Please run 'pip install easyocr'.")
            try:
                return easyocr.Reader(self.config.easyocr_languages, gpu=self.config.use_gpu)
            except Exception as e:
                self.logger.error(f"Failed to initialize EasyOCR: {e}")
                raise
        elif self.config.ocr_engine == "tesseract":
            if self.config.tesseract_path:
                pytesseract.pytesseract.tesseract_cmd = self.config.tesseract_path
            return "tesseract" # Placeholder, Tesseract is used via static calls
        else:
            raise ValueError(f"Unsupported OCR engine: {self.config.ocr_engine}")

    @safe_file_operation("Image text detection")
    def process(self, md_file_path: str, images_dir: str) -> Dict[str, Any]:
        """
        Scans a Markdown file, performs OCR on linked images, and removes links
        to images that are determined to be purely decorative (no text).

        Args:
            md_file_path: Path to the Markdown file.
            images_dir: The directory where image files are stored.

        Returns:
            A dictionary containing the results of the operation.
        """
        with timing_context(self.logger, f"Text detection for {Path(md_file_path).name}"):
            md_path = Path(md_file_path)
            content = md_path.read_text(encoding="utf-8")
            
            image_pattern = re.compile(r"!\[.*?\]\((.+?)\)")
            matches = list(image_pattern.finditer(content))
            links_to_remove = []
            
            for match in matches:
                image_rel_path = match.group(1)
                image_full_path = Path(images_dir) / Path(image_rel_path).name
                
                if image_full_path.exists():
                    if not self._image_has_text(str(image_full_path)):
                        links_to_remove.append(match.group(0))
                        self.logger.info(f"Removing link to textless image: {image_full_path.name}")
                else:
                    self.logger.warning(f"Image not found during text detection: {image_full_path}")
            
            new_content = content
            for link in links_to_remove:
                new_content = new_content.replace(link, "")

            if new_content != content:
                backup_file(md_file_path)
                md_path.write_text(new_content, encoding="utf-8")

            self.stats.update({"processed_files": 1, "successful_operations": len(matches)})
            return {
                "status": "success",
                "images_found": len(matches),
                "images_removed": len(links_to_remove),
            }

    def _image_has_text(self, image_path: str) -> bool:
        """Performs OCR on an image to determine if it contains text."""
        try:
            text = ""
            if self.config.ocr_engine == "easyocr":
                with open(image_path, "rb") as f:
                    img_bytes = f.read()
                results = self.ocr_reader.readtext(img_bytes)
                text = " ".join([res[1] for res in results if res[2] > self.config.confidence_threshold / 100.0])
            elif self.config.ocr_engine == "tesseract":
                img = Image.open(image_path)
                text = pytesseract.image_to_string(img, lang=self.config.ocr_languages)
            
            clean_text = re.sub(r"\s+", "", text).strip()
            return len(clean_text) >= self.config.min_text_length
        except Exception as e:
            self.logger.error(f"OCR failed for {image_path}: {e}")
            return True # Fail safe: assume text exists if OCR fails