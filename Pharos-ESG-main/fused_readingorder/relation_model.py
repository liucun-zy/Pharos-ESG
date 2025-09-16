#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Relation-Aware Transformer (RAT) for Fine-Grained Reading Order Modeling.

This module implements the local learning-based fine-grained ordering system:
1. Multi-modal feature construction (Equation 3-4)
2. Relation-aware Transformer for relationship prediction (Equation 3-5)
3. Directed Acyclic Graph construction and topological sorting (Equation 3-6)
4. Model downloading and management utilities

Based on theoretical foundations of Directed Acyclic Relations and Order Theory.
"""

import os
import logging
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import List, Dict, Tuple, Optional, Set
from collections import deque, defaultdict
from dataclasses import dataclass
from enum import Enum
import json
import pickle
from pathlib import Path
from transformers import AutoModel, AutoTokenizer, AutoConfig
from huggingface_hub import hf_hub_download, snapshot_download

# Import layout components
try:
    from .layout import DocumentElement, BoundingBox
except ImportError:
    # Fallback for standalone execution
    from layout import DocumentElement, BoundingBox

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RelationType(Enum):
    """Types of spatial relationships between elements."""
    FOLLOWS = "follows"  # Element j follows element i
    PRECEDES = "precedes"  # Element j precedes element i
    PARALLEL = "parallel"  # Elements are in parallel (no order)
    UNRELATED = "unrelated"  # No clear relationship


@dataclass
class RelationFeatures:
    """Multi-modal feature vector for element pair relationship."""
    content_embedding_i: np.ndarray  # E(w_i)
    content_embedding_j: np.ndarray  # E(w_j)
    delta_y: float  # Δy_ij - vertical offset
    delta_x: float  # Δx_ij - horizontal offset
    iou: float  # IoU(b_i, b_j) - bounding box intersection
    distance: float  # Dist(b_i, b_j) - normalized distance
    category_embedding_i: np.ndarray  # E(c_i)
    category_embedding_j: np.ndarray  # E(c_j)
    
    def to_vector(self) -> np.ndarray:
        """Convert to feature vector φ_ij as in Equation (3-4)."""
        return np.concatenate([
            self.content_embedding_i,
            self.content_embedding_j,
            [self.delta_y, self.delta_x, self.iou, self.distance],
            self.category_embedding_i,
            self.category_embedding_j
        ])


class ContentEncoder:
    """Encodes text content into embeddings."""
    
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.tokenizer = None
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load pre-trained sentence transformer model."""
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(self.model_name)
            logger.info(f"Loaded content encoder: {self.model_name}")
        except ImportError:
            logger.warning("sentence-transformers not available, using simple embeddings")
            self.model = None
    
    def encode(self, text: str) -> np.ndarray:
        """Encode text content to embedding vector."""
        if self.model is not None:
            return self.model.encode([text])[0]
        else:
            # Fallback: simple hash-based embedding
            hash_val = hash(text) % 1000000
            embedding = np.random.RandomState(hash_val).normal(0, 1, 384)
            return embedding / np.linalg.norm(embedding)


class CategoryEncoder:
    """Encodes element categories into embeddings."""
    
    def __init__(self):
        self.categories = ['text', 'image', 'table', 'title', 'paragraph', 'figure', 'caption']
        self.category_to_idx = {cat: idx for idx, cat in enumerate(self.categories)}
        self.embedding_dim = len(self.categories)
    
    def encode(self, category: str) -> np.ndarray:
        """Encode category as one-hot vector."""
        embedding = np.zeros(self.embedding_dim)
        if category in self.category_to_idx:
            embedding[self.category_to_idx[category]] = 1.0
        return embedding


