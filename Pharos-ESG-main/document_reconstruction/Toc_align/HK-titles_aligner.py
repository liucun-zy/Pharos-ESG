# traditional_chinese_title_aligner.py

"""
A specialized tool for aligning titles in Traditional Chinese Markdown documents.

This script is engineered to handle the nuances of Traditional Chinese document
structures, including character sets and section numbering. It aligns titles
from a Markdown file with a JSON-defined table of contents, ensuring
hierarchical correctness and completeness.

Key features include:
1.  Traditional Chinese Normalization: Uses the OpenCC library to convert
    all titles to Traditional Chinese before comparison, ensuring consistency.
2.  Advanced Title Cleaning: Employs regular expressions tailored for both
    Simplified and Traditional Chinese numbering systems and section markers
    (e.g., '第...章', '壹、', '條').
3.  LLM-Powered Insertion: For titles missing from the document, it leverages
    a Large Language Model to determine the most logical insertion point.
4.  Comprehensive Token Logging: Includes a detailed logger to track API
    token consumption, processing statistics, and success rates, which is
    crucial for cost management and performance analysis.
"""

import re
import json
import os
import sys
import datetime
import logging
import traceback
from pathlib import Path
from typing import List, Dict, Tuple, Any, Optional

from rapidfuzz import fuzz

# --- Setup and Initialization ---

# Configure standard logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Attempt to import and initialize OpenCC for Chinese character conversion
try:
    from opencc import OpenCC
    # s2t: Simplified to Traditional Chinese
    OPENCC_CONVERTER = OpenCC('s2t')
    logging.info("OpenCC loaded successfully for Simplified to Traditional Chinese conversion.")
except ImportError:
    OPENCC_CONVERTER = None
    logging.warning("OpenCC library not found. Traditional Chinese conversion will be skipped.")

# Add local directory to path for module imports
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Import the API client. Assumes get_llm_response returns (response, in_tokens, out_tokens)
try:
    from api_client import get_llm_response
except ImportError:
    logging.error("Could not import 'get_llm_response' from api_client. Please ensure the file exists.")
    sys.exit(1)

# --- Constants ---
FUZZY_MATCH_THRESHOLD = 0.75
CONTAINMENT_MATCH_SIMILARITY = 0.9
UNALIGNED_TITLE_LEVEL = 4  # Markdown level for unaligned titles (e.g., ####)

# --- Token Usage and Statistics Logger ---

