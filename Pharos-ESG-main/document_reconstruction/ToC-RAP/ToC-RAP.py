import base64
import logging
import json
import time
import os
import sys
import io
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional

from PIL import Image
from openai import OpenAI

# ==============================================================================
# Configuration
# ==============================================================================

class Config:
    """Application configuration settings."""
    # Volcano Engine API Configuration
    API_KEY = "a7c6c504-xxxx-xxxx-xxxx-7d05a75c0301"  # Your Volcano Engine API key
    BASE_URL = "https://ark.cn-xxxxxx.volces.com/api/v3"
    MODEL_NAME = "Qwen2.5-72B-vl-instruct"

    # Image Processing
    MAX_IMAGE_SIZE_MB = 3
    COMPRESSION_QUALITY_REDUCTION = 5

    # API Call Settings
    MAX_API_RETRIES = 4
    API_TIMEOUT_SECONDS = 2
    API_MAX_TOKENS = 2048
    API_TEMPERATURE = 0.0
    API_TOP_P = 1.0

    # Parsing Constants
    FINAL_OUTPUT_MARKER = "### 最终输出结果" 

# ==============================================================================
# Logging Setup
# ==============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# ==============================================================================
# Core Logic
# ==============================================================================

# Initialize the OpenAI client for the Volcano Engine API
# It's recommended to handle the API key more securely, e.g., via environment variables.
if Config.API_KEY == "your_volcengine_api_key_here":
    logger.error("API_KEY is not configured. Please set it in the Config class.")
    sys.exit(1)

client = OpenAI(
    base_url=Config.BASE_URL,
    api_key=Config.API_KEY
)

def compress_image(
    image_path: str,
    max_size_mb: float = Config.MAX_IMAGE_SIZE_MB,
    quality_reduction: int = Config.COMPRESSION_QUALITY_REDUCTION
) -> bytes:
    """
    Compresses an image to be under a specified size limit.

    Args:
        image_path: Path to the image file.
        max_size_mb: The maximum desired file size in megabytes.
        quality_reduction: The percentage to reduce quality by in each iteration.

    Returns:
        The compressed image data as bytes.
    """
    max_size_bytes = max_size_mb * 1024 * 1024
    try:
        with Image.open(image_path) as img:
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            
            quality = 95
            output = io.BytesIO()
            
            while True:
                output.seek(0)
                output.truncate()
                img.save(output, format='JPEG', quality=quality)
                size = output.tell()
                
                if size <= max_size_bytes or quality <= 5:
                    break
                
                quality -= quality_reduction
            
            return output.getvalue()
    except IOError as e:
        logger.error(f"Error opening or processing image {image_path}: {e}")
        raise

