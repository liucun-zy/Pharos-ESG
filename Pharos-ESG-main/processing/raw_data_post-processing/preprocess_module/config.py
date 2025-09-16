# preprocessing_module/config.py

"""
Configuration management for the preprocessing pipeline.

This module defines a central configuration class, `PreprocessConfig`, using
dataclasses for type safety and structure. It leverages marshmallow_dataclass
for robust serialization to and from JSON files, allowing for easy loading,
saving, and validation of experiment parameters.
"""

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import marshmallow_dataclass


@dataclass
class PreprocessConfig:
    """
    A dataclass to hold all configuration parameters for the preprocessing pipeline.
    
    Attributes:
        experiment_name: A unique name for the experiment run.
        base_dir: The base directory for input files.
        output_dir: The root directory for all generated outputs.
        main_images_dir: The primary directory to search for image folders.
        auto_search_images: If True, automatically searches for image folders
                            based on patterns.
        image_folder_patterns: A list of string patterns to find corresponding
                               image folders.
        supported_image_extensions: A list of recognized image file extensions.
        ocr_engine: The OCR engine to use. Supported options: "easyocr", "tesseract".
        use_gpu: Whether to enable GPU acceleration for EasyOCR.
        tesseract_path: The executable path for the Tesseract engine.
        ocr_languages: Language codes for Tesseract (e.g., "chi_sim+eng").
        easyocr_languages: Language codes for EasyOCR (e.g., ['ch_sim', 'en']).
        confidence_threshold: The minimum confidence score for OCR results.
        min_text_length: The minimum character length to consider an image as
                         containing meaningful text.
        log_level: The logging level (e.g., "INFO", "DEBUG").
        log_to_file: If True, logs will be written to a file.
        log_file_path: The path to the log file.
        add_page_markers: If True, adds <page_idx:N> markers in the MD output.
        preserve_html_tables: If True, keeps tables in their original HTML format.
        validate_image_existence: If True, checks if referenced image files exist.
        json_to_md_enabled: Enables or disables the JSON to Markdown step.
        image_link_conversion_enabled: Enables or disables the image link
                                       conversion step.
        text_detection_enabled: Enables or disables the image text detection step.
        ablation_config: A dictionary to store specific settings for ablation studies.
    """
    
    # --- Experiment Configuration ---
    experiment_name: str = "default_experiment"

    # --- Path Configuration ---
    base_dir: Optional[str] = None
    output_dir: Optional[str] = None

    # --- Image Directory Configuration ---
    main_images_dir: Optional[str] = None
    auto_search_images: bool = True
    image_folder_patterns: List[str] = field(
        default_factory=lambda: [
            "{base_name}_temp_images",
            "{base_name}_images",
            "{base_name}",
            "{base_name}_pages",
        ]
    )
    supported_image_extensions: List[str] = field(
        default_factory=lambda: [
            ".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff", ".webp"
        ]
    )

    # --- OCR Engine Configuration ---
    ocr_engine: str = "easyocr"
    use_gpu: bool = True  # Effective only for EasyOCR

    # --- Tesseract-Specific Configuration ---
    tesseract_path: Optional[str] = None
    ocr_languages: str = "chi_sim+eng"

    # --- EasyOCR-Specific Configuration ---
    easyocr_languages: List[str] = field(default_factory=lambda: ["ch_sim", "en"])

    # --- General OCR Configuration ---
    confidence_threshold: float = 40.0
    min_text_length: int = 20

    # --- Logging Configuration ---
    log_level: str = "INFO"
    log_to_file: bool = True
    log_file_path: Optional[str] = None

    # --- JSON to Markdown Configuration ---
    add_page_markers: bool = True
    preserve_html_tables: bool = True

    # --- Image Link Conversion Configuration ---
    validate_image_existence: bool = True

    # --- Ablation Study Switches ---
    json_to_md_enabled: bool = True
    image_link_conversion_enabled: bool = True
    text_detection_enabled: bool = True
    
    # --- Advanced Settings (usually not modified directly) ---
    ablation_config: Dict[str, bool] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the configuration object to a dictionary."""
        schema = marshmallow_dataclass.class_schema(PreprocessConfig)()
        return schema.dump(self)

    def to_json(self, file_path: str) -> None:
        """Saves the configuration to a JSON file.

        Args:
            file_path: The path to the output JSON file.
        """
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PreprocessConfig":
        """Loads configuration from a dictionary."""
        schema = marshmallow_dataclass.class_schema(PreprocessConfig)()
        return schema.load(data)

    @classmethod
    def from_json(cls, file_path: str) -> "PreprocessConfig":
        """Loads configuration from a JSON file."""
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)

    def validate(self) -> List[str]:
        """Validates the configuration parameters.

        Returns:
            A list of error messages. An empty list indicates a valid configuration.
        """
        errors = []
        if self.ocr_engine == "tesseract":
            if not self.tesseract_path:
                errors.append("`tesseract_path` must be set when using the Tesseract engine.")
            elif not os.path.exists(self.tesseract_path):
                errors.append(f"Tesseract executable not found at: {self.tesseract_path}")

        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.log_level.upper() not in valid_log_levels:
            errors.append(f"Invalid log level: {self.log_level}. Must be one of {valid_log_levels}")
        
        return errors
        
    def apply_ablation(self, experiment_name: str) -> None:
        """Applies an ablation study configuration based on its name.

        Args:
            experiment_name: The name of the ablation experiment to apply.
        """
        self.experiment_name = experiment_name
        
        # Default to all steps enabled
        self.json_to_md_enabled = True
        self.image_link_conversion_enabled = True
        self.text_detection_enabled = True
        
        if "no_text_detection" in experiment_name:
            self.text_detection_enabled = False
            self.ablation_config["text_detection_enabled"] = False
            
        if "no_image_conversion" in experiment_name:
            self.image_link_conversion_enabled = False
            self.ablation_config["image_link_conversion_enabled"] = False
            
        if "md_only" in experiment_name:
            self.image_link_conversion_enabled = False
            self.text_detection_enabled = False
            self.ablation_config.update({
                "image_link_conversion_enabled": False,
                "text_detection_enabled": False
            })

# Example usage block
if __name__ == '__main__':
    # 1. Create a default configuration instance
    config = PreprocessConfig()
    
    # 2. Modify parameters as needed
    config.base_dir = "/path/to/data"
    config.output_dir = "/path/to/output"
    config.log_level = "DEBUG"
    config.ocr_engine = "easyocr"
    config.use_gpu = True
    
    # 3. Validate the configuration
    validation_errors = config.validate()
    if validation_errors:
        print("Configuration errors found:")
        for error in validation_errors:
            print(f"- {error}")
    else:
        print("Configuration validated successfully.")
    
    # 4. Save to a dictionary and a JSON file
    config_dict = config.to_dict()
    print("\nConfiguration as dictionary:")
    print(config_dict)
    
    config_json_path = "preprocess_config.json"
    config.to_json(config_json_path)
    print(f"\nConfiguration saved to {config_json_path}")
    
    # 5. Load the configuration from the JSON file
    loaded_config = PreprocessConfig.from_json(config_json_path)
    print(f"\nLoaded OCR engine from {config_json_path}: {loaded_config.ocr_engine}")
    
    # 6. Clean up the example file
    os.remove(config_json_path)