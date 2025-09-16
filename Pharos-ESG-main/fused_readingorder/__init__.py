#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fused Reading Order Modeling Package.

This package implements a comprehensive "coarse-to-fine" paradigm for document
reading order prediction, combining macro-rule-based skeleton ordering with
local learning-based fine-grained ordering.

Modules:
    layout: Macro-level spatial analysis and layout detection
    relation_model: Micro-level relationship modeling and prediction
    demo: Complete integration and demonstration

Example:
    >>> from fused_readingorder import FusedReadingOrderModel, DocumentElement, BoundingBox
    >>> 
    >>> # Create document elements
    >>> elements = [
    ...     DocumentElement(1, "Title", BoundingBox(50, 50, 300, 80), "title"),
    ...     DocumentElement(2, "Content", BoundingBox(50, 100, 300, 200), "text"),
    ... ]
    >>> 
    >>> # Initialize model and generate reading order
    >>> model = FusedReadingOrderModel()
    >>> ordered_elements = model.generate_reading_order(elements)
"""

__version__ = "1.0.0"
__author__ = "ICLR Research Team"
__email__ = "research@example.com"
__description__ = "Fused Reading Order Modeling: Coarse-to-Fine Document Analysis"

# Import core classes and functions
try:
    from .layout import (
        DocumentElement,
        BoundingBox,
        LayoutType,
        SplitDirection,
        RegionNode,
        LayoutAnalyzer,
        ManhattanLayoutDetector,
        RecursiveXYCut,
        ProjectionAnalyzer
    )
    
    from .relation_model import (
        MicroOrderModel,
        RelationAwareTransformer,
        DirectedAcyclicGraph,
        RelationType,
        RelationFeatures,
        FeatureExtractor,
        ContentEncoder,
        CategoryEncoder,
        ModelManager
    )
    
    from .fused_reading_order_demo import (
        FusedReadingOrderModel,
        create_sample_document
    )
    
except ImportError as e:
    # Handle import errors gracefully for development
    import warnings
    warnings.warn(f"Some modules could not be imported: {e}", ImportWarning)
    
    # Define minimal interface
    class DocumentElement:
        """Fallback DocumentElement class."""
        def __init__(self, element_id, content, bbox, category, confidence=1.0):
            self.element_id = element_id
            self.content = content
            self.bbox = bbox
            self.category = category
            self.confidence = confidence
    
    class BoundingBox:
        """Fallback BoundingBox class."""
        def __init__(self, x1, y1, x2, y2):
            self.x1 = x1
            self.y1 = y1
            self.x2 = x2
            self.y2 = y2
        
        @property
        def center(self):
            return ((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)

# Define public API
__all__ = [
    # Core data structures
    'DocumentElement',
    'BoundingBox',
    'LayoutType',
    'SplitDirection',
    'RegionNode',
    'RelationType',
    'RelationFeatures',
    
    # Layout analysis
    'LayoutAnalyzer',
    'ManhattanLayoutDetector',
    'RecursiveXYCut',
    'ProjectionAnalyzer',
    
    # Relation modeling
    'MicroOrderModel',
    'RelationAwareTransformer',
    'DirectedAcyclicGraph',
    'FeatureExtractor',
    'ContentEncoder',
    'CategoryEncoder',
    'ModelManager',
    
    # Main interface
    'FusedReadingOrderModel',
    'create_sample_document',
]

# Package metadata
__package_info__ = {
    'name': 'fused_readingorder',
    'version': __version__,
    'description': __description__,
    'author': __author__,
    'email': __email__,
    'url': 'https://github.com/example/fused-reading-order',
    'license': 'MIT',
    'keywords': [
        'document analysis',
        'reading order',
        'layout analysis',
        'transformer',
        'computer vision',
        'natural language processing'
    ],
    'classifiers': [
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Topic :: Scientific/Engineering :: Artificial Intelligence',
        'Topic :: Text Processing :: Linguistic',
    ]
}

# Compatibility checks
def check_dependencies():
    """Check if all required dependencies are available."""
    missing_deps = []
    
    try:
        import torch
        if torch.__version__ < '2.0.0':
            missing_deps.append('torch>=2.0.0')
    except ImportError:
        missing_deps.append('torch>=2.0.0')
    
    try:
        import transformers
    except ImportError:
        missing_deps.append('transformers>=4.33.0')
    
    try:
        import numpy
    except ImportError:
        missing_deps.append('numpy>=1.24.0')
    
    try:
        import cv2
    except ImportError:
        missing_deps.append('opencv-python>=4.8.0')
    
    if missing_deps:
        import warnings
        warnings.warn(
            f"Missing dependencies: {', '.join(missing_deps)}. "
            "Some functionality may not be available.",
            ImportWarning
        )
    
    return len(missing_deps) == 0

# Run dependency check on import
check_dependencies()

# Utility functions
def get_version():
    """Get package version."""
    return __version__

def get_package_info():
    """Get complete package information."""
    return __package_info__.copy()

def list_models():
    """List available pre-trained models."""
    return [
        'sentence-transformers/all-MiniLM-L6-v2',
        'sentence-transformers/all-mpnet-base-v2',
        'microsoft/layoutlm-base-uncased',
        'microsoft/layoutlmv3-base'
    ]

# Configuration
class Config:
    """Global configuration for the package."""
    
    # Model settings
    DEFAULT_CONFIDENCE_THRESHOLD = 0.5
    DEFAULT_MODEL_CACHE_DIR = './models'
    
    # Layout analysis settings
    DEFAULT_ASPECT_RATIO_THRESHOLD = 1.5
    DEFAULT_MIN_GAP_RATIO = 0.02
    DEFAULT_MIN_PROJECTION_RATIO = 0.01
    
    # Relation model settings
    DEFAULT_HIDDEN_DIM = 256
    DEFAULT_NUM_HEADS = 8
    DEFAULT_NUM_LAYERS = 2
    DEFAULT_DROPOUT = 0.1
    
    # Processing settings
    DEFAULT_BATCH_SIZE = 32
    DEFAULT_MAX_ELEMENTS = 1000
    
    @classmethod
    def get_default_config(cls):
        """Get default configuration dictionary."""
        return {
            'confidence_threshold': cls.DEFAULT_CONFIDENCE_THRESHOLD,
            'model_cache_dir': cls.DEFAULT_MODEL_CACHE_DIR,
            'aspect_ratio_threshold': cls.DEFAULT_ASPECT_RATIO_THRESHOLD,
            'min_gap_ratio': cls.DEFAULT_MIN_GAP_RATIO,
            'min_projection_ratio': cls.DEFAULT_MIN_PROJECTION_RATIO,
            'hidden_dim': cls.DEFAULT_HIDDEN_DIM,
            'num_heads': cls.DEFAULT_NUM_HEADS,
            'num_layers': cls.DEFAULT_NUM_LAYERS,
            'dropout': cls.DEFAULT_DROPOUT,
            'batch_size': cls.DEFAULT_BATCH_SIZE,
            'max_elements': cls.DEFAULT_MAX_ELEMENTS
        }

# Add Config to public API
__all__.append('Config')