def call_vlm_api_with_retry(
    messages: List[Dict[str, Any]],
    max_retries: int = Config.MAX_API_RETRIES,
    **kwargs
) -> Dict[str, Any]:
    """
    Calls the Vision Language Model (VLM) API with a retry mechanism.
    Handles '413 Payload Too Large' errors by compressing the image.

    Args:
        messages: A list of message dictionaries for the API call.
        max_retries: The maximum number of retry attempts.
        **kwargs: Additional parameters to pass to the API.

    Returns:
        The API response in a standardized dictionary format.

    Raises:
        Exception: If the API call fails after all retry attempts.
    """
    retry_count = 0
    last_error: Optional[Exception] = None
    
    while retry_count < max_retries:
        try:
            api_params = {
                "model": Config.MODEL_NAME,
                "messages": messages,
                "max_tokens": Config.API_MAX_TOKENS,
                "temperature": Config.API_TEMPERATURE,
                "top_p": Config.API_TOP_P,
                "n": 1
            }
            api_params.update((k, v) for k, v in kwargs.items() if k in api_params)

            completion = client.chat.completions.create(**api_params)
            logger.info("API call successful.")
            
            content = ""
            if isinstance(completion, str):
                content = completion
            elif hasattr(completion, 'choices') and completion.choices:
                content = completion.choices[0].message.content
            else:
                content = str(completion)
            
            logger.info(f"First 500 characters of response: {content[:500]}")
            
            return {"choices": [{"message": {"content": content}}]}
            
        except Exception as e:
            last_error = e
            error_message = str(e).lower()
            logger.error(f"API call failed. Error: {e}", exc_info=True)

            is_payload_error = any(sub in error_message for sub in ["413", "request entity too large", "payload too large"])
            
            if is_payload_error:
                retry_count += 1
                if retry_count >= max_retries:
                    logger.error(f"Image remains too large after {max_retries} compression attempts. Aborting.")
                    raise last_error
                
                logger.warning(
                    f"Payload too large. Attempting compression {retry_count}/{max_retries} "
                    f"(quality reduction: {Config.COMPRESSION_QUALITY_REDUCTION}%)."
                )
                
                # Find and compress the base64 image within the messages
                for message in messages:
                    if isinstance(message.get("content"), list):
                        for item in message["content"]:
                            if item.get("type") == "image_url":
                                url = item["image_url"]["url"]
                                if url.startswith("data:image/jpeg;base64,"):
                                    try:
                                        img_data = base64.b64decode(url.split(",")[1])
                                        temp_path = Path("temp_image.jpg")
                                        temp_path.write_bytes(img_data)
                                        
                                        compressed_data = compress_image(str(temp_path))
                                        encoded_string = base64.b64encode(compressed_data).decode('utf-8')
                                        item["image_url"]["url"] = f"data:image/jpeg;base64,{encoded_string}"
                                        
                                        temp_path.unlink() # Clean up temporary file
                                    except Exception as comp_e:
                                        logger.error(f"Failed to compress image during retry: {comp_e}")
                                        raise
                continue
            else:
                raise
    
    raise last_error if last_error else Exception("VLM API call failed after all retries.")

def _get_base64_from_file(file_path: Path) -> Optional[str]:
    """Reads a file and returns its base64 encoded content."""
    if not file_path.exists():
        logger.warning(f"Base64 sample file not found: {file_path}")
        return None
    try:
        return file_path.read_text(encoding='utf-8').strip()
    except Exception as e:
        logger.error(f"Error reading base64 file {file_path}: {e}")
        return None

