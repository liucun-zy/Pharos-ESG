# chinese_title_aligner.py

"""
A specialized tool for aligning and formatting titles in Chinese Markdown
documents against a canonical table of contents from a JSON file.

This script is engineered to handle the nuances of Chinese document structures.
It aligns titles from a Markdown file with a JSON-defined structure, ensuring
completeness and hierarchical correctness.

Core functionalities, optimized for Chinese text, include:
1.  Title Alignment:
    - Matches titles using exact and fuzzy string comparison, with a special
      emphasis on the Chinese character content.
    - Corrects heading levels (e.g., #, ##) in the Markdown file to match the
      canonical JSON structure.
    - Identifies titles present in the JSON but missing from the Markdown.

2.  Intelligent Insertion via LLM:
    - For missing titles, it leverages a Large Language Model (LLM) to analyze
      the surrounding Chinese content and determine the most logical insertion
      point.
    - Supports both inserting a new title and replacing a semantically
      equivalent, lower-level title (often a result of prior misalignment).

3.  Formatting and Cleanup:
    - Cleans titles by removing common Chinese prefixes (e.g., "第...章", "一、").
    - Downgrades Markdown titles that do not match any JSON entry, marking
      them as unaligned.

This script is designed for batch processing, making it suitable for large-scale
document analysis workflows.
"""

import re
import json
import os
import sys
import traceback
from pathlib import Path
from typing import List, Dict, Tuple, Any, Optional

from rapidfuzz import fuzz

# Add the current directory to the Python path to support local module imports
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Assuming 'api_client.py' contains the necessary API interaction logic
from api_client import (
    get_llm_response,
    SELECT_TITLE_SYSTEM_PROMPT,
    INSERT_POSITION_SYSTEM_PROMPT
)

# --- Constants ---
FUZZY_MATCH_THRESHOLD = 0.75
CONTAINMENT_MATCH_SIMILARITY = 0.9
UNALIGNED_TITLE_LEVEL = 4  # Level for MD titles not found in JSON (e.g., ####)
LLM_CONTENT_MAX_LENGTH = 8000  # Character limit for content sent to the LLM

# --- Text Processing Utilities ---

def _extract_chinese_chars(text: str) -> str:
    """Extracts only Chinese characters from a string."""
    return ''.join(char for char in text if '\u4e00' <= char <= '\u9fff')


def _clean_md_title(title: str) -> str:
    """
    Cleans a Markdown title by removing common numbering and section prefixes.

    This function is specifically designed to handle patterns frequently found
    in Chinese documents, such as '第...章' (Chapter), '一、' (1.), and '(一)'.

    Args:
        title: The raw title string from the Markdown file.

    Returns:
        The cleaned title string.
    """
    # Remove standard numerical and bullet-point prefixes
    cleaned = re.sub(r'^[\d\s.\-]*', '', title)
    # Remove Chinese chapter/section prefixes (e.g., "第X章/节/条/款")
    cleaned = re.sub(r'^第[\d\s]*[章节条款][\s]*', '', cleaned)
    cleaned = re.sub(r'^第[一二三四五六七八九十]+[章节条款][\s]*', '', cleaned)
    # Remove Chinese parenthesized and list-style prefixes (e.g., "(一)", "一、")
    cleaned = re.sub(r'^[（\(][一二三四五六七八九十\d][）\)][\s]*', '', cleaned)
    cleaned = re.sub(r'^[一二三四五六七八九十][\s]*[、，,][\s]*', '', cleaned)
    # Remove any remaining digits and dots, then normalize whitespace
    cleaned = re.sub(r'[\d.]+', '', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned)
    return cleaned.strip()


# --- Title Matching Logic ---

def _is_title_match(md_title: str, json_title: str) -> Tuple[bool, float, bool]:
    """
    Determines if a Markdown title matches a JSON title.

    The matching logic prioritizes:
    1. Exact match on cleaned titles or their Chinese character content.
    2. High-similarity fuzzy match.
    3. Containment of the JSON title within the Markdown title.

    Args:
        md_title: The title from the Markdown file.
        json_title: The title from the JSON file.

    Returns:
        A tuple: (is_match, similarity_score, is_exact_match).
    """
    cleaned_md_title = _clean_md_title(md_title)
    md_chinese = _extract_chinese_chars(cleaned_md_title)
    json_chinese = _extract_chinese_chars(json_title)

    # 1. Exact match (highly reliable)
    if cleaned_md_title == json_title or (md_chinese and md_chinese == json_chinese):
        return True, 1.0, True

    # 2. Fuzzy match (good for minor variations)
    similarity = fuzz.ratio(md_chinese, json_chinese) / 100.0
    if similarity >= FUZZY_MATCH_THRESHOLD:
        return True, similarity, False

    # 3. Containment match (handles cases where MD title is more descriptive)
    if json_chinese and json_chinese in md_chinese:
        return True, CONTAINMENT_MATCH_SIMILARITY, False

    return False, 0.0, False