class FeatureExtractor:
    """Extracts multi-modal features for element pairs."""
    
    def __init__(self):
        self.content_encoder = ContentEncoder()
        self.category_encoder = CategoryEncoder()
    
    def extract_features(self, elem_i: DocumentElement, 
                        elem_j: DocumentElement) -> RelationFeatures:
        """
        Extract multi-modal feature vector φ_ij for element pair (i, j).
        
        Implements Equation (3-4) from the paper:
        φ_ij = [E(w_i), E(w_j), Δy_ij, Δx_ij, IoU(b_i, b_j), Dist(b_i, b_j), E(c_i), E(c_j)]
        
        Args:
            elem_i: First element
            elem_j: Second element
            
        Returns:
            RelationFeatures object containing all feature components
        """
        # Content embeddings E(w_i), E(w_j)
        content_emb_i = self.content_encoder.encode(elem_i.content)
        content_emb_j = self.content_encoder.encode(elem_j.content)
        
        # Spatial features
        center_i = elem_i.bbox.center
        center_j = elem_j.bbox.center
        delta_y = center_j[1] - center_i[1]  # Δy_ij
        delta_x = center_j[0] - center_i[0]  # Δx_ij
        
        # Bounding box interaction features
        iou = elem_i.bbox.iou(elem_j.bbox)  # IoU(b_i, b_j)
        distance = elem_i.bbox.distance_to(elem_j.bbox)  # Dist(b_i, b_j)
        
        # Normalize distance by page dimensions
        page_diagonal = np.sqrt((elem_i.bbox.x2 - elem_i.bbox.x1) ** 2 + 
                               (elem_i.bbox.y2 - elem_i.bbox.y1) ** 2)
        if page_diagonal > 0:
            distance = distance / page_diagonal
        
        # Category embeddings E(c_i), E(c_j)
        category_emb_i = self.category_encoder.encode(elem_i.category)
        category_emb_j = self.category_encoder.encode(elem_j.category)
        
        return RelationFeatures(
            content_embedding_i=content_emb_i,
            content_embedding_j=content_emb_j,
            delta_y=delta_y,
            delta_x=delta_x,
            iou=iou,
            distance=distance,
            category_embedding_i=category_emb_i,
            category_embedding_j=category_emb_j
        )


class RelationAwareTransformer(nn.Module):
    """
    Lightweight Relation-Aware Transformer (RAT) for relationship prediction.
    
    Implements Equation (3-5): s_ij = σ(W · Transformer(φ_ij) + b)
    """
    
    def __init__(self, 
                 input_dim: int = 776,  # Default feature vector dimension
                 hidden_dim: int = 256,
                 num_heads: int = 8,
                 num_layers: int = 2,
                 dropout: float = 0.1):
        super().__init__()
        
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        
        # Input projection
        self.input_projection = nn.Linear(input_dim, hidden_dim)
        
        # Transformer encoder layers
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=hidden_dim,
            nhead=num_heads,
            dim_feedforward=hidden_dim * 4,
            dropout=dropout,
            activation='gelu',
            batch_first=True
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers)
        
        # Output projection for relationship prediction
        self.output_projection = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim // 2, 1),
            nn.Sigmoid()
        )
        
        # Initialize weights
        self._init_weights()
    
    def _init_weights(self):
        """Initialize model weights."""
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight)
                if module.bias is not None:
                    nn.init.zeros_(module.bias)
    
    def forward(self, features: torch.Tensor) -> torch.Tensor:
        """
        Forward pass through the Relation-Aware Transformer.
        
        Args:
            features: Input feature tensor of shape [batch_size, input_dim]
            
        Returns:
            Relationship confidence scores of shape [batch_size, 1]
        """
        # Project input features
        x = self.input_projection(features)  # [batch_size, hidden_dim]
        
        # Add sequence dimension for transformer
        x = x.unsqueeze(1)  # [batch_size, 1, hidden_dim]
        
        # Apply transformer
        x = self.transformer(x)  # [batch_size, 1, hidden_dim]
        
        # Remove sequence dimension
        x = x.squeeze(1)  # [batch_size, hidden_dim]
        
        # Predict relationship confidence
        output = self.output_projection(x)  # [batch_size, 1]
        
        return output.squeeze(-1)  # [batch_size]


