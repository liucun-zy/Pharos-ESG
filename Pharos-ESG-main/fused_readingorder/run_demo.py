#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Standalone demo runner for Fused Reading Order Modeling.

This script can be run directly without package installation issues.
"""

import sys
import os
from pathlib import Path

# Add current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Check and install missing dependencies
def check_dependencies():
    """Check and install required dependencies."""
    missing_deps = []
    
    try:
        import torch
        print(f"✓ PyTorch {torch.__version__} found")
    except ImportError:
        missing_deps.append('torch')
    
    try:
        import transformers
        print(f"✓ Transformers {transformers.__version__} found")
    except ImportError:
        missing_deps.append('transformers')
        
    try:
        import sentence_transformers
        print(f"✓ Sentence Transformers {sentence_transformers.__version__} found")
    except ImportError:
        print("⚠ Sentence Transformers not found, will use fallback embeddings")
    
    try:
        import numpy
        print(f"✓ NumPy {numpy.__version__} found")
    except ImportError:
        missing_deps.append('numpy')
    
    try:
        import cv2
        print(f"✓ OpenCV {cv2.__version__} found")
    except ImportError:
        missing_deps.append('opencv-python')
    
    if missing_deps:
        print(f"\n Missing dependencies: {', '.join(missing_deps)}")
        print("Please install them using:")
        print(f"pip install {' '.join(missing_deps)}")
        return False
    
    return True

def run_simple_demo():
    """Run a simplified demo without complex dependencies."""
    print("\n=== Simplified Fused Reading Order Demo ===")
    
    # Import basic components
    from layout import DocumentElement, BoundingBox, LayoutAnalyzer
    
    # Create sample elements
    elements = [
        DocumentElement(1, "Corporate Governance Report", BoundingBox(50, 50, 300, 80), "title"),
        DocumentElement(2, "Executive Summary: This report outlines our governance framework...", 
                       BoundingBox(50, 100, 300, 180), "text"),
        DocumentElement(3, "Board Structure Overview", BoundingBox(50, 200, 300, 220), "text"),
        DocumentElement(4, "Key Performance Indicators", BoundingBox(350, 50, 600, 80), "title"),
        DocumentElement(5, "Figure 1: Governance Metrics", BoundingBox(350, 100, 600, 200), "image"),
        DocumentElement(6, "Risk Management Framework", BoundingBox(350, 280, 600, 300), "text"),
    ]
    
    print(f"\nInput: {len(elements)} document elements")
    for elem in elements:
        print(f"  ID {elem.element_id}: {elem.category} - {elem.content[:40]}...")
    
    # Run layout analysis only
    print("\nRunning layout analysis...")
    analyzer = LayoutAnalyzer()
    layout_type, region_tree = analyzer.analyze_layout(elements)
    macro_blocks = analyzer.get_macro_reading_order(region_tree)
    
    print(f"\n=== Layout Analysis Results ===")
    print(f"Layout Type: {layout_type.value}")
    print(f"Number of Regions: {len(macro_blocks)}")
    
    # Simple spatial sorting for final order
    final_order = []
    for block in macro_blocks:
        sorted_block = sorted(block, key=lambda e: (e.bbox.center[1], e.bbox.center[0]))
        final_order.extend(sorted_block)
    
    print(f"\n=== Final Reading Order (Spatial Sorting) ===")
    for i, elem in enumerate(final_order):
        print(f"{i+1:2d}. ID {elem.element_id}: {elem.category:8s} - {elem.content[:50]}...")
    
    print("\n✓ Demo completed successfully!")
    print("\nNote: This is a simplified version using only layout analysis.")
    print("For full functionality with relation modeling, please install all dependencies.")

def run_full_demo():
    """Run the complete demo with all features."""
    try:
        # Import the full demo
        from fused_readingorder.fused_reading_order import main
        print("\n=== Running Full Fused Reading Order Demo ===")
        main()
    except ImportError as e:
        print(f"\n Cannot run full demo due to missing dependencies: {e}")
        print("Falling back to simplified demo...")
        run_simple_demo()
    except Exception as e:
        print(f"\n Error in full demo: {e}")
        print("Falling back to simplified demo...")
        run_simple_demo()

if __name__ == "__main__":
    print("Fused Reading Order Modeling - Demo Runner")
    print("=" * 50)
    
    # Check dependencies
    print("\nChecking dependencies...")
    deps_ok = check_dependencies()
    
    if deps_ok:
        # Try to run full demo
        run_full_demo()
    else:
        # Run simplified demo
        print("\nRunning simplified demo without complex dependencies...")
        run_simple_demo()