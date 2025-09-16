#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Complete Fused Reading Order Modeling System.

This script implements the comprehensive "coarse-to-fine" paradigm by combining:
1. Macro-rule-based skeleton ordering (layout analysis)
2. Local learning-based fine-grained ordering (relation modeling)
3. Theoretical foundations from order theory and directed acyclic relations

Based on the research paper's methodology and theoretical framework.
"""

import logging
import numpy as np
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import json
import time

# Import our modules
try:
    from .layout import (
        DocumentElement, BoundingBox, LayoutType, RegionNode,
        LayoutAnalyzer
    )
    from .relation_model import (
        MicroOrderModel, RelationType, DirectedAcyclicGraph
    )
except ImportError:
    # Fallback for standalone execution
    from layout import (
        DocumentElement, BoundingBox, LayoutType, RegionNode,
        LayoutAnalyzer
    )
    from relation_model import (
        MicroOrderModel, RelationType, DirectedAcyclicGraph
    )

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FusedReadingOrderModel:
    """
    Complete Fused Reading Order Model implementing the "coarse-to-fine" paradigm.
    
    This model combines:
    1. Macro-level spatial analysis for global structure
    2. Micro-level relationship modeling for local ordering
    3. Theoretical guarantees from order theory
    """
    
    def __init__(self, 
                 confidence_threshold: float = 0.5,
                 model_path: Optional[str] = None,
                 enable_micro_ordering: bool = True):
        """
        Initialize the Fused Reading Order Model.
        
        Args:
            confidence_threshold: Threshold for relationship confidence
            model_path: Path to pre-trained RAT model
            enable_micro_ordering: Whether to use micro-level ordering
        """
        logger.info("Initializing Fused Reading Order Model")
        
        # Initialize macro-level analyzer
        self.layout_analyzer = LayoutAnalyzer()
        
        # Initialize micro-level model
        self.enable_micro_ordering = enable_micro_ordering
        if enable_micro_ordering:
            self.micro_model = MicroOrderModel(
                confidence_threshold=confidence_threshold,
                model_path=model_path
            )
        else:
            self.micro_model = None
            logger.info("Micro-ordering disabled, using spatial fallback")
        
        self.processing_stats = {
            'total_elements': 0,
            'macro_blocks': 0,
            'micro_sorted_blocks': 0,
            'processing_time': 0.0
        }
    
    def generate_reading_order(self, 
                             page_elements: List[DocumentElement],
                             return_intermediate: bool = False) -> List[DocumentElement]:
        """
        Generate the complete fused reading order for a page.
        
        Implements the complete pipeline from Equations (3-1) to (3-7):
        1. Macro-level skeleton ordering (3-1, 3-2)
        2. Micro-level fine-grained ordering (3-3 to 3-6)
        3. Final fusion (3-7)
        
        Args:
            page_elements: All document elements on the page
            return_intermediate: Whether to return intermediate results
            
        Returns:
            List of elements in final reading order
        """
        start_time = time.time()
        
        logger.info("=== Starting Fused Reading Order Generation ===")
        logger.info(f"Processing {len(page_elements)} elements")
        
        if not page_elements:
            return []
        
        # Update statistics
        self.processing_stats['total_elements'] = len(page_elements)
        
        # Step 1: Macro-level skeleton ordering
        logger.info("Step 1: Macro-level skeleton ordering")
        layout_type, region_tree = self.layout_analyzer.analyze_layout(page_elements)
        macro_ordered_blocks = self.layout_analyzer.get_macro_reading_order(region_tree)
        
        self.processing_stats['macro_blocks'] = len(macro_ordered_blocks)
        logger.info(f"Generated {len(macro_ordered_blocks)} macro blocks")
        
        # Step 2: Micro-level fine-grained ordering
        logger.info("Step 2: Micro-level fine-grained ordering")
        final_reading_order = []
        micro_sorted_count = 0
        
        for i, block in enumerate(macro_ordered_blocks):
            logger.info(f"Processing macro block {i+1}/{len(macro_ordered_blocks)} "
                       f"with {len(block)} elements")
            
            if self.enable_micro_ordering and len(block) > 1:
                # Apply micro-level sorting
                sorted_block = self.micro_model.sort_elements(block)
                micro_sorted_count += 1
            else:
                # Fallback: spatial sorting (top-to-bottom, left-to-right)
                sorted_block = sorted(block, key=lambda e: (e.bbox.center[1], e.bbox.center[0]))
            
            final_reading_order.extend(sorted_block)
        
        self.processing_stats['micro_sorted_blocks'] = micro_sorted_count
        
        # Step 3: Final validation and statistics
        processing_time = time.time() - start_time
        self.processing_stats['processing_time'] = processing_time
        
        logger.info("=== Fused Reading Order Generation Complete ===")
        logger.info(f"Final order: {[elem.element_id for elem in final_reading_order]}")
        logger.info(f"Processing time: {processing_time:.2f} seconds")
        
        if return_intermediate:
            return {
                'final_order': final_reading_order,
                'layout_type': layout_type,
                'region_tree': region_tree,
                'macro_blocks': macro_ordered_blocks,
                'statistics': self.processing_stats.copy()
            }
        
        return final_reading_order
    
    def analyze_document_structure(self, page_elements: List[DocumentElement]) -> Dict:
        """
        Perform comprehensive document structure analysis.
        
        Args:
            page_elements: All document elements on the page
            
        Returns:
            Dictionary containing detailed analysis results
        """
        logger.info("Performing comprehensive document structure analysis")
        
        # Get complete analysis with intermediate results
        results = self.generate_reading_order(page_elements, return_intermediate=True)
        
        # Add additional analysis
        analysis = {
            'layout_analysis': {
                'layout_type': results['layout_type'].value,
                'num_regions': self._count_regions(results['region_tree']),
                'max_depth': self._get_max_depth(results['region_tree']),
                'region_tree_summary': self._summarize_region_tree(results['region_tree'])
            },
            'reading_order': {
                'final_order': [elem.element_id for elem in results['final_order']],
                'macro_blocks': [[elem.element_id for elem in block] 
                               for block in results['macro_blocks']],
                'num_macro_blocks': len(results['macro_blocks']),
                'avg_block_size': np.mean([len(block) for block in results['macro_blocks']])
            },
            'processing_stats': results['statistics'],
            'element_details': [
                {
                    'id': elem.element_id,
                    'content_preview': elem.content[:50] + '...' if len(elem.content) > 50 else elem.content,
                    'category': elem.category,
                    'bbox': [elem.bbox.x1, elem.bbox.y1, elem.bbox.x2, elem.bbox.y2],
                    'center': elem.bbox.center
                }
                for elem in results['final_order']
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
    
    def _summarize_region_tree(self, region_tree: RegionNode) -> Dict:
        """Create a summary of the region tree structure."""
        def _summarize_node(node: RegionNode) -> Dict:
            summary = {
                'region_id': node.region_id,
                'is_leaf': node.is_leaf,
                'num_elements': len(node.elements),
                'split_type': node.split_type.value if node.split_type else None,
                'bbox': [node.bbox.x1, node.bbox.y1, node.bbox.x2, node.bbox.y2]
            }
            
            if node.children:
                summary['children'] = [_summarize_node(child) for child in node.children]
            
            if node.elements:
                summary['element_ids'] = [elem.element_id for elem in node.elements]
            
            return summary
        
        return _summarize_node(region_tree)
    
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
        file.write("=== Fused Reading Order Analysis Report ===\n\n")
        
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
        
        # Macro blocks detail
        file.write("Macro Blocks Detail:\n")
        for i, block in enumerate(reading['macro_blocks']):
            file.write(f"  Block {i+1}: {block}\n")
        file.write("\n")
        
        # Processing statistics
        stats = analysis['processing_stats']
        file.write(f"Processing Statistics:\n")
        file.write(f"  Total Elements: {stats['total_elements']}\n")
        file.write(f"  Macro Blocks: {stats['macro_blocks']}\n")
        file.write(f"  Micro Sorted Blocks: {stats['micro_sorted_blocks']}\n")
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
        DocumentElement(2, "Executive Summary: This report outlines our governance framework...", 
                       BoundingBox(50, 100, 300, 180), "text"),
        DocumentElement(3, "Board Structure Overview", BoundingBox(50, 200, 300, 220), "text"),
        DocumentElement(4, "Our board consists of 12 directors with diverse expertise...", 
                       BoundingBox(50, 240, 300, 320), "text"),
        
        # Right column
        DocumentElement(5, "Key Performance Indicators", BoundingBox(350, 50, 600, 80), "title"),
        DocumentElement(6, "Figure 1: Governance Metrics", BoundingBox(350, 100, 600, 200), "image"),
        DocumentElement(7, "The above chart shows our governance performance over the past year...", 
                       BoundingBox(350, 220, 600, 260), "text"),
        DocumentElement(8, "Risk Management Framework", BoundingBox(350, 280, 600, 300), "text"),
        DocumentElement(9, "Our comprehensive risk management approach includes...", 
                       BoundingBox(350, 320, 600, 400), "text"),
        
        # Bottom section
        DocumentElement(10, "Table 1: Director Independence", BoundingBox(50, 450, 600, 550), "table"),
        DocumentElement(11, "Conclusion and Future Outlook", BoundingBox(50, 570, 600, 590), "title"),
        DocumentElement(12, "Looking ahead, we remain committed to maintaining the highest standards...", 
                       BoundingBox(50, 610, 600, 680), "text"),
    ]


def main():
    """Main demonstration function."""
    print("=== Fused Reading Order Modeling Demonstration ===")
    print()
    
    # Create sample document
    sample_elements = create_sample_document()
    
    print(f"Input: {len(sample_elements)} document elements")
    print("Element overview:")
    for elem in sample_elements:
        print(f"  ID {elem.element_id}: {elem.category} - {elem.content[:40]}...")
    print()
    
    # Initialize model
    print("Initializing Fused Reading Order Model...")
    fused_model = FusedReadingOrderModel(
        confidence_threshold=0.6,
        enable_micro_ordering=True
    )
    print()
    
    # Generate reading order
    print("Generating reading order...")
    final_order = fused_model.generate_reading_order(sample_elements)
    print()
    
    # Display results
    print("=== Final Reading Order ===")
    for i, elem in enumerate(final_order):
        print(f"{i+1:2d}. ID {elem.element_id}: {elem.category:8s} - {elem.content[:50]}...")
    print()
    
    # Perform comprehensive analysis
    print("Performing comprehensive analysis...")
    analysis = fused_model.analyze_document_structure(sample_elements)
    
    print("=== Analysis Summary ===")
    print(f"Layout Type: {analysis['layout_analysis']['layout_type']}")
    print(f"Number of Regions: {analysis['layout_analysis']['num_regions']}")
    print(f"Macro Blocks: {analysis['reading_order']['num_macro_blocks']}")
    print(f"Processing Time: {analysis['processing_stats']['processing_time']:.2f}s")
    print()
    
    # Export results
    output_dir = Path("./output")
    output_dir.mkdir(exist_ok=True)
    
    fused_model.export_results(sample_elements, output_dir / "analysis.json", "json")
    fused_model.export_results(sample_elements, output_dir / "analysis.txt", "txt")
    
    print(f"Results exported to {output_dir}/")
    print("Demonstration completed successfully!")


if __name__ == "__main__":
    main()