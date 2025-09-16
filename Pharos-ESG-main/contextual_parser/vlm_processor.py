# vlm_processor.py

"""
A comprehensive VLM (Vision-Language Model) processing pipeline that enriches
structured document content with AI-generated image descriptions.

This module orchestrates a multi-step process:
1.  Loads a clustered JSON file (output from the content_clusterer module).
2.  Identifies content blocks containing images or tables linked to images.
3.  For each identified block, it constructs a detailed context-aware prompt.
4.  Calls a VLM API (e.g., Qwen-VL) to analyze the images within their context,
    with robust features like API key rotation, caching, retries, and timeouts.
5.  Injects the VLM-generated descriptions back into the data structure.
6.  Un-clusters the processed blocks, regrouping all content by page number.
7.  Enriches the final output with metadata extracted from the filename and
    generates multiple cross-platform path formats for all images.

The final output is a single, page-grouped JSON file ready for downstream
analysis or presentation.
"""

import base64
from collections import defaultdict
import requests
import json
import os
import re
import time
import hashlib
import pickle
import logging
import traceback
from pathlib import Path
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from queue import Queue
from urllib.parse import quote

# --- Configuration ---

class Config:
    """Centralized configuration for the VLM pipeline."""
    # API Keys for the Vision-Language Model
    API_KEYS = [
        "sk-xxxxxx",
        "sk-xxxxxx"
        # Add more keys here if needed
    ]
    # API Endpoint Details
    API_URL = "https://api.xxxxxx.cn/v1/chat/completions"
    MODEL_NAME = "Qwen/Qwen2.5-VL-72B-Instruct"
    
    # Timeout and Retry Settings
    API_TIMEOUT_SECONDS = 60  # Timeout for a single API call
    MAX_RETRIES = 3           # Maximum retry attempts for a failed API call
    RETRY_DELAY_SECONDS = 15  # Delay between retries
    
    # Caching Configuration
    CACHE_DIR = Path("vlm_cache")
    CACHE_EXPIRE_SECONDS = 7 * 24 * 60 * 60  # Cache expires in 7 days
    
    # Hardcoded base path for calculating relative image paths in the output
    PROJECT_ROOT_PATH = "/Users/liucun/Desktop/report_analysis"
    
    # Localhost server port for generating HTTP URLs
    LOCAL_HTTP_PORT = 8000

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- VLM API Client with Caching and Key Rotation ---

class VlmApiClient:
    """
    Handles all communication with the VLM API, including caching, key rotation,
    and retry mechanisms.
    """
    def __init__(self, config: Config):
        self.config = config
        self.api_key_queue = Queue()
        for key in self.config.API_KEYS:
            self.api_key_queue.put(key)
        
        # Create cache directory if it doesn't exist
        self.config.CACHE_DIR.mkdir(exist_ok=True)

    def _get_cache_key(self, prompt: str, images_base64: List[str]) -> str:
        """Generates a unique cache key based on prompt and image content."""
        content = prompt + "".join(images_base64)
        return hashlib.md5(content.encode()).hexdigest()

    def _load_from_cache(self, cache_key: str) -> Optional[Dict]:
        """Loads a result from the cache if it's valid."""
        cache_path = self.config.CACHE_DIR / f"{cache_key}.pkl"
        if not cache_path.exists():
            return None
        try:
            with cache_path.open('rb') as f:
                cache_data = pickle.load(f)
            if time.time() - cache_data['timestamp'] < self.config.CACHE_EXPIRE_SECONDS:
                logging.info(f"Cache hit for key: {cache_key}")
                return cache_data['result']
        except Exception as e:
            logging.warning(f"Failed to load from cache: {e}")
        return None

    def _save_to_cache(self, cache_key: str, result: Dict):
        """Saves a result to the cache."""
        cache_path = self.config.CACHE_DIR / f"{cache_key}.pkl"
        cache_data = {'timestamp': time.time(), 'result': result}
        try:
            with cache_path.open('wb') as f:
                pickle.dump(cache_data, f)
        except Exception as e:
            logging.warning(f"Failed to save to cache: {e}")

    def query_vlm(self, prompt: str, image_paths: List[Path]) -> Optional[Dict]:
        """
        Queries the VLM API with given images and prompt.
        Handles API key rotation, retries, and caching.
        """
        images_base64 = [base64.b64encode(p.read_bytes()).decode('utf-8') for p in image_paths]
        cache_key = self._get_cache_key(prompt, images_base64)
        
        cached_result = self._load_from_cache(cache_key)
        if cached_result:
            return cached_result
        
        api_key = self.api_key_queue.get()
        try:
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            
            content_payload = [{"type": "text", "text": prompt}]
            for b64_string in images_base64:
                content_payload.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{b64_string}"}
                })
            
            payload = {
                "model": self.config.MODEL_NAME,
                "messages": [{"role": "user", "content": content_payload}],
                "max_tokens": 4096
            }

            for attempt in range(self.config.MAX_RETRIES):
                try:
                    response = requests.post(
                        self.config.API_URL, headers=headers, json=payload, timeout=self.config.API_TIMEOUT_SECONDS
                    )
                    response.raise_for_status()
                    result = response.json()
                    self._save_to_cache(cache_key, result)
                    return result
                except requests.RequestException as e:
                    logging.warning(f"API call attempt {attempt + 1} failed: {e}")
                    if attempt < self.config.MAX_RETRIES - 1:
                        time.sleep(self.config.RETRY_DELAY_SECONDS)
                    else:
                        logging.error("All API retries failed.")
                        return None
        finally:
            self.api_key_queue.put(api_key) # Return the key to the queue
        
        return None


