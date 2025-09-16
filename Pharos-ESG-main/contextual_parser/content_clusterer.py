# content_clusterer.py

"""
A comprehensive tool for parsing structured Markdown files and clustering
related content blocks (images, tables, and text) under common headings.

This module provides a full pipeline that transforms an aligned Markdown file
into a final JSON file with clustered content. The process is designed to
group visual elements like images and tables with their descriptive text.

The pipeline consists of two main stages:
1.  Parsing: A `MarkdownParser` class reads a 'markdown_aligned.md' file,
    interpreting its structure of pages, headings (H1-H4), and content blocks
    (text, images, HTML tables). It has special logic to bind an image to a
    table that immediately follows it.

2.  Clustering: A `ContentClusterer` class takes the list of parsed blocks and
    groups them based on their shared heading hierarchy. It specifically looks
    for groups that contain both images and text, merging them into a single
    'cluster' block.

The final output is a single JSON file that preserves the original document
order while representing these newly formed clusters.
"""

import re
import json
import os
import logging
from pathlib import Path
import traceback
from typing import List, Dict, Optional, Tuple, Set, Any
from collections import defaultdict

# --- Setup and Configuration ---

# Configure standard logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# --- Class-based Markdown Parser ---

class MarkdownParser:
    """
    Parses a structured Markdown file into a list of content blocks.
    Maintains heading state across pages for contextual accuracy.
    """
    # Regex patterns for parsing different line types
    PAGE_PATTERN = re.compile(r'^<page_idx[：:]*\[?(\d+)>?]')
    H1_PATTERN = re.compile(r'^# (.*)')
    H2_PATTERN = re.compile(r'^## (.*)')
    H3_PATTERN = re.compile(r'^### (.*)')
    H4_PATTERN = re.compile(r'^#### (.*)')
    IMG_PATTERN = re.compile(r'^!\[\]\((.+?)\)$')
    TABLE_PATTERN = re.compile(r'^<html>.*?<table>.*?</table>.*?</html>', re.DOTALL)

    def __init__(self):
        self.h1 = self.h2 = self.h3 = self.h4 = "null"
        self.blocks = []

    def parse_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """
        Parses the entire Markdown file.

        Args:
            file_path: The Path object of the 'markdown_aligned.md' file.

        Returns:
            A list of structured content block dictionaries.
        """
        with file_path.open("r", encoding="utf-8") as f:
            lines = [line.rstrip('\n') for line in f]
        
        line_idx = 0
        while line_idx < len(lines):
            line = lines[line_idx].strip()
            page_match = self.PAGE_PATTERN.match(line)
            
            if page_match:
                page_idx = int(page_match.group(1))
                # Find the start of the page content block '['
                while line_idx < len(lines) and not lines[line_idx].strip().startswith('['):
                    line_idx += 1
                line_idx += 1  # Skip '['
                
                page_content_lines = []
                while line_idx < len(lines) and not lines[line_idx].strip().startswith(']'):
                    page_content_lines.append(lines[line_idx])
                    line_idx += 1
                
                self._process_page_content(page_content_lines, page_idx)
            line_idx += 1
            
        return self.blocks

    def _process_page_content(self, lines: List[str], page_idx: int):
        """Processes the content lines within a single page block."""
        reading_order = 0
        line_idx = 0
        while line_idx < len(lines):
            line = lines[line_idx].strip()
            if not line:
                line_idx += 1
                continue

            # Update heading state if a heading is found
            if self._update_headings(line):
                line_idx += 1
                continue

            block_data = {
                "h1": self.h1, "h2": self.h2, "h3": self.h3, "h4": self.h4,
                "page_idx": page_idx, "reading_order": reading_order
            }
            
            # Special logic for binding an image to a following table
            if self.IMG_PATTERN.match(line):
                next_line_idx, next_line = self._find_next_non_empty_line(lines, line_idx)
                if next_line and self.TABLE_PATTERN.match(next_line):
                    block_data.update({
                        "data_type": "table",
                        "table_path": line,  # The image path is used as the table identifier
                        "data": next_line
                    })
                    line_idx = next_line_idx
                else:
                    block_data.update({"data_type": "image", "data": line})
            
            elif self.TABLE_PATTERN.match(line):
                block_data.update({"data_type": "table", "data": line})
            
            else:
                block_data.update({"data_type": "text", "data": line})
            
            self.blocks.append(block_data)
            reading_order += 1
            line_idx += 1

    def _update_headings(self, line: str) -> bool:
        """Updates heading state based on the line and returns True if it was a heading."""
        if (m := self.H1_PATTERN.match(line)):
            self.h1, self.h2, self.h3, self.h4 = m.group(1), "null", "null", "null"
            return True
        if (m := self.H2_PATTERN.match(line)):
            self.h2, self.h3, self.h4 = m.group(1), "null", "null"
            return True
        if (m := self.H3_PATTERN.match(line)):
            self.h3, self.h4 = m.group(1), "null"
            return True
        if (m := self.H4_PATTERN.match(line)):
            self.h4 = m.group(1)
            return True
        return False
    
    @staticmethod
    def _find_next_non_empty_line(lines: List[str], current_idx: int) -> Tuple[int, Optional[str]]:
        """Finds the next non-empty line after a given index."""
        next_idx = current_idx + 1
        while next_idx < len(lines):
            if lines[next_idx].strip():
                return next_idx, lines[next_idx].strip()
            next_idx += 1
        return -1, None

# --- Class-based Content Clustering ---

