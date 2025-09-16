# Raw Data Post-Processing Module

## Overview

This module provides a comprehensive post-processing pipeline for structured document data, specifically designed for ESG (Environmental, Social, and Governance) report analysis and academic research applications. The module transforms raw JSON data into standardized formats suitable for downstream analysis, incorporating advanced image noise processing to ensure the integrity and quality of visual data. This includes handling artifacts from scanning or compression and validating the usability of image content before further processing.

## Key Features
- **JSON to Markdown Conversion**: Intelligent transformation of structured JSON data into clean, readable Markdown format
- **Image Link Standardization**: Automated conversion and validation of image references with path normalization
- **OCR-based Text Detection**: Advanced optical character recognition for filtering images without meaningful text content
- **Modular Architecture**: Configurable pipeline components supporting ablation studies and A/B testing
- **Batch Processing**: Efficient processing of large document collections with comprehensive logging
- **PDF to Image Conversion**: Utility for converting PDF documents to high-quality JPEG images
- **Configuration Management**: Flexible configuration system with JSON serialization support

## Architecture

The post-processing module follows a modular pipeline architecture:

```
raw_data_post-processing/
├── pdftojpg.py                    # PDF to JPEG conversion utility
├── run_preprocess.py              # Main execution script
├── preprocess_module/             # Core processing module
│   ├── __init__.py               # Module initialization and public API
│   ├── config.py                 # Configuration management
│   ├── processors.py             # Core processing components
│   ├── pipeline.py               # Pipeline orchestration
│   ├── utils.py                  # Utility functions and helpers
│   └── example_usage.py          # Usage examples and demonstrations
└── requirements.txt              # Python dependencies
```

## Core Components

### Processing Pipeline
- **JsonToMarkdownProcessor**: Converts structured JSON documents to Markdown format with configurable formatting options
- **ImageLinkConverter**: Standardizes image references and validates file existence
- **ImageTextDetector**: Uses OCR engines (Tesseract/EasyOCR) to detect text content in images

### Pipeline Management
- **PreprocessPipeline**: Single-document processing workflow
- **BatchPreprocessPipeline**: Multi-document batch processing with parallel execution
- **AblationExperimentRunner**: Framework for systematic ablation studies

### Configuration System
- **PreprocessConfig**: Centralized configuration with dataclass structure
- **ConfigManager**: Configuration loading, validation, and serialization

## Dependencies

### Core Requirements
- Python 3.10+
- PyMuPDF (fitz) ≥ 1.23.0
- Pillow ≥ 10.0.0
- pytesseract ≥ 0.3.10
- marshmallow-dataclass ≥ 8.6.0

### Optional Dependencies
- EasyOCR ≥ 1.7.0 (for advanced OCR capabilities)
- CUDA toolkit (for GPU acceleration)

### System Requirements
- Tesseract OCR engine (system installation required)
- Sufficient RAM for large document processing (recommended: 8GB+)


## Usage

### Quick Start

```python
from preprocess_module import quick_preprocess

# Basic usage with default configuration
result = quick_preprocess(
    input_json_path="document.json",
    output_dir="output/"
)
print(f"Processing completed: {result['summary']}")
```

### Advanced Configuration

```python
from preprocess_module import PreprocessConfig, PreprocessPipeline

# Create custom configuration
config = PreprocessConfig(
    experiment_name="esg_analysis_v1",
    ocr_engine="easyocr",
    use_gpu=True,
    confidence_threshold=0.8,
    min_text_length=10,
    json_to_md_enabled=True,
    image_link_conversion_enabled=True,
    image_text_detection_enabled=True
)

# Initialize and run pipeline
pipeline = PreprocessPipeline(config)
result = pipeline.run("input.json", "output/")
```

### Batch Processing

```python
from preprocess_module import BatchPreprocessPipeline, PreprocessConfig

# Configure for batch processing
config = PreprocessConfig(
    experiment_name="batch_esg_processing",
    log_level="INFO",
    log_to_file=True
)

# Process multiple documents
batch_pipeline = BatchPreprocessPipeline(config)
results = batch_pipeline.run(
    input_directory="data/json_files/",
    output_directory="output/batch_results/"
)
```