# --- VLM Prompt and Content Processing ---

VLM_SYSTEM_PROMPT = """
You are an expert ESG report image analysis assistant. Your task is to identify and analyze images within a JSON content block.

**1. Input Block Types:**
- **Normal Block:** Contains a single `data` item (e.g., `"![](...)"`) and a `data_type` of "image".
- **Cluster Block:** Contains a list of `data` items (text, images, tables) and a `data_type` like "cluster[text,image,table,...]". Treat the entire cluster as one logical paragraph.

**2. Image Type Classification (Must choose one of the following seven):**
1.  **Table Image:** Data presented in a tabular format (borders, headers, cells).
2.  **Flowchart:** Shows a process, stages, or steps (often with arrows, nodes).
3.  **Statistical Chart:** Bar, line, pie, or column charts based on numerical data.
4.  **Relationship Diagram:** Displays connections or hierarchies (e.g., organizational charts).
5.  **Pure Text Image:** The entire image consists of text blocks without graphical structures.
6.  **Mixed Type:** A single image containing multiple visual elements (e.g., chart + icons + photo).
7.  **Combined Images:** Two or more separate images that must be understood together to form a complete message (e.g., one image is a legend, the other is the corresponding map). If you identify combined images, merge your analysis into a single output.

**3. Output Requirements:**
- All output must be a formal, objective, natural language paragraph suitable for a report.
- Do NOT use phrases like "This image shows," "As you can see," etc., except for statistical or mixed-type charts.
- For statistical charts, you can start with, "This is a bar chart that displays..."
- For mixed types, you can use structural descriptions: "The left side of the image shows..."
- Embed the analysis directly into the context. E.g., "...is reflected in the course curriculum provided."
- NO Markdown (`**`, `#`), special characters (`★`), or escape characters (`\\n`).
- Base all analysis strictly on visible elements and the provided text context. Do not speculate on intent, attitudes, or emotions.

**4. Output Format:**
`<Image Type> <Natural language description of the image content>`

**Example:**
`Statistical Chart This bar chart displays the distribution of employees by age group, with the largest group being 30-40 years old.`

Now, analyze the following data:
"""