# --- JSON and Markdown Parsing ---

def _flatten_json_titles(
    titles_json: List[Any],
    parent_title: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Flattens the nested JSON title structure into a list of title dictionaries.

    Each dictionary contains the title, its hierarchical level, and its parent.

    Args:
        titles_json: The list of titles and subtitles from the JSON file.
        parent_title: The title of the parent entry, used for recursion.

    Returns:
        A flat list of title dictionaries.
    """
    flat_list = []
    
    def _process_entry(entry: Any, level: int, parent: Optional[str]):
        if isinstance(entry, str):
            flat_list.append({"title": entry, "level": level, "parent": parent})
            return

        if isinstance(entry, dict):
            title = entry.get('title')
            if title:
                flat_list.append({"title": title, "level": level, "parent": parent})
                if 'subtitles' in entry:
                    for sub_entry in entry['subtitles']:
                        _process_entry(sub_entry, level + 1, title)

    for top_level_entry in titles_json:
        _process_entry(top_level_entry, level=1, parent=None)
        
    return flat_list


def _parse_page_blocks(md_path: str) -> List[Tuple[str, List[str]]]:
    """
    Parses a pre-grouped Markdown file into page-based content blocks.
    
    Args:
        md_path: Path to the 'grouped.md' file.

    Returns:
        A list of tuples, where each is (page_index, list_of_content_lines).
    """
    page_blocks = []
    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()

    block_pattern = re.compile(r'<page_idx:(\d+)>[\s\n]*\[(.*?)\]', re.DOTALL)
    for match in block_pattern.finditer(content):
        page_idx = match.group(1)
        # Split content into lines, removing empty ones
        block_content = [line for line in match.group(2).strip().split('\n') if line.strip()]
        page_blocks.append((page_idx, block_content))
    
    print(f"[Parser] Parsed {len(page_blocks)} page blocks from {md_path}.")
    return page_blocks


# --- Core Alignment and Insertion Logic ---

def initial_title_alignment(
    markdown_content: str,
    titles_json_path: str,
    output_md_path: str
) -> Tuple[bool, List[Dict[str, Any]]]:
    """
    Performs the initial alignment of Markdown titles against the JSON structure.

    This function matches titles, corrects heading levels, and identifies any
    titles from the JSON that are missing in the Markdown file.

    Args:
        markdown_content: The full content of the Markdown file as a string.
        titles_json_path: Path to the JSON file with the canonical title structure.
        output_md_path: Path to save the initially aligned Markdown file.

    Returns:
        A tuple: (success_status, list_of_unmatched_title_info).
    """
    try:
        with open(titles_json_path, 'r', encoding='utf-8') as f:
            titles_json_data = json.load(f)
        json_titles = _flatten_json_titles(titles_json_data)
        
        lines = markdown_content.splitlines(True)
        processed_lines = list(lines)
        heading_re = re.compile(r'^(#+)\s*(.+?)\s*$')

        md_titles = []  # (title_text, line_number, original_level)
        for i, line in enumerate(lines):
            match = heading_re.match(line)
            if match:
                md_titles.append((match.group(2).strip(), i, len(match.group(1))))
        
        matched_md_lines = set()
        unmatched_json_titles = []
        md_title_pointer = 0

        # --- Alignment Pass ---
        for json_idx, json_title_info in enumerate(json_titles):
            json_title = json_title_info["title"]
            json_level = json_title_info["level"]
            
            best_match_md_idx = -1
            best_similarity = 0.0
            
            # Search for a match from the last position onward to maintain order
            for md_idx in range(md_title_pointer, len(md_titles)):
                md_title, md_line, _ = md_titles[md_idx]
                if md_line in matched_md_lines:
                    continue

                is_match, similarity, _ = _is_title_match(md_title, json_title)
                if is_match and similarity > best_similarity:
                    best_similarity = similarity
                    best_match_md_idx = md_idx
            
            # If a suitable match is found, process it
            if best_match_md_idx != -1:
                md_title, md_line, _ = md_titles[best_match_md_idx]
                processed_lines[md_line] = f"{'#' * json_level} {md_title}\n"
                matched_md_lines.add(md_line)
                md_title_pointer = best_match_md_idx + 1
            else:
                # If no match, record it for the next processing stage
                prev_title = json_titles[json_idx - 1]["title"] if json_idx > 0 else None
                next_title = json_titles[json_idx + 1]["title"] if json_idx < len(json_titles) - 1 else None
                unmatched_json_titles.append({
                    "title": json_title,
                    "level": json_level,
                    "prev_title": prev_title,
                    "next_title": next_title,
                })
        
        # Downgrade any remaining, unaligned MD titles
        for md_title, md_line, _ in md_titles:
            if md_line not in matched_md_lines:
                processed_lines[md_line] = f"{'#' * UNALIGNED_TITLE_LEVEL} {md_title}\n"
        
        # Write the intermediate result
        output_path = Path(output_md_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.writelines(processed_lines)
            
        return True, unmatched_json_titles
    except Exception as e:
        print(f"Error during initial alignment: {e}\n{traceback.format_exc()}")
        return False, []


def process_unmatched_titles(
    aligned_md_path: str,
    unmatched_titles: List[Dict[str, Any]],
    api_key: str
) -> bool:
    """
    Processes missing titles using an LLM to find the best insertion point.

    Args:
        aligned_md_path: Path to the partially aligned Markdown file.
        unmatched_titles: A list of dictionaries for each unmatched title.
        api_key: The API key for the LLM.

    Returns:
        True if the process completes successfully.
    """
    print(f"Starting to process {len(unmatched_titles)} unmatched titles...")
    if not unmatched_titles:
        return True

    for i, title_info in enumerate(unmatched_titles):
        print(f"\n--- Processing unmatched title {i+1}/{len(unmatched_titles)}: '{title_info['title']}' ---")
        try:
            with open(aligned_md_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            heading_re = re.compile(r'^(#+)\s*(.+?)\s*$')
            md_titles_map = {i: (m.group(2).strip(), len(m.group(1)))
                             for i, line in enumerate(lines) if (m := heading_re.match(line))}

            # Find the line numbers of the preceding and succeeding titles to define a search scope
            prev_line = next((ln for ln, (t, _) in md_titles_map.items() if _is_title_match(t, title_info["prev_title"])[0]), 0) if title_info["prev_title"] else 0
            next_line = next((ln for ln, (t, _) in md_titles_map.items() if _is_title_match(t, title_info["next_title"])[0]), len(lines) - 1) if title_info["next_title"] else len(lines) - 1

            # Prepare content for the LLM
            search_content_lines = lines[prev_line : next_line + 1]
            annotated_content = [f"{prev_line + i + 1}. {'[Title]' if (prev_line + i) in md_titles_map else '[Content]'} {_clean_md_title(line.rstrip()) if (prev_line + i) in md_titles_map else line.rstrip()}"
                                 for i, line in enumerate(search_content_lines)]
            content_for_llm = "\n".join(annotated_content)
            if len(content_for_llm) > LLM_CONTENT_MAX_LENGTH:
                content_for_llm = content_for_llm[:LLM_CONTENT_MAX_LENGTH] + "\n\n[Content truncated...]"

            # Construct the prompt for the LLM
            prompt = f'''
Take a deep breath and work on this step by step.
You must determine the best position to insert a missing title into a document.

Target Title: "{title_info['title']}" (Intended Level: {title_info['level']})

Contextual Information:
- Preceding Title in Table of Contents: "{title_info['prev_title']}"
- Succeeding Title in Table of Contents: "{title_info['next_title']}"

Below is the Annotated Document Context:. Each line is prefixed with its global line number and a tag ([Title] or [Content]). All titles have been cleaned of numbering.

{content_for_llm}

[Analysis Task Background]
The target title is missing from this section. It might serve as a high-level summary for the content between the preceding and succeeding titles, or it could be a more specific content heading that was omitted.

[Analysis Step Requirements]
1.  Summarize the topics covered in the provided content.
2.  Evaluate if the section lacks a summary title that the target title could provide.
3.  Search for a specific point where inserting the title would logically connect with the surrounding text.
4.  **Special Replacement Logic**: Pay close attention to any '####' titles. These are likely unaligned titles. If you find a '####' title that is semantically equivalent to the target title, recommend replacing it.
5.  Based on your analysis, provide your final recommendation.

[Required Output Format]
Choose ONE of the following three formats for your response.

**Option 1: Insert at New Position**
Insert global line number: <line_number>
Reason: <Your detailed analysis and justification.>

**Option 2: Replace Existing Title**
Replace global line number: <line_number>
Reason: <Your detailed analysis of semantic equivalence and justification for replacement.>

**Option 3: No Suitable Position**
Insertion point: None
Reason: <Explain why no suitable insertion or replacement point exists.>

Warning: Your response MUST use "Insert global line number:" or "Replace global line number:". Any other format will be invalid.
'''
            # Call the LLM API
            response_text = get_llm_response(prompt, api_key, system_prompt=INSERT_POSITION_SYSTEM_PROMPT)
            if not response_text:
                print("API call failed. Skipping title.")
                continue

            # Process the LLM's recommendation
            if "Insertion point: None" in response_text:
                print("LLM found no suitable position. Skipping title.")
                continue

            insert_match = re.search(r'Insert global line number[:：]\s*(\d+)', response_text)
            replace_match = re.search(r'Replace global line number[:：]\s*(\d+)', response_text)
            
            line_to_modify = -1
            is_replacement = False
            
            if insert_match:
                line_to_modify = int(insert_match.group(1)) - 1
            elif replace_match:
                line_to_modify = int(replace_match.group(1)) - 1
                is_replacement = True

            if line_to_modify != -1:
                # Default to inserting at the start of the scope if the line number is invalid
                if not (prev_line <= line_to_modify <= next_line):
                    line_to_modify = prev_line
                    is_replacement = False

                if is_replacement:
                    lines[line_to_modify] = f"{'#' * title_info['level']} {title_info['title']}\n"
                else:
                    lines.insert(line_to_modify, f"{'#' * title_info['level']} {title_info['title']}\n")
            else:
                # Fallback: insert at the beginning of the scope if parsing fails
                lines.insert(prev_line, f"{'#' * title_info['level']} {title_info['title']}\n")
                
            # Save the updated file content
            with open(aligned_md_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
        except Exception as e:
            print(f"Error processing title '{title_info['title']}': {e}\n{traceback.format_exc()}")
            continue
            
    return True

# --- Batch Processing and Main Execution ---

def batch_align_titles(base_path: str, api_key: str):
    """
    Batch processes all 'grouped.md' files in a directory for title alignment.

    Args:
        base_path: The root directory containing subdirectories with 'grouped.md'.
        api_key: The API key for the LLM.
    """
    base_path = Path(base_path)
    titles_base_path = Path(r"/")
    
    print("Starting batch title alignment process...")
    grouped_files = list(base_path.rglob("grouped.md"))
    if not grouped_files:
        print("No 'grouped.md' files found to process.")
        return

    for i, grouped_file in enumerate(grouped_files, 1):
        print(f"\n--- Processing file {i}/{len(grouped_files)}: {grouped_file} ---")
        try:
            parent_dir_name = grouped_file.parent.name
            titles_json_path = titles_base_path / parent_dir_name / "titles.json"

            if not titles_json_path.exists():
                print(f" 'titles.json' not found for {parent_dir_name}. Skipping.")
                continue
            
            output_md_path = grouped_file.parent / "markdown_aligned.md"
            with open(grouped_file, 'r', encoding='utf-8') as f:
                content = f.read()

            success, unmatched_titles = initial_title_alignment(
                content, str(titles_json_path), str(output_md_path)
            )

            if success and unmatched_titles:
                process_unmatched_titles(str(output_md_path), unmatched_titles, api_key)
            
            print(f"Finished processing for {parent_dir_name}.")

        except Exception as e:
            print(f"An unexpected error occurred: {e}\n{traceback.format_exc()}")
            continue

def main():
    """Main execution function."""
    # It is recommended to use environment variables or a config file for production.
    BASE_PATH = r"/"
    API_KEY = ''  # IMPORTANT: Replace with your actual API key
    batch_align_titles(BASE_PATH, API_KEY)


if __name__ == '__main__':
    main()