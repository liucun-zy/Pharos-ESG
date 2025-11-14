## System Architecture

The system follows a multi-stage pipeline architecture with four main processing modules:

```
AAAI_code/
├── processing/                   # Stage 1: Raw Data Processing
│   ├── raw_data_preprocessing/   # PDF parsing and OCR
│   └── raw_data_post-processing/ # JSON to Markdown conversion
├── document_reconstruction/      # Stage 2: Document Structure Reconstruction
│   ├── ToC-RAP/                 # Table of Contents extraction
│   └── Toc_align/               # Multi-language title alignment
├── fused_readingorder/          # Stage 3: Reading Order Modeling
└── contextual_parser/           # Stage 4: AI-Enhanced Content Analysis
```

## Core Modules

### 1. Raw Data Processing (`processing/`)

#### Raw Data Preprocessing (`raw_data_preprocessing/`)
- **MinerU Integration**: Advanced PDF parsing with layout analysis
- **OCR Processing**: PaddleOCR with GPU acceleration for robust text recognition
- **Multi-language Support**: including Simplified Chinese, Traditional Chinese, and English
- **Structured Output**: JSON-formatted content with image extraction

**Key Features**:

- Table of Contents extraction with intelligent page identification
- Advanced OCR with confidence scoring and validation
- Batch processing with comprehensive logging
- GPU acceleration for enhanced performance

#### Raw Data Post-Processing (`raw_data_post-processing/`)
- **JSON to Markdown Conversion**: Intelligent transformation with formatting preservation
- **Image Link Standardization**: Automated path normalization and validation
- **OCR-based Content Filtering**: Removes images without meaningful text
- **Modular Pipeline**: Configurable processing stages with ablation study support

**Key Features**:
- Multi-engine OCR support (Tesseract/EasyOCR)
- Comprehensive configuration management
- Batch processing with parallel execution
- Quality assurance and validation

### 2. Fused Reading Order Modeling (`fused_readingorder/`)

- **Coarse-to-Fine Paradigm**: Combines macro-rule-based skeleton ordering with local learning-based fine-grained ordering
- **Theoretical Foundations**: Based on Directed Acyclic Relations (DAR) and Order Theory
- **Manhattan Layout Detection**: Intelligent classification of document layout patterns (vertical/horizontal)
- **Recursive X-Y Cut**: Advanced spatial decomposition algorithm with projection analysis
- **Relation-Aware Transformer**: Lightweight model for fine-grained relationship prediction
- **Topological Sorting**: Graph-based ordering with cycle detection and resolution

**Key Features**:
- Dual-stage architecture ensuring both global structure and local precision
- Multi-modal feature construction (content, spatial, categorical embeddings)
- Automatic model downloading from HuggingFace Hub
- Multiple execution modes (simplified, complete, adaptive)
- Comprehensive dependency resolution and error handling
- Performance monitoring and detailed analysis export

**Execution Options**:
- `simple_demo.py`: Zero-dependency version with spatial ordering
- `fused_reading_order_demo.py`: Complete system with relation modeling
- `run_demo.py`: Adaptive runner with intelligent fallback
- `setup_dependencies.py`: Automated dependency resolution

### 3. Document Reconstruction (`document_reconstruction/`)

#### Table of Contents Recognition and Parsing (`ToC-RAP/`)
- **Vision-Language Model Integration**: Qwen2.5-72B-VL-Instruct for robust image understanding
- **Advanced Rule-Based Parsing**: Seven sophisticated parsing rules for hierarchical structure
- **Intelligent Chapter Handling**: Advanced algorithms for processing section markers
- **Adaptive Image Compression**: Dynamic optimization for API constraints

**Key Features**:
- Hierarchical structure recognition (Level 1, 2, 3)
- Batch processing with error recovery
- Structured JSON output with validation
- Comprehensive retry mechanisms

#### Multi-Language Title Alignment (`Toc_align/`)
- **Multi-Language Support**: Specialized processors for Simplified Chinese, Traditional Chinese, and English
- **LLM-Powered Insertion**: Context-aware missing title insertion using large language models
- **Advanced Matching**: Fuzzy matching with language-specific optimizations
- **Batch Processing**: Efficient processing of large document collections

**Key Features**:
- Character normalization with OpenCC
- Intelligent prefix removal and cleaning
- Comprehensive token usage tracking
- High insertion success rate (>**99%**)




### 4. Contextual Parser (`contextual_parser/`)

- **Intelligent Content Clustering**: Groups related content blocks under common headings
- **VLM-Enhanced Analysis**: AI-generated image descriptions with contextual understanding
- **Multi-Modal Integration**: Seamless handling of text, images, and tables
- **Advanced API Management**: Caching, key rotation, and retry mechanisms

**Key Features**:
- Seven-category image classification system
- Context-aware prompt engineering
- Cross-platform path generation
- Comprehensive metadata extraction

## Installation

### Quick Start

```bash
# Install dependencies for all modules
find . -name "requirements.txt" -exec pip install -r {} \;

# Or install module-specific dependencies
cd processing/raw_data_preprocessing && pip install -r requirements.txt
cd ../raw_data_post-processing && pip install -r requirements.txt
cd ../../document_reconstruction/ToC-RAP && pip install -r requirements.txt
cd ../Toc_align && pip install -r requirements.txt
cd ../../contextual_parser && pip install -r requirements.txt
```