### PDF to Image Conversion

```python
from pdftojpg import convert_pdf_to_images
from pathlib import Path

# Convert single PDF
convert_pdf_to_images(
    pdf_path=Path("document.pdf"),
    source_base_dir=Path("input/"),
    output_base_dir=Path("output/images/")
)
```

### Ablation Studies

```python
from preprocess_module import AblationExperimentRunner

# Define experimental configurations
configs = {
    "baseline": PreprocessConfig(),
    "no_ocr": PreprocessConfig(image_text_detection_enabled=False),
    "high_threshold": PreprocessConfig(confidence_threshold=0.9)
}

# Run ablation study
runner = AblationExperimentRunner()
results = runner.run_experiments(
    configs=configs,
    input_data="test_data.json",
    output_base="ablation_results/"
)
```

## Configuration Options

The `PreprocessConfig` class provides extensive customization options:

```python
@dataclass
class PreprocessConfig:
    # Experiment settings
    experiment_name: str = "default_experiment"
    
    # Path configuration
    base_dir: str = "./"
    output_dir: str = "./output"
    main_images_dir: str = "./images"
    
    # OCR settings
    ocr_engine: str = "tesseract"  # "tesseract" or "easyocr"
    use_gpu: bool = False
    confidence_threshold: float = 0.7
    min_text_length: int = 5
    
    # Processing toggles
    json_to_md_enabled: bool = True
    image_link_conversion_enabled: bool = True
    image_text_detection_enabled: bool = True
    
    # Output formatting
    add_page_markers: bool = True
    preserve_html_tables: bool = False
    validate_image_existence: bool = True
```

## Output Format

The module generates structured outputs:

- **Markdown Files**: Clean, formatted documents with standardized structure
- **Processing Reports**: Detailed JSON reports with statistics and metadata
- **Log Files**: Comprehensive processing logs for debugging and analysis
- **Configuration Files**: Serialized configuration for reproducibility

### Example Output Structure

```
output/
├── processed_document.md         # Main Markdown output
├── processing_report.json        # Detailed processing statistics
├── preprocess_config.json        # Configuration used for processing
├── preprocess_log.txt            # Processing log file
└── images/                       # Processed image directory
    ├── validated_images/         # Images with detected text
    └── filtered_images/          # Images without meaningful text
```

## Performance Considerations

- **Memory Management**: Automatic cleanup of temporary files and memory optimization
- **GPU Acceleration**: CUDA support for EasyOCR processing
- **Parallel Processing**: Multi-threading support for batch operations
- **Caching**: Intelligent caching of OCR results to avoid reprocessing

## Logging and Monitoring

Comprehensive logging system with configurable levels:

```python
# Configure logging
config = PreprocessConfig(
    log_level="DEBUG",
    log_to_file=True,
    log_file_path="processing.log"
)

# Logs include:
# - Processing timestamps and duration
# - OCR confidence scores and results
# - File validation status
# - Error handling and recovery
# - Memory usage statistics
```

## Research Applications

This post-processing module is particularly suited for:

- **ESG Report Analysis**: Structured extraction and analysis of sustainability reports
- **Document Classification**: Preparing documents for machine learning classification
- **Content Analysis**: Systematic analysis of document structure and content
- **Multi-modal Research**: Integration of text and image content analysis
- **Reproducible Research**: Configuration-driven experiments with detailed logging

## Ablation Study Support

The module includes built-in support for systematic ablation studies:

```python
# Example ablation study configurations
ablation_configs = {
    "full_pipeline": PreprocessConfig(),
    "no_image_processing": PreprocessConfig(image_text_detection_enabled=False),
    "tesseract_only": PreprocessConfig(ocr_engine="tesseract"),
    "easyocr_only": PreprocessConfig(ocr_engine="easyocr"),
    "high_confidence": PreprocessConfig(confidence_threshold=0.9)
}
```

## Acknowledgments

- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) for robust text recognition
- [EasyOCR](https://github.com/JaidedAI/EasyOCR) for deep learning-based OCR
- [PyMuPDF](https://github.com/pymupdf/PyMuPDF) for PDF processing capabilities
- [Marshmallow](https://marshmallow.readthedocs.io/) for configuration serialization

