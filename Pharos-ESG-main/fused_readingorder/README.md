# Fused Reading Order Modeling: Coarse-to-Fine Document Analysis

## Overview

This module implements a comprehensive **"coarse-to-fine" paradigm** for document reading order prediction, combining macro-rule-based skeleton ordering with local learning-based fine-grained ordering. The system is grounded in theoretical foundations from order theory and directed acyclic relations, providing both computational efficiency and high accuracy for complex document layouts.

## Key Features

- **Dual-Stage Architecture**: Combines spatial geometry rules with deep learning models
- **Theoretical Foundations**: Based on Directed Acyclic Relations (DAR) and Order Theory
- **Manhattan Layout Detection**: Intelligent classification of document layout patterns
- **Recursive X-Y Cut**: Advanced spatial decomposition algorithm
- **Relation-Aware Transformer**: Lightweight model for relationship prediction
- **Topological Sorting**: Graph-based ordering with cycle detection
- **Comprehensive Analysis**: Detailed structure analysis and visualization

## Architecture

The system implements a two-stage pipeline:

```
fused_readingorder/
├── layout.py                      # Stage 1: Macro-level spatial analysis
├── relation_model.py              # Stage 2: Micro-level relationship modeling
├── fused_reading_order.py    # Complete integration and demonstration
├── simple_demo.py                 # Simplified version for quick testing
├── run_demo.py                    # Adaptive runner with dependency detection
├── setup_dependencies.py          # Automated dependency resolution
├── requirements.txt               # Python dependencies
└── README.md                     # Documentation
```

## Theoretical Framework

### Stage 1: Macro-Rule-Based Skeleton Ordering

**Equation (3-1): Spatial Relation Discrimination**
```
Layout_type = f_spatial(E_page)
```

**Equation (3-2): Depth-First Traversal**
```
R_page^macro = DFS(RegionTree)
```

### Stage 2: Local Learning-Based Fine-Grained Ordering

**Equation (3-3): Region Content Encoding**
```
D_r = {(w_i, b_i, c_i)}_{i=1}^{N_r}
```

**Equation (3-4): Multi-Modal Feature Construction**
```
φ_ij = [E(w_i), E(w_j), Δy_ij, Δx_ij, IoU(b_i, b_j), Dist(b_i, b_j), E(c_i), E(c_j)]
```

**Equation (3-5): Relation-Aware Transformer**
```
s_ij = σ(W · Transformer(φ_ij) + b)
```

**Equation (3-6): Graph Construction and Topological Sorting**
```
R_r^micro = TopoSort(G_r)
```

**Equation (3-7): Final Fusion**
```
R_p = ⋃_{r∈R_p^macro} R_r^micro
```

## Core Components

### 1. Layout Analysis (`layout.py`)

#### ManhattanLayoutDetector
- **Spatial Analysis**: Detects dominant layout patterns (vertical/horizontal Manhattan)
- **Column/Row Structure**: Analyzes spatial distribution and alignment
- **Confidence Scoring**: Provides reliability metrics for layout classification

#### RecursiveXYCut
- **Projection Analysis**: Computes spatial projections along x/y axes
- **Gap Detection**: Identifies significant whitespace for region splitting
- **Hierarchical Decomposition**: Builds region trees through recursive splitting

#### LayoutAnalyzer
- **Integrated Pipeline**: Coordinates layout detection and region tree construction
- **DFS Traversal**: Extracts macro-level reading order from spatial hierarchy

### 2. Relation Modeling (`relation_model.py`)

#### FeatureExtractor
- **Content Encoding**: Uses sentence transformers for semantic embeddings
- **Spatial Features**: Computes geometric relationships (Δx, Δy, IoU, distance)
- **Category Encoding**: One-hot encoding for element types

#### RelationAwareTransformer
- **Lightweight Architecture**: Efficient transformer for relationship prediction
- **Multi-Head Attention**: Captures complex spatial-semantic relationships
- **Confidence Scoring**: Outputs relationship probabilities

#### DirectedAcyclicGraph
- **Cycle Detection**: Ensures acyclic property of relationship graphs
- **Topological Sorting**: Kahn's algorithm for linear ordering
- **Transitive Closure**: Computes complete relationship matrix

