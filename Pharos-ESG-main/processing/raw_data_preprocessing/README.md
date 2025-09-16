# Raw Data Preprocessing Module

## Overview

This module provides a comprehensive preprocessing pipeline for raw document data, specifically designed for academic research applications. The module integrates state-of-the-art OCR technologies, layout analysis, and document parsing capabilities to transform unstructured PDF documents into structured, machine-readable formats suitable for downstream analysis tasks.

## Key Features

- **Advanced OCR Processing**: Leverages PaddleOCR with GPU acceleration for robust text recognition across multiple languages
- **Table of Contents Extraction**: Intelligent identification and extraction of TOC pages from PDF documents
- **Layout Analysis**: Sophisticated document layout understanding using the MinerU framework
- **Batch Processing**: Efficient processing of large document collections with progress tracking
- **Structured Output**: Generates JSON-formatted structured data with associated image extraction
- **Configuration Management**: Flexible configuration system for different processing scenarios

## Architecture

The preprocessing module consists of several core components:

```
raw_data_preprocessing/
├── optimized_ocr.py          # OCR processing and TOC extraction
├── layoutanalysis.py         # Document layout analysis using MinerU
├── clean_empty_folders.py    # Utility for cleaning empty directories
├── fix_ssh_config.py         # SSH configuration management
├── MinerU-master/            # Integrated MinerU library
└── pyrightconfig.json        # Python type checking configuration
```

## Usage

### Basic OCR Processing

```python
from optimized_ocr import OCRProcessor

# Initialize OCR processor
processor = OCRProcessor(use_gpu=True)

# Process a single PDF
result = processor.process_pdf('input.pdf', output_dir='output/')

# Batch process multiple PDFs
processor.batch_process('input_directory/', 'output_directory/')
```

### Layout Analysis with MinerU

```python
from layoutanalysis import DocumentProcessor

# Initialize document processor
processor = DocumentProcessor()

# Process PDF to structured JSON
processor.process_document(
    pdf_path='document.pdf',
    output_dir='structured_output/',
    extract_images=True
)
```

### Utility Functions

```python
from clean_empty_folders import clean_empty_directories
from fix_ssh_config import fix_ssh_config

# Clean empty folders after processing
clean_empty_directories('output_directory/')

# Fix SSH configuration for remote processing
fix_ssh_config()
```

## Configuration

The module supports flexible configuration through `pyrightconfig.json` for development environments and runtime parameters:

```json
{
    "pythonVersion": "3.11",
    "extraPaths": ["./MinerU-master"],
    "typeCheckingMode": "basic"
}
```

## Output Format

The preprocessing pipeline generates structured outputs:

- **JSON Files**: `content_list.json` containing structured document content
- **Images**: Extracted figures, tables, and diagrams
- **Metadata**: Processing logs and configuration details

### Example Output Structure

```json
{
    "pages": [
        {
            "page_number": 1,
            "text_blocks": [...],
            "tables": [...],
            "images": [...],
            "layout_info": {...}
        }
    ],
    "metadata": {
        "processing_time": "2024-01-01T12:00:00",
        "ocr_confidence": 0.95,
        "total_pages": 10
    }
}
```

## Performance Considerations

- **GPU Acceleration**: Recommended for large-scale processing
- **Memory Management**: Automatic cleanup of temporary files
- **Batch Processing**: Optimized for processing multiple documents
- **Progress Tracking**: Real-time processing status with tqdm

## Logging and Debugging

The module provides comprehensive logging:

```python
import logging

# Configure logging level
logging.basicConfig(level=logging.INFO)

# Processing logs include:
# - OCR confidence scores
# - Processing time per document
# - Error handling and recovery
# - Memory usage statistics
```

## Acknowledgments

- [MinerU](https://github.com/opendatalab/MinerU) for advanced document parsing capabilities
- [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) for robust OCR functionality
- [PyMuPDF](https://github.com/pymupdf/PyMuPDF) for PDF processing utilities