def _build_request_messages(image_b64: str) -> List[Dict[str, Any]]:
    """
    Constructs the message payload for the VLM API call, including prompts and images.
    
    Note: The prompt text is extensive and contains specific, complex rules. It has been
    encapsulated here for clarity. For academic purposes, this prompt should be translated
    to English and included in the paper's methodology section.
    """
    script_dir = Path(__file__).parent
    
    # These prompts should be translated to English for publication.
    # The structure and rules are highly specific to the task.
    prompt_part1 = """
You are a document table of contents extraction assistant. Please identify the hierarchical
titles from the final image provided and output them.

**Strictly Prohibited**: Do not include any reasoning, explanations, comments, Markdown headers (#),
or text like "Phase One / Phase Two" in the final answer. **Only output the final list of titles**.
Before generating the final answer, you **must** sequentially execute and complete the reasoning for
the following 7 rules and state your reasoning for each. Then, state if a "chapter tag X" was found.
If not found, provide the final result. If found, explain the substitutable Y and Z with reasons.
After completing all of the above, provide the final result.

Candidate Extraction

First, fully extract all possible table of contents titles from the image. Ignore page numbers, line numbers, open dots, dashed lines, and descriptive words such as "CONTENTS"/目录, "Part 1"/上篇, and "Part 2"/下篇.

──────────────────────────────────────
Identification and Screening Rules
──────────────────────────────────────

Step 1: Identify Candidate Tags (X)

A line is considered a candidate tag X only if its length is ≤ 3 characters and it must end with "篇" (Part/Chapter), "章" (Chapter), or "部" (Section). (The stem X' refers to the tag with the suffix removed).

【Example】When a line initially classified as a Level 1 title is exactly equal to "治理篇" (Governance Part), "社会篇" (Social Part), or "环境篇" (Environment Part), it is considered a candidate tag X.

⚠️ Irrelevant Words: If "上篇" (Part 1) or "下篇" (Part 2) appear, the entire line, including any accompanying title, must be deleted immediately and must not appear in the final output.

Step 2: Search for a Replacement Title (Y) within the Visual Vicinity

Visual Vicinity is defined as:

The 10 consecutive lines below X in the same column; or

Lines appearing on the same horizontal row as X, within 40% of the page width to the right.

Y must satisfy the following conditions:

It visually appears as a Level 1 title; titles with relatively smaller fonts should be disregarded.

Text length is ≥ 3 characters.

Fuzzy Match Conditions (satisfy any one):
① X' and Y share at least 2 Chinese characters (not required to be consecutive).
② Chinese Jaccard similarity is ≥ 0.5.
③ Edit distance ÷ max(length) is ≤ 0.5.

Step 3: Replacement

If a conforming Y is found: Delete X and retain only Y as the Level 1 title (or, if required for page-wide consistency, merge them as "X' + space + Y").

If a conforming Y is not found:

Find the nearest line Z within 3 lines below X that has a length ≥ 6, and merge them into "X' + space + Z".

After merging, delete the original lines for both X and Z.

If merging/replacement fails, discard the entire line X; it must not be output as a Level 1 title.

Step 4: Deduplication

If multiple X tags point to the same Y, only keep the first occurrence.

Output Constraint:

The final output must not contain any line with a length ≤ 4 that ends in "篇/章/部". Violation is considered an error.

All steps for tag handling are triggered only when a candidate tag exists.

Step 5：Hierarchy Determination Priority

A. Independent Numbering Alignment → Titles with independent, aligned numbering are prioritized as the same level and must not be nested.

B. Unnumbered Parallel Items → Determine level sequentially by [Font Size/Weight → Color → Positional Indentation].

C. Same Font, Different Color → Within the same visual block, if spacing between titles is uniform, the title with a unique color is the higher-level title, while those with a more common color are lower-level titles.

D. Similar Color and Font → Observe the vertical spacing ΔY between adjacent lines. If ΔY is roughly uniform, they are considered the same level. If a line's ΔY is significantly greater than the spacing below it, that line is considered a new parent-level title, and all subsequent lines are demoted by one level until the next large spacing is encountered.

Graphic Block Structure Recognition Rule

If a visual module appears on the page consisting of an Arabic numeral superscript (e.g., 01, 02, 03), followed by a short tag like "××篇", and then a long title:
→ Merge these three lines into a single, complete Level 1 title with the format: "××篇 + space + Long Title".

Example: "环境篇 育绿色之苗" (Environment Part Fostering Green Shoots).

If 4–8 short sentences with smaller font and uniform color appear below this module, matching or similar to the main title's color:
→ All these lines are to be considered Level 2 titles under that Level 1 title.

All graphic block structures must be evaluated with priority over plain text areas and must not be duplicated.

Step 6：Multi-line Title Consolidation

If a single logical title is broken into multiple lines due to formatting (e.g., "Compliance Governance" on one line and "Escorting Development" on the next), they must be merged into a single sentence connected by a space during output.

Level 2 / Level 3 Title Recognition (Within the visible area of a single Level 1 title)
6.1 A line with a significantly more prominent font or color (usually bolder/darker) is considered a Level 2 title.
6.2 Several lines immediately following it, if their font/color is noticeably fainter or the font size is smaller and they share the same color, are all considered its Level 3 titles.
6.3 When another prominent line appears, a new Level 2 title group begins.

Alignment of Appendix-type Content
7.1 Identify appendix-type titles: Titles containing words like "Appendix," "Key Performance Table," "ESG Performance Table," "Indicator Index," "ESG Indicator Index," "Feedback," or "Reader Feedback."
7.2 Order Verification: This content typically belongs to the final part of a document and should be sorted according to the following standard writing convention:
• Appendix → Key Performance Table/ESG Performance Table → Indicator Index/ESG Indicator Index → Feedback/Reader Feedback
7.3 Page Number Assistance: If the table of contents includes page numbers, use their numerical order to verify and adjust the arrangement of the appendix-type content.
7.4 Order Adjustment: Before generating the final output, ensure that the appendix-type content conforms to the logical order described above, rearranging it if necessary.

───────────────────
OUTPUT FORMAT
───────────────────
### Rule-based Reasoning and Judgment
(Your reasoning for each of the 7 rules)
### X, Y, Z Discovery and Rationale
(Your analysis of chapter tags)
### Final Output
(The structured list of titles)
"""
    prompt_part2 = """
Rule C applies to this example. If you encounter a format identical to this image,
partition the output according to this expected format:
Expected Output:
Appendix
    ESG Performance Sheet
    ESG Indicator Index
    Feedback
"""
    prompt_part3 = """
Rule D applies to this example. If you encounter a format identical to this image,
use the following logic to determine hierarchy:
Observe the vertical spacing between titles. Similar spacing implies same-level hierarchy.
A significantly larger space above a title indicates it is a new parent-level title.
Expected Output:
About this Report
Chairman's Message

Responsibility and Growth
    Key Performance
    Honors and Recognition
    Progress in Supporting SDG Actions

Special Feature on Responsibility
    Fostering New Quality Productive Forces in Equipment Manufacturing Through Innovation
    Building a Leading Talent Formation for Our 'Pillar of a Great Nation' Mission

Responsibility Management
    Sustainable Development Philosophy and Governance
    Management of Material Issues
    Stakeholder Communication

Outlook
    Indicator Index
    Key Performance Table
    Reader Feedback
"""

    example1_b64 = _get_base64_from_file(script_dir / "sample2base64.txt")
    example2_b64 = _get_base64_from_file(script_dir / "sample1base64.txt")

    content_list = [{"type": "text", "text": prompt_part1}]
    
    if example2_b64:
        content_list.extend([
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{example2_b64}", "detail": "high"}},
            {"type": "text", "text": prompt_part2}
        ])
    
    if example1_b64:
        content_list.extend([
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{example1_b64}", "detail": "high"}},
            {"type": "text", "text": prompt_part3}
        ])

    content_list.append({
        "type": "image_url",
        "image_url": {"url": f"data:image/jpeg;base64,{image_b64}", "detail": "high"}
    })
    
    return [{"role": "user", "content": content_list}]