#### MicroOrderModel
- **End-to-End Pipeline**: Integrates feature extraction, prediction, and sorting
- **Cycle Resolution**: Handles conflicting relationships gracefully
- **Fallback Mechanisms**: Spatial sorting when graph methods fail

### 3. Fused Integration (`fused_reading_order.py`)

#### FusedReadingOrderModel
- **Complete Pipeline**: Orchestrates macro and micro stages
- **Performance Monitoring**: Tracks processing statistics
- **Result Export**: JSON and text format outputs
- **Comprehensive Analysis**: Detailed structure examination

## Installation

### Prerequisites
- Python 3.8+
- PyTorch 2.0+
- CUDA-compatible GPU (recommended)

### Development Installation

```bash
# Install with development dependencies
pip install -r requirements.txt
pip install pytest black flake8 mypy

# Run tests
pytest tests/

# Format code
black .
isort .
```

## Quick Start Guide

### Execution Options

This system provides multiple execution modes to accommodate different dependency environments and use cases:

#### 1. Simplified Demo (Recommended for Initial Testing)

```bash
# Run immediately without dependency conflicts
python simple_demo.py
```

**Features:**
-  **Zero Setup**: Works with minimal dependencies
-  **Macro Analysis**: Complete spatial layout detection and region decomposition
-  **Spatial Ordering**: Geometric rule-based reading order generation
-  **Fast Execution**: Immediate results for algorithm validation

**Use Cases:**
- Algorithm verification and testing
- Baseline comparison for research
- Quick demonstration of coarse-grained ordering

#### 2. Complete System (Full Coarse-to-Fine Pipeline)

```bash
# Run complete system with relation modeling
python fused_reading_order.py
```

**Features:**
-  **Full Pipeline**: Complete "coarse-to-fine" paradigm implementation
-  **Relation Modeling**: Transformer-based fine-grained relationship prediction
-  **Comprehensive Analysis**: Detailed performance metrics and structure analysis
-  **Result Export**: JSON and text format outputs with metadata

**Prerequisites:**
- PyTorch 2.0+
- Transformers 4.33+
- Sentence Transformers 2.2+

#### 3. Adaptive Runner (Intelligent Fallback)

```bash
# Automatically selects appropriate version based on available dependencies
python run_demo.py
```

**Features:**
-  **Dependency Detection**: Automatically checks available packages
-  **Graceful Degradation**: Falls back to simplified version if needed
-  **Setup Guidance**: Provides clear instructions for missing dependencies

### Usage Examples

#### Basic Usage (Simplified Version)

```python
from layout import DocumentElement, BoundingBox, LayoutAnalyzer

# Create document elements
elements = [
    DocumentElement(1, "Title", BoundingBox(50, 50, 300, 80), "title"),
    DocumentElement(2, "Content", BoundingBox(50, 100, 300, 200), "text"),
    DocumentElement(3, "Image", BoundingBox(350, 100, 600, 200), "image"),
]

# Run layout analysis
analyzer = LayoutAnalyzer()
layout_type, region_tree = analyzer.analyze_layout(elements)
macro_blocks = analyzer.get_macro_reading_order(region_tree)

print(f"Layout Type: {layout_type.value}")
print(f"Macro Blocks: {len(macro_blocks)}")
```

#### Advanced Usage (Complete System)

```python
from fused_reading_order_demo import FusedReadingOrderModel

# Initialize complete model
model = FusedReadingOrderModel(
    confidence_threshold=0.6,
    enable_micro_ordering=True
)

# Generate reading order with full pipeline
ordered_elements = model.generate_reading_order(elements)

# Comprehensive analysis
analysis = model.analyze_document_structure(elements)
print(f"Processing Time: {analysis['processing_stats']['processing_time']:.2f}s")
print(f"Micro Sorted Blocks: {analysis['processing_stats']['micro_sorted_blocks']}")

# Export results
model.export_results(elements, "analysis.json", "json")
```

### Advanced Configuration

```python
# Custom model configuration
model = FusedReadingOrderModel(
    confidence_threshold=0.7,
    model_path="./models/custom_rat.pth",
    enable_micro_ordering=True
)

# Comprehensive analysis
analysis = model.analyze_document_structure(elements)
print(f"Layout Type: {analysis['layout_analysis']['layout_type']}")
print(f"Processing Time: {analysis['processing_stats']['processing_time']:.2f}s")

# Export results
model.export_results(elements, "analysis.json", "json")
model.export_results(elements, "report.txt", "txt")
```