class BlockProcessor:
    """
    Processes a single content block to enrich it with VLM descriptions.
    """
    def __init__(self, api_client: VlmApiClient, config: Config):
        self.api_client = api_client
        self.config = config

    def process_block(self, block: Dict, image_base_dir: Path) -> Dict:
        """
        Main method to process a block. Identifies images, calls VLM, and injects results.
        """
        if 'data' not in block: return block

        is_cluster = block.get('data_type', '').startswith('cluster')
        data_items = block['data'] if is_cluster else [block['data']]
        
        # Identify all images and their contexts
        image_groups = self._group_consecutive_images(data_items)
        
        vlm_results = {} # Store VLM results keyed by the index of the first image in a group

        for group in image_groups:
            image_indices = group['indices']
            image_markdowns = group['markdowns']
            
            image_paths = [self._construct_image_path(md, image_base_dir) for md in image_markdowns]
            valid_image_paths = [p for p in image_paths if p and p.exists()]

            if not valid_image_paths:
                logging.warning(f"Skipping group; no valid image paths found for: {image_markdowns}")
                continue

            context = self._build_context(block, data_items, image_indices)
            prompt = f"{context}\n\nCurrent Image(s):\n" + "\n".join(image_markdowns)
            
            result = self.api_client.query_vlm(prompt, valid_image_paths)
            if result and result.get('choices'):
                vlm_results[image_indices[0]] = result['choices'][0]['message']['content']

        return self._inject_vlm_results(block, vlm_results)

    def _group_consecutive_images(self, data_items: List[str]) -> List[Dict]:
        """Groups consecutive image markdown strings together."""
        groups = []
        current_group = None
        for i, item in enumerate(data_items):
            if isinstance(item, str) and item.startswith('!['):
                if current_group is None:
                    current_group = {'indices': [], 'markdowns': []}
                current_group['indices'].append(i)
                current_group['markdowns'].append(item)
            else:
                if current_group is not None:
                    groups.append(current_group)
                    current_group = None
        if current_group is not None:
            groups.append(current_group)
        return groups
    
    def _build_context(self, block: Dict, data_items: List[str], image_indices: List[int]) -> str:
        """Builds the text context surrounding a group of images."""
        context_parts = [f"{key.upper()}: {value}" for key, value in block.items() if key in ['h1', 'h2', 'h3', 'h4'] and value != "null"]
        
        # Get text immediately before and after the image group
        pre_index = image_indices[0] - 1
        post_index = image_indices[-1] + 1

        if pre_index >= 0 and not data_items[pre_index].startswith('!['):
            context_parts.append(f"Previous Text: {data_items[pre_index]}")
        if post_index < len(data_items) and not data_items[post_index].startswith('!['):
            context_parts.append(f"Following Text: {data_items[post_index]}")
            
        return "\n".join(context_parts)

    def _construct_image_path(self, markdown_str: str, image_base_dir: Path) -> Optional[Path]:
        """Extracts a valid image file path from a markdown string."""
        match = re.search(r'!\[\]\((.*?)\)', markdown_str)
        if match:
            # Use only the filename and join it with the provided base directory
            filename = Path(match.group(1)).name
            return image_base_dir / filename
        return None
        
    def _inject_vlm_results(self, block: Dict, vlm_results: Dict[int, str]) -> Dict:
        """Injects VLM descriptions back into the block data."""
        is_cluster = block.get('data_type', '').startswith('cluster')
        data_items = list(block['data']) if is_cluster else [block['data']]
        data_types = block.get('data_type', 'text').replace('cluster[','').replace(']','').split(',') if is_cluster else [block.get('data_type', 'text')]

        # A reverse mapping to handle insertions without messing up indices
        insertions = {}

        for start_index, content in vlm_results.items():
            parts = content.split(' ', 1)
            img_type = parts[0] if len(parts) > 1 else "Unknown"
            description = parts[1] if len(parts) > 1 else content
            
            # If VLM identifies combined images, replace the first image with the description
            # and mark subsequent images for removal.
            if "Combined Images" in img_type or "组合图" in img_type:
                insertions[start_index] = (description, img_type)
                # Find how many images were in this group to mark for removal
                i = start_index + 1
                while i < len(data_items) and data_items[i].startswith('!['):
                    insertions[i] = ("__REMOVE__", None)
                    i += 1
            else:
                 # For other types, just replace the single image
                 insertions[start_index] = (description, img_type)

        # Reconstruct data and data_type lists
        new_data = []
        new_data_types = []
        for i, item in enumerate(data_items):
            if i in insertions:
                description, img_type = insertions[i]
                if description == "__REMOVE__":
                    continue # Skip this item
                new_data.append(description)
                # Update the data_type to reflect it's now a VLM description
                new_data_types.append(f"vlm_description<{img_type}>")
            else:
                new_data.append(item)
                new_data_types.append(data_types[i])

        # Update the block
        if is_cluster:
            block['data'] = new_data
            block['data_type'] = f"cluster[{','.join(new_data_types)}]"
        else:
            block['data'] = new_data[0]
            block['data_type'] = new_data_types[0]
            
        return block