def parse_titles_from_text(content: str) -> List[Dict[str, Any]]:
    """
    Parses the structured title text from the VLM's output.

    The parser expects titles to be indented with 4 spaces for each level.
    It starts parsing after the `FINAL_OUTPUT_MARKER`.

    Args:
        content: The raw string content from the VLM API response.

    Returns:
        A list of dictionaries representing the hierarchical structure of titles.
    """
    logger.info("Parsing VLM output for structured titles.")
    
    start_index = content.find(Config.FINAL_OUTPUT_MARKER)
    if start_index == -1:
        logger.error(f"Could not find the start marker '{Config.FINAL_OUTPUT_MARKER}' in the output.")
        return []
    
    content = content[start_index + len(Config.FINAL_OUTPUT_MARKER):].strip()
    
    lines = content.splitlines()
    result: List[Dict[str, Any]] = []
    current_h1: Optional[Dict[str, Any]] = None
    current_h2: Optional[Dict[str, Any]] = None
    
    for line in lines:
        line = line.strip('\r\n')
        if not line.strip():
            continue
            
        stripped_line = line.lstrip()
        indentation = len(line) - len(stripped_line)

        if indentation == 0:  # Level 1 Title
            if current_h1:
                result.append(current_h1)
            current_h1 = {"title": stripped_line}
            current_h2 = None
        elif indentation == 4:  # Level 2 Title
            if current_h1:
                if "subtitles" not in current_h1:
                    current_h1["subtitles"] = []
                current_h2 = {"title": stripped_line}
                current_h1["subtitles"].append(current_h2)
        elif indentation >= 8:  # Level 3 Title
            if current_h2:
                if "subtitles" not in current_h2:
                    current_h2["subtitles"] = []
                current_h2["subtitles"].append(stripped_line)
    
    if current_h1:
        result.append(current_h1)
    
    return result

