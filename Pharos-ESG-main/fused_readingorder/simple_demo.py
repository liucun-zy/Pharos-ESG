#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simplified Fused Reading Order Demo.

This version works without complex dependencies and demonstrates
the core layout analysis functionality.
"""

import logging
import numpy as np
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import json
import time

# Import basic layout components
from layout import (
    DocumentElement, BoundingBox, LayoutType, RegionNode,
    LayoutAnalyzer
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SimplifiedFusedModel:
    """
    Simplified version of the Fused Reading Order Model.
    
    This version uses only layout analysis without the complex
    relation modeling components that require heavy dependencies.
    """
    
    def __init__(self):
        """Initialize the simplified model."""
        logger.info("Initializing Simplified Fused Reading Order Model")
        self.layout_analyzer = LayoutAnalyzer()
        
        self.processing_stats = {
            'total_elements': 0,
            'macro_blocks': 0,
            'processing_time': 0.0
        }
    
    def generate_reading_order(self, page_elements: List[DocumentElement]) -> List[DocumentElement]:
        """
        Generate reading order using layout analysis and spatial sorting.
        
        Args:
            page_elements: All document elements on the page
            
        Returns:
            List of elements in reading order
        """
        start_time = time.time()
        
        logger.info("=== Starting Simplified Reading Order Generation ===")
        logger.info(f"Processing {len(page_elements)} elements")
        
        if not page_elements:
            return []
        
        # Update statistics
        self.processing_stats['total_elements'] = len(page_elements)
        
        # Step 1: Macro-level layout analysis
        logger.info("Step 1: Macro-level layout analysis")
        layout_type, region_tree = self.layout_analyzer.analyze_layout(page_elements)
        macro_ordered_blocks = self.layout_analyzer.get_macro_reading_order(region_tree)
        
        self.processing_stats['macro_blocks'] = len(macro_ordered_blocks)
        logger.info(f"Generated {len(macro_ordered_blocks)} macro blocks")
        
        # Step 2: Simple spatial sorting within each block
        logger.info("Step 2: Spatial sorting within blocks")
        final_reading_order = []
        
        for i, block in enumerate(macro_ordered_blocks):
            logger.info(f"Processing block {i+1}/{len(macro_ordered_blocks)} with {len(block)} elements")
            
            # Sort by spatial position (top-to-bottom, left-to-right)
            sorted_block = sorted(block, key=lambda e: (e.bbox.center[1], e.bbox.center[0]))
            final_reading_order.extend(sorted_block)
        
        # Final statistics
        processing_time = time.time() - start_time
        self.processing_stats['processing_time'] = processing_time
        
        logger.info("=== Reading Order Generation Complete ===")
        logger.info(f"Final order: {[elem.element_id for elem in final_reading_order]}")
        logger.info(f"Processing time: {processing_time:.2f} seconds")
        
        return final_reading_order
    
    def analyze_document_structure(self, page_elements: List[DocumentElement]) -> Dict:
        """
        Perform document structure analysis.
        
        Args:
            page_elements: All document elements on the page
            
        Returns:
            Dictionary containing analysis results
        """
        logger.info("Performing document structure analysis")
        
        # Get layout analysis
        layout_type, region_tree = self.layout_analyzer.analyze_layout(page_elements)
        macro_blocks = self.layout_analyzer.get_macro_reading_order(region_tree)
        final_order = self.generate_reading_order(page_elements)
        
        analysis = {
            'layout_analysis': {
                'layout_type': layout_type.value,
                'num_regions': self._count_regions(region_tree),
                'max_depth': self._get_max_depth(region_tree)
            },
            'reading_order': {
                'final_order': [elem.element_id for elem in final_order],
                'macro_blocks': [[elem.element_id for elem in block] for block in macro_blocks],
                'num_macro_blocks': len(macro_blocks),
                'avg_block_size': np.mean([len(block) for block in macro_blocks]) if macro_blocks else 0
            },
            'processing_stats': self.processing_stats.copy(),
            'element_details': [
                {
                    'id': elem.element_id,
                    'content_preview': elem.content[:50] + '...' if len(elem.content) > 50 else elem.content,
                    'category': elem.category,
                    'bbox': [elem.bbox.x1, elem.bbox.y1, elem.bbox.x2, elem.bbox.y2],
                    'center': elem.bbox.center
                }
                for elem in final_order
            ]
        }
        
        return analysis
    
    def _count_regions(self, region_tree: RegionNode) -> int:
        """Count total number of regions in the tree."""
        count = 1
        for child in region_tree.children:
            count += self._count_regions(child)
        return count
    
    def _get_max_depth(self, region_tree: RegionNode) -> int:
        """Get maximum depth of the region tree."""
        if not region_tree.children:
            return 1
        return 1 + max(self._get_max_depth(child) for child in region_tree.children)
    
    def export_results(self, page_elements: List[DocumentElement], 
                      output_path: str, format: str = 'json'):
        """
        Export analysis results to file.
        
        Args:
            page_elements: Document elements to analyze
            output_path: Path to save results
            format: Output format ('json' or 'txt')
        """
        analysis = self.analyze_document_structure(page_elements)
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if format.lower() == 'json':
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(analysis, f, indent=2, ensure_ascii=False)
        elif format.lower() == 'txt':
            with open(output_path, 'w', encoding='utf-8') as f:
                self._write_text_report(f, analysis)
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        logger.info(f"Results exported to {output_path}")
    
    def _write_text_report(self, file, analysis: Dict):
        """Write human-readable text report."""
        file.write("=== Simplified Reading Order Analysis Report ===\n\n")
        
        # Layout analysis
        layout = analysis['layout_analysis']
        file.write(f"Layout Type: {layout['layout_type']}\n")
        file.write(f"Number of Regions: {layout['num_regions']}\n")
        file.write(f"Maximum Depth: {layout['max_depth']}\n\n")
        
        # Reading order
        reading = analysis['reading_order']
        file.write(f"Final Reading Order: {reading['final_order']}\n")
        file.write(f"Number of Macro Blocks: {reading['num_macro_blocks']}\n")
        file.write(f"Average Block Size: {reading['avg_block_size']:.1f}\n\n")
        
        # Processing statistics
        stats = analysis['processing_stats']
        file.write(f"Processing Statistics:\n")
        file.write(f"  Total Elements: {stats['total_elements']}\n")
        file.write(f"  Macro Blocks: {stats['macro_blocks']}\n")
        file.write(f"  Processing Time: {stats['processing_time']:.2f}s\n\n")
        
        # Element details
        file.write("Element Details:\n")
        for elem in analysis['element_details']:
            file.write(f"  ID {elem['id']}: {elem['category']} - {elem['content_preview']}\n")


def create_sample_document() -> List[DocumentElement]:
    """Create a sample document for testing."""
    return [
        # Left column
        DocumentElement(1, "Corporate Governance Report", BoundingBox(50, 50, 300, 80), "title"),
        DocumentElement(2, "Executive Summary: This report outlines our governance framework and key initiatives for the fiscal year.", 
                       BoundingBox(50, 100, 300, 180), "text"),
        DocumentElement(3, "Board Structure Overview", BoundingBox(50, 200, 300, 220), "text"),
        DocumentElement(4, "Our board consists of 12 directors with diverse expertise in finance, technology, and sustainability.", 
                       BoundingBox(50, 240, 300, 320), "text"),
        
        # Right column
        DocumentElement(5, "Key Performance Indicators", BoundingBox(350, 50, 600, 80), "title"),
        DocumentElement(6, "Figure 1: Governance Metrics Dashboard", BoundingBox(350, 100, 600, 200), "image"),
        DocumentElement(7, "The above chart shows our governance performance metrics over the past fiscal year, demonstrating continuous improvement.", 
                       BoundingBox(350, 220, 600, 280), "text"),
        DocumentElement(8, "Risk Management Framework", BoundingBox(350, 300, 600, 320), "text"),
        DocumentElement(9, "Our comprehensive risk management approach includes identification, assessment, and mitigation strategies.", 
                       BoundingBox(350, 340, 600, 420), "text"),
        
        # Bottom section
        DocumentElement(10, "Table 1: Director Independence and Tenure", BoundingBox(50, 450, 600, 550), "table"),
        DocumentElement(11, "Conclusion and Future Outlook", BoundingBox(50, 570, 600, 590), "title"),
        DocumentElement(12, "Looking ahead, we remain committed to maintaining the highest standards of corporate governance while adapting to evolving regulatory requirements and stakeholder expectations.", 
                       BoundingBox(50, 610, 600, 680), "text"),
    ]


def main():
    """Main demonstration function."""
    print("=== Simplified Fused Reading Order Modeling Demo ===")
    print("Note: This version uses layout analysis with spatial sorting")
    print("For full relation modeling, install all dependencies and use demo.py")
    print()
    
    # Create sample document
    sample_elements = create_sample_document()
    
    print(f"Input: {len(sample_elements)} document elements")
    print("Element overview:")
    for elem in sample_elements:
        print(f"  ID {elem.element_id}: {elem.category:8s} - {elem.content[:40]}...")
    print()
    
    # Initialize simplified model
    print("Initializing Simplified Model...")
    model = SimplifiedFusedModel()
    print()
    
    # Generate reading order
    print("Generating reading order...")
    final_order = model.generate_reading_order(sample_elements)
    print()
    
    # Display results
    print("=== Final Reading Order ===")
    for i, elem in enumerate(final_order):
        print(f"{i+1:2d}. ID {elem.element_id}: {elem.category:8s} - {elem.content[:50]}...")
    print()
    
    # Perform analysis
    print("Performing structure analysis...")
    analysis = model.analyze_document_structure(sample_elements)
    
    print("=== Analysis Summary ===")
    print(f"Layout Type: {analysis['layout_analysis']['layout_type']}")
    print(f"Number of Regions: {analysis['layout_analysis']['num_regions']}")
    print(f"Macro Blocks: {analysis['reading_order']['num_macro_blocks']}")
    print(f"Processing Time: {analysis['processing_stats']['processing_time']:.2f}s")
    print()
    
    # Export results
    output_dir = Path("./output")
    output_dir.mkdir(exist_ok=True)
    
    model.export_results(sample_elements, output_dir / "simplified_analysis.json", "json")
    model.export_results(sample_elements, output_dir / "simplified_analysis.txt", "txt")
    
    print(f"Results exported to {output_dir}/")
    print("\n✓ Simplified demo completed successfully!")
    print("\nTo run the full demo with relation modeling:")
    print("1. Update transformers: pip install transformers -U")
    print("2. Install sentence-transformers: pip install sentence-transformers")
    print("3. Run: python demo.py")


if __name__ == "__main__":
    main()