# --- Post-Processing and Final Formatting ---

class FinalFormatter:
    """
    Takes VLM-processed blocks, unnests clusters, groups by page, and adds
    metadata and rich path information.
    """
    def __init__(self, config: Config):
        self.config = config

    def format_final_json(self, processed_blocks: List[Dict], original_filename: str, image_base_dir: Path) -> Dict:
        """Main method to create the final structured JSON."""
        metadata = self._extract_metadata(original_filename)
        flat_blocks = self._uncluster_blocks(processed_blocks)
        
        pages_dict = defaultdict(list)
        for block in flat_blocks:
            # Each block should have these paths generated
            block_with_paths = self._add_rich_paths_to_block(block, image_base_dir, Path(original_filename).parent)
            pages_dict[block['page_idx']].append(block_with_paths)
        
        final_pages = []
        for page_idx in sorted(pages_dict.keys()):
            sorted_content = sorted(pages_dict[page_idx], key=lambda b: b['reading_order'])
            # Clean up temporary keys from content blocks
            for block in sorted_content: block.pop('page_idx', None)

            page_image_filename = f"{page_idx}.jpg"
            page_paths = self._generate_cross_platform_paths(
                image_base_dir.parent / f"{original_filename.split('_')[0]}_pages",
                page_image_filename,
                image_base_dir.parent
            )

            final_pages.append({
                "page_idx": page_idx,
                "page_paths": page_paths,
                "content": sorted_content
            })
            
        return {"metadata": metadata, "pages": final_pages}

    def _extract_metadata(self, file_path: str) -> Dict:
        """Extracts metadata like stock code and company name from the filename."""
        filename = Path(file_path).stem
        # Clean known suffixes
        for suffix in ['_vlm', '_clustering', '_grouped', '_aligned', '_descriptions']:
            filename = filename.replace(suffix, '')
        
        # Pattern: CODE-COMPANY-YEAR年度REPORT_TYPE
        match = re.match(r'([^-]+)-([^-]+)-(\d{4})年度(.+)', filename.replace('_', '-'))
        if match:
            return {
                "stock_code": match.group(1), "company_name": match.group(2),
                "report_year": int(match.group(3)), "report_type": match.group(4)
            }
        return {"original_filename": Path(file_path).name}

    def _uncluster_blocks(self, blocks: List[Dict]) -> List[Dict]:
        """Flattens cluster blocks back into individual blocks."""
        flat_blocks = []
        for block in blocks:
            if block.get('data_type', '').startswith('cluster'):
                # Deconstruct the cluster
                data_items = block['data']
                data_types = block['data_type'].replace('cluster[','').replace(']','').split(',')
                indices = block['data_indices']
                
                for i, item_data in enumerate(data_items):
                    page_idx, reading_order = indices[i]
                    new_block = block.copy()
                    new_block.update({
                        "data": item_data,
                        "data_type": data_types[i] if i < len(data_types) else 'unknown',
                        "page_idx": page_idx,
                        "reading_order": reading_order,
                    })
                    del new_block['data_indices']
                    flat_blocks.append(new_block)
            else:
                flat_blocks.append(block)
        return flat_blocks

    def _add_rich_paths_to_block(self, block: Dict, image_base_dir: Path, report_folder_path: Path) -> Dict:
        """Adds various path formats to image/table blocks."""
        markdown_url = block.get('image_markdown_url') or block.get('table_markdown_url')
        if markdown_url:
            match = re.search(r'!\[\]\((.*?)\)', markdown_url)
            if match:
                filename = Path(match.group(1)).name
                paths = self._generate_cross_platform_paths(image_base_dir, filename, report_folder_path)
                
                if block.get('image_markdown_url'): block['image_paths'] = paths
                if block.get('table_markdown_url'): block['table_paths'] = paths
        return block

    def _generate_cross_platform_paths(self, image_folder: Path, filename: str, report_folder: Path) -> Dict:
        """Generates a dictionary of useful path formats for an image."""
        full_path = image_folder / filename
        relative_to_report = Path(os.path.relpath(full_path, report_folder))
        
        return {
            "markdown": f"![]({(image_folder.name)}/{filename})",
            "file_url": full_path.as_uri(),
            "relative_path": relative_to_report.as_posix(),
            "http_url": f"http://localhost:{self.config.LOCAL_HTTP_PORT}/{quote(relative_to_report.as_posix())}"
        }