def extract_titles_from_image(image_path: str) -> Optional[str]:
    """
    Extracts a hierarchical list of titles from an image of a table of contents.

    Args:
        image_path: The absolute path to the image file.

    Returns:
        The path to the output JSON file if successful, otherwise None.
    """
    try:
        image_path_obj = Path(image_path).resolve()
        if not image_path_obj.exists():
            logger.error(f"Image file not found: {image_path_obj}")
            return None

        with open(image_path_obj, "rb") as img_file:
            image_b64 = base64.b64encode(img_file.read()).decode("utf-8")
            
        messages = _build_request_messages(image_b64)
        
        result = call_vlm_api_with_retry(messages=messages)
        time.sleep(Config.API_TIMEOUT_SECONDS)

        content = result["choices"][0]["message"]["content"]
        titles_list = parse_titles_from_text(content)

        output_path = image_path_obj.parent / f"{image_path_obj.stem}_titles.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(titles_list, f, ensure_ascii=False, indent=2)
            
        logger.info(f"Title extraction complete. Results saved to: {output_path}")
        return str(output_path)

    except Exception as e:
        logger.error(f"An unexpected error occurred during title extraction: {e}", exc_info=True)
        return None

# ==============================================================================
# Batch Processing
# ==============================================================================

def find_image_files(base_path: str) -> List[str]:
    """
    Recursively finds all image files in a directory, excluding folders ending in '_pages'.

    Args:
        base_path: The root directory to search.

    Returns:
        A list of absolute paths to image files.
    """
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.gif', '.webp'}
    image_files = []
    
    for root, dirs, files in os.walk(base_path):
        dirs[:] = [d for d in dirs if not d.endswith('_pages')]
        
        for file in files:
            if Path(file).suffix.lower() in image_extensions:
                image_files.append(os.path.join(root, file))
    
    return image_files

def process_all_images(base_path: str):
    """
    Processes all images found in a given base path.
    """
    logger.info(f"Starting to scan for images in: {base_path}")
    image_files = find_image_files(base_path)
    
    if not image_files:
        logger.warning("No image files found in the specified path.")
        return
    
    logger.info(f"Found {len(image_files)} image file(s) to process.")
    
    success_count = 0
    total_files = len(image_files)
    
    for i, image_path in enumerate(image_files, 1):
        logger.info(f"--- Processing file {i}/{total_files}: {image_path} ---")
        try:
            result = extract_titles_from_image(image_path)
            if result:
                success_count += 1
                logger.info(f"Successfully processed: {Path(image_path).name}")
            else:
                logger.error(f"Failed to process: {Path(image_path).name}")
        except Exception as e:
            logger.error(f"An unexpected error occurred while processing {image_path}: {e}", exc_info=True)
        
        time.sleep(1) # Rate limiting to be polite to the API
    
    logger.info("=" * 20 + " BATCH PROCESSING COMPLETE " + "=" * 20)
    logger.info(f"Successfully processed: {success_count}")
    logger.info(f"Failed to process: {total_files - success_count}")
    logger.info(f"Total files: {total_files}")

# ==============================================================================
# Main Execution
# ==============================================================================

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Extract a hierarchical Table of Contents (ToC) from images using a Vision Language Model.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    parser.add_argument(
        "path",
        nargs='?',
        default=r"/",
        help="Path to a single image file or a directory for batch processing.\n"
             "If not provided, defaults to a pre-configured directory."
    )
    
    parser.add_argument(
        "--single",
        action="store_true",
        help="Force single-file processing mode. Use this if your path is a single file."
    )

    args = parser.parse_args()
    
    base_path = Path(args.path)

    if not base_path.exists():
        logger.error(f"Error: The specified path does not exist: {base_path}")
        sys.exit(1)

    if args.single or base_path.is_file():
        if not base_path.is_file():
            logger.error(f"Error: --single mode requires a valid file path, but got a directory: {base_path}")
            sys.exit(1)
        extract_titles_from_image(str(base_path))
    else:
        process_all_images(str(base_path))

if __name__ == "__main__":
    main()