class ContentClusterer:
    """
    Groups related content blocks from a parsed document structure.
    Specifically targets blocks with images and text under the same heading.
    """
    def __init__(self, blocks: List[Dict[str, Any]]):
        self.all_blocks = blocks
        self.block_map = {(b['page_idx'], b['reading_order']): b for b in blocks}

    def cluster_blocks(self) -> List[Dict[str, Any]]:
        """
        Executes the clustering process and returns the final ordered list of blocks.
        
        Returns:
            A list of blocks, with related items grouped into 'cluster' blocks.
        """
        # Group blocks by their full heading hierarchy
        section_groups = defaultdict(list)
        for block in self.all_blocks:
            heading_key = (block['h1'], block['h2'], block['h3'], block['h4'])
            section_groups[heading_key].append(block)

        # Identify which groups should be clustered
        clustered_groups_indices = []
        processed_block_indices = set()

        for group in section_groups.values():
            has_image = any(block['data_type'] == 'image' for block in group)
            has_text = any(block['data_type'] == 'text' for block in group)
            
            if has_image and has_text:
                group_indices = sorted([(b['page_idx'], b['reading_order']) for b in group])
                clustered_groups_indices.append(group_indices)
                processed_block_indices.update(group_indices)

        return self._reconstruct_ordered_blocks(clustered_groups_indices, processed_block_indices)

    def _reconstruct_ordered_blocks(self, clustered_groups_indices: List[List[Tuple]],
                                    processed_block_indices: Set[Tuple]) -> List[Dict[str, Any]]:
        """
        Reconstructs the full list of blocks, inserting cluster blocks in order.
        """
        ordered_blocks = []
        
        # Sort all original blocks by page and reading order
        sorted_indices = sorted(self.block_map.keys())
        
        # Sort cluster groups by their first element's appearance in the document
        sorted_clusters = sorted(clustered_groups_indices, key=lambda g: sorted_indices.index(g[0]))

        # Use a set for quick lookup of indices within any cluster
        all_clustered_indices = {idx for group in sorted_clusters for idx in group}

        cluster_iter = iter(sorted_clusters)
        current_cluster = next(cluster_iter, None)

        for index in sorted_indices:
            if index in all_clustered_indices:
                # If we encounter the first element of the next cluster, process the cluster
                if current_cluster and index == current_cluster[0]:
                    cluster_block = self._create_cluster_block(current_cluster)
                    ordered_blocks.append(cluster_block)
                    current_cluster = next(cluster_iter, None)
                # Otherwise, it's part of a cluster but not the first element, so we skip it.
            else:
                # This block is not part of any cluster, so add it as is.
                ordered_blocks.append(self.block_map[index])
                
        return ordered_blocks

    def _create_cluster_block(self, group_indices: List[Tuple]) -> Dict[str, Any]:
        """Creates a single 'cluster' block from a group of block indices."""
        first_block = self.block_map[group_indices[0]]
        
        cluster_block = {
            'data_indices': group_indices,
            'data': [self.block_map[idx]['data'] for idx in group_indices],
            'data_type': f"cluster[{','.join([self.block_map[idx]['data_type'] for idx in group_indices])}]",
            'h1': first_block['h1'],
            'h2': first_block['h2'],
            'h3': first_block['h3'],
            'h4': first_block['h4'],
            'page_idx': first_block['page_idx']
        }
        
        table_paths = [self.block_map[idx].get('table_path') for idx in group_indices if self.block_map[idx].get('table_path')]
        if table_paths:
            cluster_block['table_paths'] = table_paths
            
        return cluster_block

# --- Batch Processing ---

def batch_process_directory(base_dir: str):
    """
    Finds and processes all 'markdown_aligned.md' files in a directory.
    
    Args:
        base_dir: The root directory to search.
    """
    base_path = Path(base_dir)
    if not base_path.is_dir():
        logging.critical(f"Error: Base path is not a valid directory: {base_path}")
        return

    markdown_files = list(base_path.rglob("markdown_aligned.md"))
    logging.info(f"Found {len(markdown_files)} 'markdown_aligned.md' files to process.")
    
    success_count = 0
    total_count = len(markdown_files)

    for i, md_file in enumerate(markdown_files, 1):
        try:
            logging.info(f"\n--- [{i}/{total_count}] Processing: {md_file.relative_to(base_path)} ---")
            
            # Define output path based on parent folder name
            folder_name = md_file.parent.name
            output_path = md_file.parent / f"{folder_name}_clustering.json"
            
            if output_path.exists():
                logging.info(f"Skipping: Output file already exists at {output_path.name}")
                success_count += 1
                continue
                
            # Step 1: Parse the Markdown file
            logging.info("Step 1: Parsing Markdown file...")
            parser = MarkdownParser()
            parsed_blocks = parser.parse_file(md_file)
            logging.info(f"Parsing complete. Found {len(parsed_blocks)} content blocks.")
            
            # Step 2: Cluster the content blocks
            logging.info("Step 2: Clustering content blocks...")
            clusterer = ContentClusterer(parsed_blocks)
            clustered_blocks = clusterer.cluster_blocks()
            logging.info(f"Clustering complete. Result contains {len(clustered_blocks)} final blocks.")
            
            # Step 3: Save the final clustered JSON
            logging.info(f"Step 3: Saving output to {output_path.name}...")
            with output_path.open('w', encoding='utf-8') as f:
                json.dump(clustered_blocks, f, ensure_ascii=False, indent=2)
            
            success_count += 1
            logging.info(f"✓ Successfully processed and saved file.")

        except Exception as e:
            logging.error(f"✗ Failed to process {md_file.name}: {e}")
            logging.error(traceback.format_exc())

    logging.info(f"\n--- Batch processing complete! ---")
    logging.info(f"Successfully processed: {success_count}/{total_count} files.")


if __name__ == "__main__":
    # The base path containing subdirectories with the markdown_aligned.md files
    BASE_DIRECTORY = r"/"
    batch_process_directory(BASE_DIRECTORY)