class ApiMetricsLogger:
    """
    Logs API token usage and processing statistics to a file.
    """
    def __init__(self, log_file="token_usage.txt"):
        self.log_file = Path(log_file)
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.file_count = 0
        self.current_file = ""
        self.current_file_input_tokens = 0
        self.current_file_output_tokens = 0
        self.successful_insertions = 0
        self.failed_insertions = 0
        self.total_unmatched_titles = 0
        
        # Initialize the log file
        with self.log_file.open("w", encoding="utf-8") as f:
            f.write(f"Processing Started: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n")
            f.write("Detailed API Call Log:\n")
            f.write("Type,File,InputTokens,OutputTokens,TotalTokens,Status,TargetTitle\n")

    def start_file_processing(self, file_name: str):
        """Logs the start of processing for a new file."""
        if self.current_file:
            self._log_file_summary()
        
        self.current_file = file_name
        self.file_count += 1
        self.current_file_input_tokens = 0
        self.current_file_output_tokens = 0
        
        with self.log_file.open("a", encoding="utf-8") as f:
            f.write(f"\n{'='*80}\n")
            f.write(f"Processing File {self.file_count}: {file_name}\n")
            f.write(f"Start Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"{'='*80}\n")

    def log_api_call(self, input_tokens: int, output_tokens: int, description: str,
                     status: str = "N/A", target_title: str = ""):
        """Logs a single API call's token usage."""
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.current_file_input_tokens += input_tokens
        self.current_file_output_tokens += output_tokens
        
        with self.log_file.open("a", encoding="utf-8") as f:
            f.write(
                f'"{description}","{self.current_file}",{input_tokens},{output_tokens},'
                f'{input_tokens + output_tokens},"{status}","{target_title}"\n'
            )
        self._update_realtime_summary()

    def log_insertion_result(self, title: str, success: bool, reason: str = ""):
        """Logs the outcome of a title insertion attempt."""
        if success:
            self.successful_insertions += 1
        else:
            self.failed_insertions += 1
        logging.info(f"Insertion result for '{title}': {'Success' if success else 'Failure'}. Reason: {reason}")
    
    def set_unmatched_titles_count(self, count: int):
        """Sets the number of unmatched titles for the current file."""
        self.total_unmatched_titles += count
        with self.log_file.open("a", encoding="utf-8") as f:
            f.write(f"Unmatched titles in this file: {count}\n")

    def _log_file_summary(self):
        """Appends a summary for the currently processed file to the log."""
        with self.log_file.open("a", encoding="utf-8") as f:
            f.write(f"\nSummary for '{self.current_file}':\n")
            f.write(f"  - Input Tokens: {self.current_file_input_tokens}\n")
            f.write(f"  - Output Tokens: {self.current_file_output_tokens}\n")
            f.write(f"  - Total Tokens: {self.current_file_input_tokens + self.current_file_output_tokens}\n")
            f.write(f"  - Completion Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    def _update_realtime_summary(self):
        """
        Updates a real-time summary section at the end of the log file.

        Note: This method involves reading and rewriting the entire log file
        on each API call, which can be I/O intensive for very large batches.
        A more performant alternative would be to log summaries only at the
        end of each file or the entire batch process.
        """
        try:
            content = self.log_file.read_text(encoding="utf-8")
            
            summary_marker = "\n[Real-time Summary]"
            if summary_marker in content:
                content = content.split(summary_marker)[0]
            
            summary = (
                f"{summary_marker} - Last Updated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"Files Processed: {self.file_count}\n"
                f"Total Input Tokens: {self.total_input_tokens}\n"
                f"Total Output Tokens: {self.total_output_tokens}\n"
                f"Total Token Consumption: {self.total_input_tokens + self.total_output_tokens}\n"
                f"Successful Insertions: {self.successful_insertions}\n"
                f"Failed Insertions: {self.failed_insertions}\n"
            )
            
            self.log_file.write_text(content + summary, encoding="utf-8")
        except Exception as e:
            logging.error(f"Failed to update real-time summary: {e}")

    def finalize_log(self):
        """Writes the final summary for the entire batch process."""
        if self.current_file:
            self._log_file_summary()
        
        with self.log_file.open("a", encoding="utf-8") as f:
            f.write(f"\n{'='*80}\n")
            f.write("Final Batch Processing Summary\n")
            f.write(f"{'='*80}\n")
            f.write(f"Completion Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Files Processed: {self.file_count}\n")
            f.write(f"Total Input Tokens: {self.total_input_tokens}\n")
            f.write(f"Total Output Tokens: {self.total_output_tokens}\n")
            f.write(f"Total Token Consumption: {self.total_input_tokens + self.total_output_tokens}\n")
            f.write(f"Total Unmatched Titles Found: {self.total_unmatched_titles}\n")
            f.write(f"Successful Insertions: {self.successful_insertions}\n")
            f.write(f"Failed Insertions: {self.failed_insertions}\n")
            total_insertions = self.successful_insertions + self.failed_insertions
            if total_insertions > 0:
                success_rate = (self.successful_insertions / total_insertions) * 100
                f.write(f"Insertion Success Rate: {success_rate:.1f}%\n")
            f.write(f"{'='*80}\n")
        logging.info(f"Final summary logged to {self.log_file}")

# --- Text Processing and Normalization ---

def _to_traditional(text: str) -> str:
    """Converts a string to Traditional Chinese if OpenCC is available."""
    if OPENCC_CONVERTER:
        return OPENCC_CONVERTER.convert(text)
    return text

def _clean_md_title(title: str) -> str:
    """
    Cleans a Markdown title by removing numbering prefixes.
    Handles both Simplified and Traditional Chinese markers.
    """
    # Remove standard numerical prefixes
    cleaned = re.sub(r'^[\d\s.\-]*', '', title)
    # Remove Chinese section markers (Simplified/Traditional)
    cleaned = re.sub(r'^第[\d\s]*[章节節條款目項][\s]*', '', cleaned)
    cleaned = re.sub(r'^第[一二三四五六七八九十壹貳參肆伍陸柒捌玖拾百千萬亿]+[章节節條款目項][\s]*', '', cleaned)
    # Remove parenthesized and list-style markers
    cleaned = re.sub(r'^[（\(\[]([\d一二三四五六七八九十壹貳參肆伍陸柒捌玖拾])[）\)\]][\s]*', '', cleaned)
    cleaned = re.sub(r'^[一二三四五六七八九十壹貳參肆伍陸柒捌玖拾][、，,][\s]*', '', cleaned)
    # Final cleanup
    cleaned = re.sub(r'[\d.]+', '', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

def _normalize_for_matching(title: str) -> str:
    """
    Normalizes a title for robust matching.
    
    Actions:
    1. Keeps only Chinese, English, and numeric characters.
    2. Converts the string to Traditional Chinese.
    3. Removes all whitespace.
    """
    # Keep only relevant characters
    text = ''.join(char for char in title if (
        '\u4e00' <= char <= '\u9fff' or 'a' <= char.lower() <= 'z' or char.isdigit()
    ))
    # Unify to Traditional Chinese
    text = _to_traditional(text)
    # Remove whitespace
    return re.sub(r'\s+', '', text)

# --- Core Logic Functions ---
# Note: The following functions have been streamlined and unused ones removed.
# Refer to previous refactoring explanations for details on the consolidation.

def _is_title_match(md_title: str, json_title: str) -> Tuple[bool, float]:
    """Determines if two titles match after normalization."""
    norm_md = _normalize_for_matching(_clean_md_title(md_title))
    norm_json = _normalize_for_matching(_clean_md_title(json_title))

    if norm_md == norm_json:
        return True, 1.0
    
    similarity = fuzz.ratio(norm_md, norm_json) / 100.0
    if similarity >= FUZZY_MATCH_THRESHOLD:
        return True, similarity
        
    if norm_json in norm_md:
        return True, CONTAINMENT_MATCH_SIMILARITY
        
    return False, 0.0

# ... [The rest of the refactored code for alignment and batch processing] ...
# Due to the complexity, I will continue with the rest of the script.
# The following is the continuation of the refactored code.

def _flatten_json_titles(titles_json: List[Any]) -> List[Dict[str, Any]]:
    """Flattens the nested JSON title structure into a list of title dictionaries."""
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

def initial_title_alignment(content: str, titles_json_path: str, output_md_path: str) -> Tuple[bool, List[Dict]]:
    """Performs the initial alignment of Markdown titles against the JSON structure."""
    try:
        with open(titles_json_path, 'r', encoding='utf-8') as f:
            titles_json_data = json.load(f)
        json_titles = _flatten_json_titles(titles_json_data)
        
        lines = content.splitlines(True)
        processed_lines = list(lines)
        heading_re = re.compile(r'^(#+)\s*(.+?)\s*$')
        md_titles = [(m.group(2).strip(), i, len(m.group(1))) for i, line in enumerate(lines) if (m := heading_re.match(line))]
        
        matched_md_lines = set()
        unmatched_json_titles = []
        md_title_pointer = 0

        for json_idx, json_title_info in enumerate(json_titles):
            json_title, json_level = json_title_info["title"], json_title_info["level"]
            best_match_idx, best_sim = -1, 0.0

            for md_idx in range(md_title_pointer, len(md_titles)):
                md_title, md_line, _ = md_titles[md_idx]
                if md_line in matched_md_lines: continue
                is_match, similarity = _is_title_match(md_title, json_title)
                if is_match and similarity > best_sim:
                    best_sim, best_match_idx = similarity, md_idx

            if best_match_idx != -1:
                md_title, md_line, _ = md_titles[best_match_idx]
                processed_lines[md_line] = f"{'#' * json_level} {md_title}\n"
                matched_md_lines.add(md_line)
                md_title_pointer = best_match_idx + 1
            else:
                prev = json_titles[json_idx - 1]["title"] if json_idx > 0 else None
                next_t = json_titles[json_idx + 1]["title"] if json_idx < len(json_titles) - 1 else None
                unmatched_json_titles.append({"title": json_title, "level": json_level, "prev_title": prev, "next_title": next_t})
        
        for md_title, md_line, _ in md_titles:
            if md_line not in matched_md_lines:
                processed_lines[md_line] = f"{'#' * UNALIGNED_TITLE_LEVEL} {md_title}\n"
        
        Path(output_md_path).write_text("".join(processed_lines), encoding='utf-8')
        return True, unmatched_json_titles
    except Exception as e:
        logging.error(f"Initial alignment failed: {e}\n{traceback.format_exc()}")
        return False, []

def process_unmatched_titles(aligned_md_path: str, unmatched_titles: List[Dict], api_key: str, metrics_logger: ApiMetricsLogger):
    """Processes missing titles using an LLM to find the best insertion point."""
    metrics_logger.set_unmatched_titles_count(len(unmatched_titles))
    for title_info in unmatched_titles:
        try:
            lines = Path(aligned_md_path).read_text(encoding='utf-8').splitlines(True)
            heading_re = re.compile(r'^(#+)\s*(.+?)\s*$')
            md_titles_map = {i: m.group(2).strip() for i, line in enumerate(lines) if (m := heading_re.match(line))}

            prev_line = next((ln for ln, t in md_titles_map.items() if _is_title_match(t, title_info["prev_title"])[0]), 0) if title_info.get("prev_title") else 0
            next_line = next((ln for ln, t in md_titles_map.items() if _is_title_match(t, title_info["next_title"])[0]), len(lines) - 1) if title_info.get("next_title") else len(lines) - 1

            content_for_llm = "\n".join([f"{prev_line + i + 1}. {_clean_md_title(line.rstrip())}" for i, line in enumerate(lines[prev_line:next_line + 1])])

            prompt = f"""
Take a deep breath and work on this step by step. You must determine the best position to insert a missing title into a document.

Target Title (Traditional Chinese): "{_to_traditional(title_info['title'])}" (Intended Level: {title_info['level']})

Contextual Information:
- Preceding Title: "{title_info.get('prev_title')}"
- Succeeding Title: "{title_info.get('next_title')}"

Below is the relevant document section (titles are cleaned of numbering):
{content_for_llm[:8000]}

[Analysis Task]
Analyze the content to find the most logical insertion point for the target title. Consider if it should be a new summary heading or a specific content heading. Pay attention to '####' titles, which can be replaced if semantically equivalent.

[Required Output Format]
Choose ONE format:
1.  **Insert global line number:** <line_number>
    **Reason:** <Your justification.>
2.  **Replace global line number:** <line_number>
    **Reason:** <Your justification for replacement.>
3.  **Insertion point:** None
    **Reason:** <Explanation.>
"""
            response, in_tokens, out_tokens = get_llm_response(prompt, api_key)
            status = "API_FAIL" if not response else "NO_POS" if "None" in response else "PENDING"
            metrics_logger.log_api_call(in_tokens, out_tokens, "InsertionAnalysis", status, title_info['title'])

            if not response or "Insertion point: None" in response:
                metrics_logger.log_insertion_result(title_info['title'], False, "No suitable position found by LLM")
                continue

            insert_match = re.search(r'Insert global line number[:：]\s*(\d+)', response)
            replace_match = re.search(r'Replace global line number[:：]\s*(\d+)', response)
            line_to_modify, is_replacement = (-1, False)

            if insert_match: line_to_modify = int(insert_match.group(1)) - 1
            elif replace_match: line_to_modify, is_replacement = int(replace_match.group(1)) - 1, True

            if prev_line <= line_to_modify <= next_line:
                if is_replacement: lines[line_to_modify] = f"{'#' * title_info['level']} {title_info['title']}\n"
                else: lines.insert(line_to_modify, f"{'#' * title_info['level']} {title_info['title']}\n")
                metrics_logger.log_insertion_result(title_info['title'], True, f"{'Replaced' if is_replacement else 'Inserted'} at line {line_to_modify + 1}")
            else:
                lines.insert(prev_line, f"{'#' * title_info['level']} {title_info['title']}\n")
                metrics_logger.log_insertion_result(title_info['title'], True, f"Fallback insertion at line {prev_line + 1}")

            Path(aligned_md_path).write_text("".join(lines), encoding='utf-8')
        except Exception as e:
            logging.error(f"Error processing unmatched title '{title_info['title']}': {e}\n{traceback.format_exc()}")
            metrics_logger.log_insertion_result(title_info['title'], False, str(e))

def batch_align_titles(base_path: str, api_key: str):
    """Batch processes all 'grouped.md' files for title alignment."""
    base_path = Path(base_path)
    metrics_logger = ApiMetricsLogger()
    grouped_files = list(base_path.rglob("grouped.md"))
    
    logging.info(f"Starting batch alignment for {len(grouped_files)} files...")
    for i, grouped_file in enumerate(grouped_files, 1):
        try:
            logging.info(f"\n--- Processing file {i}/{len(grouped_files)}: {grouped_file.relative_to(base_path)} ---")
            metrics_logger.start_file_processing(str(grouped_file.relative_to(base_path)))
            
            titles_json_path = grouped_file.parent / "titles.json"
            if not titles_json_path.exists():
                logging.warning(f"titles.json not found for {grouped_file.parent.name}. Skipping.")
                continue

            output_md_path = grouped_file.parent / "markdown_aligned.md"
            content = grouped_file.read_text(encoding='utf-8')
            
            success, unmatched = initial_title_alignment(content, str(titles_json_path), str(output_md_path))
            if success and unmatched:
                process_unmatched_titles(str(output_md_path), unmatched, api_key, metrics_logger)

        except Exception as e:
            logging.error(f"Failed to process {grouped_file}: {e}\n{traceback.format_exc()}")
    
    metrics_logger.finalize_log()
    logging.info("Batch processing complete.")

def main():
    """Main execution function."""
    BASE_PATH = r"/"
    API_KEY = ''  
    batch_align_titles(BASE_PATH, API_KEY)

if __name__ == '__main__':
    main()