class ModelManager:
    """Manages model downloading and loading from HuggingFace Hub."""
    
    def __init__(self, cache_dir: str = "./models"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
    
    def download_model(self, model_name: str, force_download: bool = False) -> Path:
        """
        Download model from HuggingFace Hub.
        
        Args:
            model_name: Name of the model on HuggingFace Hub
            force_download: Whether to force re-download
            
        Returns:
            Path to the downloaded model directory
        """
        model_path = self.cache_dir / model_name.replace("/", "_")
        
        if model_path.exists() and not force_download:
            logger.info(f"Model {model_name} already exists at {model_path}")
            return model_path
        
        try:
            logger.info(f"Downloading model {model_name} from HuggingFace Hub...")
            snapshot_download(
                repo_id=model_name,
                cache_dir=str(self.cache_dir),
                local_dir=str(model_path),
                local_dir_use_symlinks=False
            )
            logger.info(f"Successfully downloaded {model_name} to {model_path}")
            return model_path
        except Exception as e:
            logger.error(f"Failed to download model {model_name}: {e}")
            raise
    
    def load_pretrained_rat(self, model_path: Optional[str] = None) -> RelationAwareTransformer:
        """
        Load pre-trained RAT model or create new one.
        
        Args:
            model_path: Path to pre-trained model, if None creates new model
            
        Returns:
            RelationAwareTransformer instance
        """
        if model_path and Path(model_path).exists():
            try:
                model = RelationAwareTransformer()
                model.load_state_dict(torch.load(model_path, map_location='cpu'))
                logger.info(f"Loaded pre-trained RAT model from {model_path}")
                return model
            except Exception as e:
                logger.warning(f"Failed to load model from {model_path}: {e}")
        
        # Create new model with default parameters
        logger.info("Creating new RAT model with default parameters")
        return RelationAwareTransformer()


class DirectedAcyclicGraph:
    """
    Directed Acyclic Graph for representing element relationships.
    
    Based on theoretical foundations from Definition 1 (Directed Acyclic Relation).
    """
    
    def __init__(self, elements: List[DocumentElement]):
        self.elements = elements
        self.element_map = {elem.element_id: elem for elem in elements}
        self.adjacency_list: Dict[int, List[int]] = defaultdict(list)
        self.edge_weights: Dict[Tuple[int, int], float] = {}
    
    def add_edge(self, from_id: int, to_id: int, weight: float):
        """Add directed edge with confidence weight."""
        if from_id != to_id:  # Prevent self-loops
            self.adjacency_list[from_id].append(to_id)
            self.edge_weights[(from_id, to_id)] = weight
    
    def has_cycle(self) -> bool:
        """
        Check if the graph contains cycles.
        
        Returns:
            True if cycle exists, False otherwise
        """
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {node_id: WHITE for node_id in self.element_map.keys()}
        
        def dfs_visit(node_id: int) -> bool:
            if color[node_id] == GRAY:
                return True  # Back edge found, cycle detected
            if color[node_id] == BLACK:
                return False  # Already processed
            
            color[node_id] = GRAY
            for neighbor in self.adjacency_list[node_id]:
                if dfs_visit(neighbor):
                    return True
            color[node_id] = BLACK
            return False
        
        for node_id in self.element_map.keys():
            if color[node_id] == WHITE:
                if dfs_visit(node_id):
                    return True
        return False
    
    def topological_sort(self) -> Optional[List[int]]:
        """
        Perform topological sorting using Kahn's algorithm.
        
        Implements Equation (3-6): R_r^micro = TopoSort(G_r)
        
        Returns:
            List of element IDs in topological order, or None if cycle exists
        """
        # Calculate in-degrees
        in_degree = {node_id: 0 for node_id in self.element_map.keys()}
        for node_id in self.adjacency_list:
            for neighbor in self.adjacency_list[node_id]:
                in_degree[neighbor] += 1
        
        # Initialize queue with nodes having zero in-degree
        queue = deque([node_id for node_id, degree in in_degree.items() if degree == 0])
        topo_order = []
        
        while queue:
            current = queue.popleft()
            topo_order.append(current)
            
            # Reduce in-degree of neighbors
            for neighbor in self.adjacency_list[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        # Check if all nodes are included (no cycle)
        if len(topo_order) == len(self.element_map):
            return topo_order
        else:
            logger.warning("Cycle detected in graph, topological sort failed")
            return None
    
    def get_transitive_closure(self) -> 'DirectedAcyclicGraph':
        """
        Compute transitive closure of the DAR.
        
        Based on Theorem 2: The transitive closure of a DAR is a SPO.
        
        Returns:
            New DAG representing the transitive closure
        """
        closure = DirectedAcyclicGraph(self.elements)
        
        # Floyd-Warshall algorithm for transitive closure
        nodes = list(self.element_map.keys())
        n = len(nodes)
        node_to_idx = {node: i for i, node in enumerate(nodes)}
        
        # Initialize reachability matrix
        reach = [[False] * n for _ in range(n)]
        
        # Set direct edges
        for i in range(n):
            reach[i][i] = True  # Self-reachable
            node_id = nodes[i]
            for neighbor in self.adjacency_list[node_id]:
                j = node_to_idx[neighbor]
                reach[i][j] = True
        
        # Compute transitive closure
        for k in range(n):
            for i in range(n):
                for j in range(n):
                    reach[i][j] = reach[i][j] or (reach[i][k] and reach[k][j])
        
        # Add edges to closure graph
        for i in range(n):
            for j in range(n):
                if i != j and reach[i][j]:
                    from_id = nodes[i]
                    to_id = nodes[j]
                    # Use minimum weight along path as closure weight
                    weight = self._get_path_weight(from_id, to_id)
                    closure.add_edge(from_id, to_id, weight)
        
        return closure
    
    def _get_path_weight(self, from_id: int, to_id: int) -> float:
        """Get minimum weight along path from from_id to to_id."""
        if (from_id, to_id) in self.edge_weights:
            return self.edge_weights[(from_id, to_id)]
        
        # BFS to find path with minimum weight
        queue = deque([(from_id, 1.0)])
        visited = {from_id}
        
        while queue:
            current, weight = queue.popleft()
            
            for neighbor in self.adjacency_list[current]:
                if neighbor == to_id:
                    edge_weight = self.edge_weights.get((current, neighbor), 0.5)
                    return min(weight, edge_weight)
                
                if neighbor not in visited:
                    visited.add(neighbor)
                    edge_weight = self.edge_weights.get((current, neighbor), 0.5)
                    queue.append((neighbor, min(weight, edge_weight)))
        
        return 0.5  # Default weight if no path found


class MicroOrderModel:
    """
    Local learning-based fine-grained ordering model.
    
    Implements the complete micro-order pipeline from Equations (3-3) to (3-6).
    """
    
    def __init__(self, 
                 confidence_threshold: float = 0.5,
                 model_path: Optional[str] = None):
        self.confidence_threshold = confidence_threshold
        self.feature_extractor = FeatureExtractor()
        self.model_manager = ModelManager()
        
        # Load or create RAT model
        self.rat_model = self.model_manager.load_pretrained_rat(model_path)
        self.rat_model.eval()
        
        logger.info(f"Initialized MicroOrderModel with threshold {confidence_threshold}")
    
    def predict_relationships(self, elements: List[DocumentElement]) -> Dict[Tuple[int, int], float]:
        """
        Predict pairwise relationships between elements.
        
        Implements Equation (3-5): s_ij = σ(W · Transformer(φ_ij) + b)
        
        Args:
            elements: List of document elements in a region
            
        Returns:
            Dictionary mapping (i, j) pairs to confidence scores
        """
        if len(elements) <= 1:
            return {}
        
        relationships = {}
        feature_vectors = []
        element_pairs = []
        
        # Extract features for all pairs
        for i, elem_i in enumerate(elements):
            for j, elem_j in enumerate(elements):
                if i != j:
                    features = self.feature_extractor.extract_features(elem_i, elem_j)
                    feature_vectors.append(features.to_vector())
                    element_pairs.append((elem_i.element_id, elem_j.element_id))
        
        if not feature_vectors:
            return relationships
        
        # Convert to tensor and predict
        features_tensor = torch.FloatTensor(np.array(feature_vectors))
        
        with torch.no_grad():
            predictions = self.rat_model(features_tensor)
            predictions = predictions.cpu().numpy()
        
        # Map predictions back to element pairs
        for (elem_i_id, elem_j_id), score in zip(element_pairs, predictions):
            relationships[(elem_i_id, elem_j_id)] = float(score)
        
        return relationships
    
    def build_relation_graph(self, elements: List[DocumentElement], 
                           relationships: Dict[Tuple[int, int], float]) -> DirectedAcyclicGraph:
        """
        Build directed acyclic graph from relationship predictions.
        
        Args:
            elements: List of document elements
            relationships: Predicted relationship scores
            
        Returns:
            DirectedAcyclicGraph representing element relationships
        """
        graph = DirectedAcyclicGraph(elements)
        
        # Add edges based on confidence threshold
        for (from_id, to_id), confidence in relationships.items():
            if confidence > self.confidence_threshold:
                graph.add_edge(from_id, to_id, confidence)
        
        # Check for cycles and remove problematic edges if necessary
        if graph.has_cycle():
            logger.warning("Cycle detected in relation graph, removing low-confidence edges")
            graph = self._resolve_cycles(graph, relationships)
        
        return graph
    
    def _resolve_cycles(self, graph: DirectedAcyclicGraph, 
                       relationships: Dict[Tuple[int, int], float]) -> DirectedAcyclicGraph:
        """Resolve cycles by removing lowest confidence edges."""
        # Sort edges by confidence (ascending)
        sorted_edges = sorted(relationships.items(), key=lambda x: x[1])
        
        # Rebuild graph by adding edges in order of confidence
        clean_graph = DirectedAcyclicGraph(graph.elements)
        
        for (from_id, to_id), confidence in reversed(sorted_edges):
            if confidence > self.confidence_threshold:
                # Temporarily add edge and check for cycles
                clean_graph.add_edge(from_id, to_id, confidence)
                if clean_graph.has_cycle():
                    # Remove the edge that caused the cycle
                    clean_graph.adjacency_list[from_id].remove(to_id)
                    del clean_graph.edge_weights[(from_id, to_id)]
        
        return clean_graph
    
    def sort_elements(self, elements: List[DocumentElement]) -> List[DocumentElement]:
        """
        Sort elements within a region using fine-grained relationship modeling.
        
        Implements the complete pipeline from Equations (3-3) to (3-6):
        1. Extract multi-modal features (3-4)
        2. Predict relationships (3-5)
        3. Build graph and perform topological sort (3-6)
        
        Args:
            elements: List of document elements in a region
            
        Returns:
            Sorted list of elements in reading order
        """
        if len(elements) <= 1:
            return elements
        
        logger.info(f"Sorting {len(elements)} elements using micro-order model")
        
        # Step 1: Predict pairwise relationships
        relationships = self.predict_relationships(elements)
        
        # Step 2: Build relation graph
        relation_graph = self.build_relation_graph(elements, relationships)
        
        # Step 3: Perform topological sort
        sorted_ids = relation_graph.topological_sort()
        
        if sorted_ids is not None:
            # Map back to elements
            id_to_element = {elem.element_id: elem for elem in elements}
            sorted_elements = [id_to_element[elem_id] for elem_id in sorted_ids]
            logger.info(f"Successfully sorted elements: {[e.element_id for e in sorted_elements]}")
            return sorted_elements
        else:
            # Fallback: sort by spatial position (top-to-bottom, left-to-right)
            logger.warning("Topological sort failed, using spatial fallback")
            return sorted(elements, key=lambda e: (e.bbox.center[1], e.bbox.center[0]))


# Example usage and testing
if __name__ == "__main__":
    # Create sample elements for testing
    sample_elements = [
        DocumentElement(1, "Introduction paragraph", BoundingBox(50, 100, 250, 150), "text"),
        DocumentElement(2, "Figure 1: Overview", BoundingBox(50, 160, 250, 260), "image"),
        DocumentElement(3, "Figure caption", BoundingBox(50, 270, 250, 290), "text"),
        DocumentElement(4, "Analysis section", BoundingBox(50, 300, 250, 400), "text"),
    ]
    
    # Initialize micro-order model
    micro_model = MicroOrderModel(confidence_threshold=0.6)
    
    # Sort elements
    sorted_elements = micro_model.sort_elements(sample_elements)
    
    print("\nMicro-Order Results:")
    for i, elem in enumerate(sorted_elements):
        print(f"{i+1}. ID {elem.element_id}: '{elem.content}' ({elem.category})")