### Layout-Only Analysis

```python
from layout import LayoutAnalyzer

# Initialize layout analyzer
analyzer = LayoutAnalyzer()

# Analyze layout
layout_type, region_tree = analyzer.analyze_layout(elements)
macro_blocks = analyzer.get_macro_reading_order(region_tree)

print(f"Detected Layout: {layout_type.value}")
print(f"Macro Blocks: {len(macro_blocks)}")
```

### Relation-Only Modeling

```python
from relation_model import MicroOrderModel

# Initialize micro-order model
micro_model = MicroOrderModel(confidence_threshold=0.5)

# Sort elements within a region
sorted_elements = micro_model.sort_elements(elements)

print("Micro-order results:")
for elem in sorted_elements:
    print(f"- {elem.content}")
```

## Model Management

### Automatic Model Download

The system automatically downloads required models from HuggingFace Hub:

```python
from relation_model import ModelManager

# Initialize model manager
manager = ModelManager(cache_dir="./models")

# Download specific model
model_path = manager.download_model("sentence-transformers/all-MiniLM-L6-v2")

# Load pre-trained RAT model
rat_model = manager.load_pretrained_rat("./models/rat_model.pth")
```

### Custom Model Training

```python
from relation_model import RelationAwareTransformer
import torch

# Create custom RAT model
model = RelationAwareTransformer(
    input_dim=776,
    hidden_dim=256,
    num_heads=8,
    num_layers=2
)

# Training loop (example)
optimizer = torch.optim.Adam(model.parameters(), lr=1e-4)
criterion = torch.nn.BCELoss()

for batch in training_data:
    features, labels = batch
    predictions = model(features)
    loss = criterion(predictions, labels)
    
    optimizer.zero_grad()
    loss.backward()
    optimizer.step()

# Save trained model
torch.save(model.state_dict(), "custom_rat.pth")
```

## Configuration Options

### Layout Analysis Configuration

```python
from layout import ManhattanLayoutDetector, ProjectionAnalyzer

# Layout detector settings
detector = ManhattanLayoutDetector(aspect_ratio_threshold=1.5)

# Projection analyzer settings
analyzer = ProjectionAnalyzer(
    min_gap_ratio=0.02,
    min_projection_ratio=0.01
)
```

### Relation Model Configuration

```python
from relation_model import MicroOrderModel, ContentEncoder

# Content encoder settings
encoder = ContentEncoder(model_name="sentence-transformers/all-MiniLM-L6-v2")

# Micro-order model settings
model = MicroOrderModel(
    confidence_threshold=0.6,
    model_path="./models/rat_model.pth"
)
```

## Algorithm Details

### Manhattan Layout Detection

1. **Spatial Analysis**:
   ```python
   aspect_ratio = page_width / page_height
   column_analysis = analyze_column_structure(elements)
   row_analysis = analyze_row_structure(elements)
   ```

2. **Decision Logic**:
   ```python
   if column_analysis['confidence'] > 0.7:
       return VERTICAL_MANHATTAN if aspect_ratio < threshold else HORIZONTAL_MANHATTAN
   elif row_analysis['confidence'] > 0.7:
       return HORIZONTAL_MANHATTAN
   else:
       return MIXED_LAYOUT
   ```

### Recursive X-Y Cut Algorithm

1. **Projection Computation**:
   ```python
   projection = compute_projection(boxes, axis)
   region_starts, region_ends = find_split_points(projection)
   ```

2. **Recursive Splitting**:
   ```python
   for start, end in zip(region_starts, region_ends):
       child_elements = filter_elements_in_region(elements, region)
       child_node = recursive_split(child_elements, next_direction)
   ```

### Relation-Aware Transformer

1. **Feature Processing**:
   ```python
   x = input_projection(features)  # [batch, hidden_dim]
   x = transformer(x.unsqueeze(1))  # Add sequence dimension
   output = output_projection(x.squeeze(1))  # [batch, 1]
   ```

2. **Relationship Prediction**:
   ```python
   confidence = sigmoid(W · transformer_output + b)
   edge_exists = confidence > threshold
   ```