## Usage

### Complete Pipeline

```python
# Stage 1: Raw Data Processing
from processing.raw_data_preprocessing.optimized_ocr import OCRProcessor
from processing.raw_data_post_processing.preprocess_module import quick_preprocess

# Process PDF to structured JSON
ocr_processor = OCRProcessor(use_gpu=True)
ocr_result = ocr_processor.process_pdf("document.pdf", "output/")

# Convert to Markdown
markdown_result = quick_preprocess("document.json", "markdown_output/")

# Stage 2: Document Reconstruction
from document_reconstruction.ToC_RAP.ToC_RAP import extract_titles_from_image
from document_reconstruction.Toc_align.CN_titles_aligner import batch_align_titles

# Extract table of contents
toc_result = extract_titles_from_image("toc_image.jpg")

# Align titles
batch_align_titles("documents/", "your_api_key")

# Stage 3: Fused Reading Order Modeling
from fused_readingorder.fused_reading_order_demo import FusedReadingOrderModel

# Generate reading order with complete coarse-to-fine pipeline
fused_model = FusedReadingOrderModel(
    confidence_threshold=0.6,
    enable_micro_ordering=True
)
reading_order = fused_model.generate_reading_order(page_elements)

# Alternative: Use simplified version for quick testing
# from fused_readingorder.simple_demo import SimplifiedFusedModel
# simple_model = SimplifiedFusedModel()
# reading_order = simple_model.generate_reading_order(page_elements)

# Stage 4: Contextual Analysis
from contextual_parser.content_clusterer import batch_process_directory
from contextual_parser.vlm_processor import PipelineManager, Config

# Cluster content
batch_process_directory("aligned_documents/")

# Enhance with VLM
pipeline = PipelineManager(Config())
pipeline.run_batch("clustered_documents/")
```

### Module-Specific Usage

Each module can be used independently. Refer to individual module READMEs for detailed usage instructions:

- [Raw Data Preprocessing](processing/raw_data_preprocessing/README.md)
- [Raw Data Post-Processing](processing/raw_data_post-processing/README.md)
- [ToC-RAP](document_reconstruction/ToC-RAP/README.md)
- [Multi-Language Title Alignment](document_reconstruction/Toc_align/README.md)
- [Contextual Parser](contextual_parser/README.md)

## Performance Benchmarks

### Processing Speed
- **PDF Processing**: ~40-50 seconds per page (with GPU)
- **OCR Recognition**: ~10-20 seconds per page
- **Title Alignment**: ~15-25 seconds per document
- **VLM Analysis**: ~20-30 seconds per image
- **Complete Pipeline**: ~1-3 minutes per document

### Key Performance Indicators
The overall performance of the pipeline is measured through the evaluation of its core modules, and the following key results have been achieved:
- Layout Analysis: The system achieved an F1-Score of **92.04%** on the initial document structuring task, providing a reliable layout foundation for subsequent modules.
- Reading Order Modeling: Using the Kendall's Tau metric to measure the correlation between the predicted and ground-truth sequences, our model scored **0.92**, demonstrating its precision in capturing complex document flows.
- ToC Parsing (ToC-RAP): For the core table of contents parsing module, we achieved a comprehensive accuracy of **94.84%** on the combined task of restoring hierarchical relationships and textual content.
- Hierarchical Alignment & Insertion: On the most challenging alignment tasks requiring anchor-based reasoning (i.e., Stage 2 of ToC-ALIGN), the model reached an insertion accuracy of **92.46%**, showcasing its robustness in handling ambiguous matches.

### Scalability
- **Batch Processing**: 60-180 documents per hour
- **API Efficiency**: >95% success rate with retry mechanisms

### Academic Research
- **Document Understanding**: Large-scale analysis of research papers
- **Cross-Language Studies**: Comparative analysis across language variants
- **Layout Analysis**: Systematic study of document structures
- **Multi-Modal Learning**: Integration of text and visual information

### Industrial Applications
- **ESG Report Processing**: Automated analysis of sustainability reports
- **Financial Document Analysis**: Annual reports and regulatory filings
- **Legal Document Processing**: Contract and compliance analysis
- **Technical Documentation**: Software manuals and API documentation

### Evaluation Datasets
- **ESG Reports**: 30000+ corporate sustainability reports

## Acknowledgments

- **MinerU**: Advanced PDF parsing and layout analysis
- **PaddleOCR**: Robust multi-language OCR capabilities
- **OpenCC**: Chinese character conversion
- **DeepSeek AI**: Large language model API
- **Volcano Engine**: Vision-language model services
- **Qwen-VL**: State-of-the-art vision-language understanding

### Supported Formats

- **Input**: PDF, JPEG, PNG, TIFF
- **Intermediate**: JSON, Markdown, HTML
- **Output**: JSON, Markdown, CSV

### API Compatibility

- **OpenAI-compatible**: GPT-4V, GPT-4-Turbo
- **Alibaba Cloud**: Qwen2.5-VL
- **DeepSeek**: DeepSeek-V3
- **Custom**: Any OpenAI-compatible endpoint