# --- Main Pipeline Manager ---

class PipelineManager:
    """
    Orchestrates the entire VLM processing and finalization pipeline.
    """
    def __init__(self, config: Config):
        self.config = config
        self.api_client = VlmApiClient(config)
        self.formatter = FinalFormatter(config)

    def run_batch(self, base_dir: str):
        """Finds and processes all relevant JSON files in a directory."""
        base_path = Path(base_dir)
        source_files = list(base_path.rglob("*_clustering.json"))
        logging.info(f"Found {len(source_files)} clustering files to process in {base_dir}.")

        for i, file_path in enumerate(source_files):
            logging.info(f"\n--- [{i+1}/{len(source_files)}] Processing file: {file_path.name} ---")
            try:
                self._process_file(file_path)
            except Exception as e:
                logging.error(f"FATAL: Unhandled exception for file {file_path.name}: {e}")
                logging.error(traceback.format_exc())
    
    def _process_file(self, json_path: Path):
        """Processes a single file through the full VLM and formatting pipeline."""
        # Define output path for the final result
        report_name = json_path.stem.replace('_clustering', '')
        output_path = json_path.parent / f"{report_name}_grouped.json"

        if output_path.exists():
            logging.info(f"Skipping: Final output file already exists: {output_path.name}")
            return
            
        # Dynamically find the corresponding image directory (_temp_images)
        image_dir_name = f"{report_name}_temp_images"
        image_base_dir = json_path.parent.parent / "md_jpg" / image_dir_name
        if not image_base_dir.is_dir():
            logging.error(f"Image directory not found for {json_path.name}. Searched at: {image_base_dir}")
            return

        with json_path.open('r', encoding='utf-8') as f:
            blocks = json.load(f)

        # Step 1: Enrich blocks with VLM descriptions
        logging.info(f"Step 1: Processing {len(blocks)} blocks with VLM...")
        block_processor = BlockProcessor(self.api_client, self.config)
        
        # Note: The original logic was misnamed as 'parallel' but ran serially.
        # This implementation maintains the safer, serial processing logic.
        enriched_blocks = [block_processor.process_block(b, image_base_dir) for b in blocks if self._block_has_image(b)]
        
        # Merge enriched blocks back into the original list
        enriched_map = {(b['page_idx'], tuple(b.get('data_indices', [(0,b.get('reading_order'))])[0])): b for b in enriched_blocks}
        final_blocks = [enriched_map.get((b['page_idx'], tuple(b.get('data_indices', [(0,b.get('reading_order'))])[0])), b) for b in blocks]
        
        # Step 2: Format the final JSON output
        logging.info("Step 2: Formatting final JSON with page grouping and metadata...")
        final_output = self.formatter.format_final_json(final_blocks, json_path.name, image_base_dir)
        
        # Step 3: Save the result
        with output_path.open('w', encoding='utf-8') as f:
            json.dump(final_output, f, ensure_ascii=False, indent=2)
        logging.info(f"✓ Successfully created final file: {output_path.name}")
        
    def _block_has_image(self, block: Dict) -> bool:
        """Checks if a block contains any images."""
        if not isinstance(block.get('data'), (list, str)): return False
        items = block['data'] if isinstance(block['data'], list) else [block['data']]
        return any(isinstance(item, str) and item.startswith("![") for item in items)


if __name__ == "__main__":
    # The base path containing subdirectories with the _clustering.json files
    BASE_DIRECTORY = r"/"
    
    # Initialize the pipeline with the configuration
    pipeline = PipelineManager(Config())
    
    # Run the batch processing
    pipeline.run_batch(BASE_DIRECTORY)