### Topological Sorting (Kahn's Algorithm)

1. **In-Degree Calculation**:
   ```python
   in_degree = {node: 0 for node in graph}
   for node in graph:
       for neighbor in graph[node]:
           in_degree[neighbor] += 1
   ```

2. **Sorting Process**:
   ```python
   queue = [node for node, degree in in_degree.items() if degree == 0]
   while queue:
       current = queue.pop(0)
       result.append(current)
       for neighbor in graph[current]:
           in_degree[neighbor] -= 1
           if in_degree[neighbor] == 0:
               queue.append(neighbor)
   ```

## Input/Output Format

### Input: Document Elements

```python
DocumentElement(
    element_id=1,
    content="Sample text content",
    bbox=BoundingBox(x1=50, y1=100, x2=300, y2=150),
    category="text",
    confidence=0.95
)
```

### Output: Analysis Results

```json
{
  "layout_analysis": {
    "layout_type": "vertical_manhattan",
    "num_regions": 5,
    "max_depth": 3,
    "region_tree_summary": {...}
  },
  "reading_order": {
    "final_order": [1, 2, 5, 3, 4],
    "macro_blocks": [[1, 2], [5], [3, 4]],
    "num_macro_blocks": 3,
    "avg_block_size": 1.67
  },
  "processing_stats": {
    "total_elements": 5,
    "macro_blocks": 3,
    "micro_sorted_blocks": 2,
    "processing_time": 1.23
  }
}
```

## Research Applications

### Academic Document Analysis
- **Research Papers**: Multi-column layouts with figures and tables
- **Conference Proceedings**: Complex nested structures
- **Thesis Documents**: Long-form academic content

### Business Document Processing
- **Annual Reports**: Financial statements and narratives
- **ESG Reports**: Sustainability and governance content
- **Technical Manuals**: Structured procedural documents

### Digital Publishing
- **Magazine Layouts**: Multi-column designs with media
- **Newspaper Articles**: Complex editorial layouts
- **Web Content**: Responsive design analysis

## Evaluation Framework

### Metrics

```python
def evaluate_reading_order(predicted, ground_truth):
    """
    Evaluation metrics:
    - Kendall's Tau: Rank correlation
    - Spearman's Rho: Monotonic relationship
    - Edit Distance: Sequence similarity
    - Block Accuracy: Macro-level correctness
    """
    tau = kendall_tau(predicted, ground_truth)
    rho = spearman_rho(predicted, ground_truth)
    edit_dist = edit_distance(predicted, ground_truth)
    block_acc = block_accuracy(predicted, ground_truth)
    
    return {
        'kendall_tau': tau,
        'spearman_rho': rho,
        'edit_distance': edit_dist,
        'block_accuracy': block_acc
    }
```

### Benchmarking

```python
# Run benchmark on test dataset
results = []
for document in test_dataset:
    predicted = model.generate_reading_order(document.elements)
    metrics = evaluate_reading_order(predicted, document.ground_truth)
    results.append(metrics)

# Aggregate results
avg_metrics = {
    metric: np.mean([r[metric] for r in results])
    for metric in results[0].keys()
}
```

## Limitations and Future Work

### Current Limitations
- **Complex Nested Layouts**: Performance degrades with >4 nesting levels
- **Non-Manhattan Layouts**: Limited support for circular or irregular layouts
- **Language Dependency**: Optimized for left-to-right reading languages
- **Model Size**: Transformer models require significant memory

### Future Enhancements
- **Multi-Language Support**: Bidirectional and vertical text support
- **Dynamic Thresholding**: Adaptive confidence thresholds
- **Online Learning**: Continuous model improvement
- **3D Layout Support**: Depth-aware spatial analysis
- **Real-Time Processing**: Streaming document analysis

## Acknowledgments

- **Order Theory**: Mathematical foundations from lattice theory and directed acyclic relations
- **Graph Algorithms**: Topological sorting and cycle detection algorithms
- **Transformer Architecture**: Attention mechanisms for spatial-semantic relationship modeling
- **Open Source Libraries**: HuggingFace Transformers, PyTorch, OpenCV, and Sentence Transformers
- **Research Community**: Contributions to document understanding and layout analysis
