#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Advanced Layout Analysis Module for Fused Reading Order Modeling.

This module implements sophisticated layout analysis algorithms including:
1. Manhattan layout detection and classification
2. Recursive X-Y Cut algorithm for spatial decomposition
3. Projection-based region segmentation
4. Multi-scale layout understanding

Based on theoretical foundations from order theory and spatial geometry.
"""

import logging
import numpy as np
from typing import List, Dict, Tuple, Optional, Union, NamedTuple
from enum import Enum
from dataclasses import dataclass
import cv2

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LayoutType(Enum):
    """Manhattan layout types based on dominant spatial arrangement."""
    VERTICAL_MANHATTAN = "vertical_manhattan"  # Left-right dominant
    HORIZONTAL_MANHATTAN = "horizontal_manhattan"  # Top-bottom dominant
    MIXED_LAYOUT = "mixed_layout"  # Complex nested layout
    SINGLE_COLUMN = "single_column"  # Single column layout


class SplitDirection(Enum):
    """Direction for recursive splitting."""
    VERTICAL = "vertical"    # Split along x-axis (left-right)
    HORIZONTAL = "horizontal"  # Split along y-axis (top-bottom)


@dataclass
class BoundingBox:
    """Enhanced bounding box with geometric operations."""
    x1: float
    y1: float
    x2: float
    y2: float
    
    @property
    def width(self) -> float:
        return self.x2 - self.x1
    
    @property
    def height(self) -> float:
        return self.y2 - self.y1
    
    @property
    def area(self) -> float:
        return self.width * self.height
    
    @property
    def center(self) -> Tuple[float, float]:
        return ((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)
    
    def iou(self, other: 'BoundingBox') -> float:
        """Calculate Intersection over Union with another bounding box."""
        # Calculate intersection
        x1_inter = max(self.x1, other.x1)
        y1_inter = max(self.y1, other.y1)
        x2_inter = min(self.x2, other.x2)
        y2_inter = min(self.y2, other.y2)
        
        if x1_inter >= x2_inter or y1_inter >= y2_inter:
            return 0.0
        
        intersection = (x2_inter - x1_inter) * (y2_inter - y1_inter)
        union = self.area + other.area - intersection
        
        return intersection / union if union > 0 else 0.0
    
    def distance_to(self, other: 'BoundingBox') -> float:
        """Calculate normalized distance between centers."""
        cx1, cy1 = self.center
        cx2, cy2 = other.center
        return np.sqrt((cx1 - cx2) ** 2 + (cy1 - cy2) ** 2)
    
    def to_array(self) -> np.ndarray:
        """Convert to numpy array format [x1, y1, x2, y2]."""
        return np.array([self.x1, self.y1, self.x2, self.y2])


@dataclass
class DocumentElement:
    """Enhanced document element with rich metadata."""
    element_id: int
    content: str
    bbox: BoundingBox
    category: str  # 'text', 'image', 'table', 'title', 'paragraph'
    confidence: float = 1.0
    reading_order: Optional[int] = None
    parent_region: Optional[int] = None
    
    def __post_init__(self):
        """Validate element after initialization."""
        if self.bbox.width <= 0 or self.bbox.height <= 0:
            raise ValueError(f"Invalid bounding box for element {self.element_id}")


class RegionNode:
    """Node in the region hierarchy tree."""
    
    def __init__(self, 
                 region_id: int,
                 bbox: BoundingBox,
                 split_type: Optional[SplitDirection] = None,
                 elements: Optional[List[DocumentElement]] = None,
                 children: Optional[List['RegionNode']] = None):
        self.region_id = region_id
        self.bbox = bbox
        self.split_type = split_type
        self.elements = elements or []
        self.children = children or []
        self.parent: Optional['RegionNode'] = None
        
        # Set parent references for children
        for child in self.children:
            child.parent = self
    
    @property
    def is_leaf(self) -> bool:
        """Check if this is a leaf node (contains elements)."""
        return len(self.children) == 0
    
    @property
    def depth(self) -> int:
        """Calculate depth in the tree."""
        if self.parent is None:
            return 0
        return self.parent.depth + 1
    
    def add_child(self, child: 'RegionNode'):
        """Add a child node."""
        child.parent = self
        self.children.append(child)
    
    def get_all_elements(self) -> List[DocumentElement]:
        """Get all elements in this subtree."""
        if self.is_leaf:
            return self.elements.copy()
        
        all_elements = []
        for child in self.children:
            all_elements.extend(child.get_all_elements())
        return all_elements


class ProjectionAnalyzer:
    """Analyzes projection profiles for layout understanding."""
    
    def __init__(self, min_gap_ratio: float = 0.02, min_projection_ratio: float = 0.01):
        self.min_gap_ratio = min_gap_ratio
        self.min_projection_ratio = min_projection_ratio
    
    def compute_projection(self, boxes: np.ndarray, axis: int) -> np.ndarray:
        """
        Compute projection histogram along specified axis.
        
        Args:
            boxes: Array of shape [N, 4] containing bounding boxes
            axis: 0 for x-axis projection, 1 for y-axis projection
            
        Returns:
            1D projection histogram
        """
        if len(boxes) == 0:
            return np.array([])
        
        # Determine projection range
        if axis == 0:  # x-axis projection
            min_coord = int(np.min(boxes[:, 0]))
            max_coord = int(np.max(boxes[:, 2]))
            coord_pairs = boxes[:, [0, 2]]  # x1, x2 pairs
        else:  # y-axis projection
            min_coord = int(np.min(boxes[:, 1]))
            max_coord = int(np.max(boxes[:, 3]))
            coord_pairs = boxes[:, [1, 3]]  # y1, y2 pairs
        
        # Create projection histogram
        projection_length = max_coord - min_coord + 1
        projection = np.zeros(projection_length, dtype=int)
        
        for start, end in coord_pairs:
            start_idx = max(0, int(start) - min_coord)
            end_idx = min(projection_length, int(end) - min_coord)
            if start_idx < end_idx:
                projection[start_idx:end_idx] += 1
        
        return projection
    
    def find_split_points(self, projection: np.ndarray, 
                         total_length: float) -> Tuple[np.ndarray, np.ndarray]:
        """
        Find split points in projection profile.
        
        Args:
            projection: 1D projection histogram
            total_length: Total length for ratio calculations
            
        Returns:
            Tuple of (start_indices, end_indices) for valid regions
        """
        if len(projection) == 0:
            return np.array([]), np.array([])
        
        # Calculate thresholds
        min_gap = max(1, int(total_length * self.min_gap_ratio))
        min_projection = max(1, int(np.max(projection) * self.min_projection_ratio))
        
        # Find regions with sufficient projection
        valid_indices = np.where(projection >= min_projection)[0]
        
        if len(valid_indices) == 0:
            return np.array([]), np.array([])
        
        # Find gaps between regions
        gaps = valid_indices[1:] - valid_indices[:-1]
        gap_positions = np.where(gaps > min_gap)[0]
        
        # Convert to region boundaries
        region_starts = np.concatenate([[valid_indices[0]], 
                                       valid_indices[gap_positions + 1]])
        region_ends = np.concatenate([valid_indices[gap_positions], 
                                     [valid_indices[-1]]]) + 1
        
        return region_starts, region_ends


class ManhattanLayoutDetector:
    """Detects and classifies Manhattan layout patterns."""
    
    def __init__(self, aspect_ratio_threshold: float = 1.5):
        self.aspect_ratio_threshold = aspect_ratio_threshold
    
    def detect_layout_type(self, elements: List[DocumentElement]) -> LayoutType:
        """
        Detect the dominant layout type based on spatial analysis.
        
        Implements Equation (3-1) from the paper:
        Layout_type = f_spatial(E_page)
        
        Args:
            elements: List of document elements
            
        Returns:
            Detected layout type
        """
        if not elements:
            return LayoutType.SINGLE_COLUMN
        
        if len(elements) == 1:
            return LayoutType.SINGLE_COLUMN
        
        # Calculate page boundaries
        all_boxes = [elem.bbox for elem in elements]
        min_x = min(box.x1 for box in all_boxes)
        max_x = max(box.x2 for box in all_boxes)
        min_y = min(box.y1 for box in all_boxes)
        max_y = max(box.y2 for box in all_boxes)
        
        page_width = max_x - min_x
        page_height = max_y - min_y
        
        if page_width == 0 or page_height == 0:
            return LayoutType.SINGLE_COLUMN
        
        # Analyze spatial distribution
        aspect_ratio = page_width / page_height
        
        # Analyze column structure
        column_analysis = self._analyze_column_structure(elements)
        row_analysis = self._analyze_row_structure(elements)
        
        # Decision logic based on spatial characteristics
        if column_analysis['num_columns'] > 1 and column_analysis['column_confidence'] > 0.7:
            if aspect_ratio > self.aspect_ratio_threshold:
                return LayoutType.HORIZONTAL_MANHATTAN
            else:
                return LayoutType.VERTICAL_MANHATTAN
        elif row_analysis['num_rows'] > 1 and row_analysis['row_confidence'] > 0.7:
            return LayoutType.HORIZONTAL_MANHATTAN
        elif aspect_ratio > self.aspect_ratio_threshold * 2:
            return LayoutType.HORIZONTAL_MANHATTAN
        elif aspect_ratio < 1 / self.aspect_ratio_threshold:
            return LayoutType.VERTICAL_MANHATTAN
        else:
            return LayoutType.MIXED_LAYOUT
    
    def _analyze_column_structure(self, elements: List[DocumentElement]) -> Dict:
        """Analyze vertical column structure."""
        if not elements:
            return {'num_columns': 0, 'column_confidence': 0.0}
        
        # Group elements by approximate x-position
        x_centers = [elem.bbox.center[0] for elem in elements]
        x_sorted_indices = np.argsort(x_centers)
        
        # Simple clustering based on x-position gaps
        columns = []
        current_column = [x_sorted_indices[0]]
        
        for i in range(1, len(x_sorted_indices)):
            curr_idx = x_sorted_indices[i]
            prev_idx = x_sorted_indices[i-1]
            
            curr_x = x_centers[curr_idx]
            prev_x = x_centers[prev_idx]
            
            # Check if there's a significant gap
            if abs(curr_x - prev_x) > 50:  # Threshold for column separation
                columns.append(current_column)
                current_column = [curr_idx]
            else:
                current_column.append(curr_idx)
        
        columns.append(current_column)
        
        # Calculate confidence based on column balance
        column_sizes = [len(col) for col in columns]
        if len(column_sizes) <= 1:
            confidence = 0.0
        else:
            size_variance = np.var(column_sizes)
            mean_size = np.mean(column_sizes)
            confidence = max(0.0, 1.0 - (size_variance / (mean_size ** 2)))
        
        return {
            'num_columns': len(columns),
            'column_confidence': confidence,
            'columns': columns
        }
    
    def _analyze_row_structure(self, elements: List[DocumentElement]) -> Dict:
        """Analyze horizontal row structure."""
        if not elements:
            return {'num_rows': 0, 'row_confidence': 0.0}
        
        # Group elements by approximate y-position
        y_centers = [elem.bbox.center[1] for elem in elements]
        y_sorted_indices = np.argsort(y_centers)
        
        # Simple clustering based on y-position gaps
        rows = []
        current_row = [y_sorted_indices[0]]
        
        for i in range(1, len(y_sorted_indices)):
            curr_idx = y_sorted_indices[i]
            prev_idx = y_sorted_indices[i-1]
            
            curr_y = y_centers[curr_idx]
            prev_y = y_centers[prev_idx]
            
            # Check if there's a significant gap
            if abs(curr_y - prev_y) > 20:  # Threshold for row separation
                rows.append(current_row)
                current_row = [curr_idx]
            else:
                current_row.append(curr_idx)
        
        rows.append(current_row)
        
        # Calculate confidence
        row_sizes = [len(row) for row in rows]
        if len(row_sizes) <= 1:
            confidence = 0.0
        else:
            size_variance = np.var(row_sizes)
            mean_size = np.mean(row_sizes)
            confidence = max(0.0, 1.0 - (size_variance / (mean_size ** 2)))
        
        return {
            'num_rows': len(rows),
            'row_confidence': confidence,
            'rows': rows
        }


class RecursiveXYCut:
    """Implements the Recursive X-Y Cut algorithm for spatial decomposition."""
    
    def __init__(self, projection_analyzer: Optional[ProjectionAnalyzer] = None):
        self.projection_analyzer = projection_analyzer or ProjectionAnalyzer()
        self.region_counter = 0
    
    def build_region_tree(self, elements: List[DocumentElement], 
                         layout_type: LayoutType) -> RegionNode:
        """
        Build hierarchical region tree using Recursive X-Y Cut.
        
        Args:
            elements: List of document elements
            layout_type: Detected layout type
            
        Returns:
            Root node of the region tree
        """
        if not elements:
            raise ValueError("Cannot build region tree from empty element list")
        
        # Calculate bounding box for all elements
        all_boxes = [elem.bbox for elem in elements]
        min_x = min(box.x1 for box in all_boxes)
        min_y = min(box.y1 for box in all_boxes)
        max_x = max(box.x2 for box in all_boxes)
        max_y = max(box.y2 for box in all_boxes)
        
        root_bbox = BoundingBox(min_x, min_y, max_x, max_y)
        
        # Determine initial split direction based on layout type
        initial_direction = self._get_initial_split_direction(layout_type)
        
        # Reset region counter
        self.region_counter = 0
        
        # Build tree recursively
        root_node = self._recursive_split(elements, root_bbox, initial_direction)
        
        logger.info(f"Built region tree with {self.region_counter + 1} regions")
        return root_node
    
    def _get_initial_split_direction(self, layout_type: LayoutType) -> SplitDirection:
        """Determine initial split direction based on layout type."""
        if layout_type == LayoutType.VERTICAL_MANHATTAN:
            return SplitDirection.VERTICAL
        elif layout_type == LayoutType.HORIZONTAL_MANHATTAN:
            return SplitDirection.HORIZONTAL
        else:
            return SplitDirection.HORIZONTAL  # Default to horizontal
    
    def _recursive_split(self, elements: List[DocumentElement], 
                        bbox: BoundingBox, 
                        split_direction: SplitDirection) -> RegionNode:
        """
        Recursively split elements into regions.
        
        Args:
            elements: Elements to split
            bbox: Bounding box of current region
            split_direction: Direction for splitting
            
        Returns:
            Region node representing this split
        """
        current_id = self.region_counter
        self.region_counter += 1
        
        # Base case: single element or no valid split
        if len(elements) <= 1:
            return RegionNode(current_id, bbox, None, elements)
        
        # Convert elements to numpy array for projection analysis
        boxes_array = np.array([elem.bbox.to_array() for elem in elements])
        
        # Compute projection along split axis
        axis = 0 if split_direction == SplitDirection.VERTICAL else 1
        projection = self.projection_analyzer.compute_projection(boxes_array, axis)
        
        if len(projection) == 0:
            return RegionNode(current_id, bbox, None, elements)
        
        # Find split points
        total_length = bbox.width if axis == 0 else bbox.height
        region_starts, region_ends = self.projection_analyzer.find_split_points(
            projection, total_length)
        
        # If no valid splits found, create leaf node
        if len(region_starts) <= 1:
            return RegionNode(current_id, bbox, None, elements)
        
        # Create child regions
        children = []
        next_direction = (SplitDirection.HORIZONTAL 
                         if split_direction == SplitDirection.VERTICAL 
                         else SplitDirection.VERTICAL)
        
        base_coord = bbox.x1 if axis == 0 else bbox.y1
        
        for start, end in zip(region_starts, region_ends):
            # Calculate child bounding box
            if axis == 0:  # Vertical split
                child_bbox = BoundingBox(
                    base_coord + start, bbox.y1,
                    base_coord + end, bbox.y2
                )
            else:  # Horizontal split
                child_bbox = BoundingBox(
                    bbox.x1, base_coord + start,
                    bbox.x2, base_coord + end
                )
            
            # Find elements in this region
            child_elements = self._filter_elements_in_region(elements, child_bbox)
            
            if child_elements:
                child_node = self._recursive_split(child_elements, child_bbox, next_direction)
                children.append(child_node)
        
        # If no children created, return leaf node
        if not children:
            return RegionNode(current_id, bbox, None, elements)
        
        return RegionNode(current_id, bbox, split_direction, None, children)
    
    def _filter_elements_in_region(self, elements: List[DocumentElement], 
                                  region_bbox: BoundingBox) -> List[DocumentElement]:
        """Filter elements that belong to a specific region."""
        filtered_elements = []
        
        for elem in elements:
            # Check if element center is within region
            center_x, center_y = elem.bbox.center
            if (region_bbox.x1 <= center_x <= region_bbox.x2 and 
                region_bbox.y1 <= center_y <= region_bbox.y2):
                filtered_elements.append(elem)
        
        return filtered_elements


class LayoutAnalyzer:
    """Main layout analysis coordinator."""
    
    def __init__(self):
        self.layout_detector = ManhattanLayoutDetector()
        self.xy_cut = RecursiveXYCut()
        self.projection_analyzer = ProjectionAnalyzer()
    
    def analyze_layout(self, elements: List[DocumentElement]) -> Tuple[LayoutType, RegionNode]:
        """
        Perform complete layout analysis.
        
        Args:
            elements: List of document elements
            
        Returns:
            Tuple of (detected_layout_type, region_tree_root)
        """
        logger.info(f"Starting layout analysis for {len(elements)} elements")
        
        # Step 1: Detect layout type (Equation 3-1)
        layout_type = self.layout_detector.detect_layout_type(elements)
        logger.info(f"Detected layout type: {layout_type.value}")
        
        # Step 2: Build region tree using Recursive X-Y Cut
        region_tree = self.xy_cut.build_region_tree(elements, layout_type)
        
        logger.info("Layout analysis completed")
        return layout_type, region_tree
    
    def get_macro_reading_order(self, region_tree: RegionNode) -> List[List[DocumentElement]]:
        """
        Extract macro-level reading order from region tree using DFS.
        
        Implements Equation (3-2): R_page^macro = DFS(RegionTree)
        
        Args:
            region_tree: Root of the region tree
            
        Returns:
            List of element groups in macro reading order
        """
        macro_order = []
        self._dfs_traversal(region_tree, macro_order)
        
        logger.info(f"Generated macro reading order with {len(macro_order)} blocks")
        return macro_order
    
    def _dfs_traversal(self, node: RegionNode, result: List[List[DocumentElement]]):
        """Perform depth-first traversal to extract reading order."""
        if node.is_leaf:
            if node.elements:
                result.append(node.elements)
        else:
            for child in node.children:
                self._dfs_traversal(child, result)


# Example usage and testing
if __name__ == "__main__":
    # Create sample elements for testing
    sample_elements = [
        DocumentElement(1, "Left column header", BoundingBox(50, 50, 250, 80), "text"),
        DocumentElement(2, "Left column content", BoundingBox(50, 100, 250, 300), "text"),
        DocumentElement(3, "Right column header", BoundingBox(300, 50, 500, 80), "text"),
        DocumentElement(4, "Right column content", BoundingBox(300, 100, 500, 200), "text"),
        DocumentElement(5, "Right column image", BoundingBox(320, 220, 480, 320), "image"),
    ]
    
    # Initialize analyzer
    analyzer = LayoutAnalyzer()
    
    # Perform analysis
    layout_type, region_tree = analyzer.analyze_layout(sample_elements)
    macro_order = analyzer.get_macro_reading_order(region_tree)
    
    print(f"\nLayout Analysis Results:")
    print(f"Layout Type: {layout_type.value}")
    print(f"Macro Order Blocks: {len(macro_order)}")
    
    for i, block in enumerate(macro_order):
        print(f"Block {i+1}: {[elem.element_id for elem in block]}")