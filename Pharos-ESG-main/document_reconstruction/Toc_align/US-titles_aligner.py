# -*- coding: utf-8 -*-

"""
Markdown Title Alignment and Formatting Tool for English Reports

Description:
    Aligns Markdown file title structure with PDF table of contents structure,
    ensuring title completeness and correctness for English reports.

Main Features:
1. Title Alignment
   - Ensures all titles defined in PDF table of contents exist in Markdown file
   - Arranges titles according to PDF table of contents order
   - Automatically supplements missing main titles and subtitles

2. Title Formatting
   - Main titles uniformly formatted as "# Title"
   - Subtitles uniformly formatted as "## Subtitle"
   - Unaligned titles converted to "### Subtitle"

3. Title Matching
   - Supports fuzzy matching of title text (ignoring space differences)
   - Preserves original title format and case

Input Files:
    - pdf_titles.json: PDF table of contents structure file
    - markdown2_cleaned.md: Markdown file to be processed

Output Files:
    - markdown_aligned.md: Processed Markdown file

Notes:
    - Preserves non-title content of document
    - Maintains title hierarchy structure
    - Ensures reasonable title insertion positions
"""

import re
import json
import os
import sys
import time
import datetime
# Note: OpenCC library for traditional/simplified Chinese conversion removed
# as this version is specifically designed for English reports
from rapidfuzz import fuzz, process as rapidfuzz_process
from typing import List, Dict, Tuple, Set
from pathlib import Path

# Add logging functionality for English report processing
class TokenLogger:
    def __init__(self, log_file="token_usage.txt"):
        self.log_file = log_file
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.file_count = 0
        self.current_file = ""
        self.current_file_input_tokens = 0
        self.current_file_output_tokens = 0
        self.successful_insertions = 0
        self.failed_insertions = 0
        self.total_unmatched_titles = 0
        
        # Create or clear log file
        with open(self.log_file, "w", encoding="utf-8") as f:
            f.write(f"Processing start time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n")
            f.write("Detailed API call records:\n")
            f.write("Operation Type,File Name,Input Tokens,Output Tokens,Total Tokens,Insert Status,Target Title\n")
    
    def log_file_start(self, file_name):
        """Record start of processing new file"""
        # If there's a previous file, record its summary first
        if self.current_file:
            self._log_file_summary()
        
        self.current_file = file_name
        self.file_count += 1
        self.current_file_input_tokens = 0
        self.current_file_output_tokens = 0
        
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(f"\n{'='*80}\n")
            f.write(f"Starting to process file {self.file_count}: {file_name}\n")
            f.write(f"Start time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"{'='*80}\n")
    
    def log_api_call(self, input_tokens, output_tokens, description="", insert_status="Unknown", target_title=""):
        """Record token usage for single API call"""
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.current_file_input_tokens += input_tokens
        self.current_file_output_tokens += output_tokens
        
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(f"{description},{self.current_file},{input_tokens},{output_tokens},{input_tokens + output_tokens},{insert_status},{target_title}\n")
        
        # Update real-time summary
        self._update_realtime_summary()
    
    def log_insertion_result(self, title, success, reason=""):
        """Record insertion result"""
        if success:
            self.successful_insertions += 1
            status = "Success"
        else:
            self.failed_insertions += 1
            status = "Failed"
        
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(f"Insertion result: Title='{title}', Status={status}, Reason={reason}\n")
    
    def log_unmatched_titles_count(self, count):
        """Record count of unmatched titles"""
        self.total_unmatched_titles += count
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(f"Current file unmatched titles count: {count}\n")
    
    def _log_file_summary(self):
        """Record processing summary for single file"""
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(f"\nFile '{self.current_file}' processing summary:\n")
            f.write(f"  - Input tokens: {self.current_file_input_tokens}\n")
            f.write(f"  - Output tokens: {self.current_file_output_tokens}\n")
            f.write(f"  - Total tokens: {self.current_file_input_tokens + self.current_file_output_tokens}\n")
            f.write(f"  - Completion time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    def _update_realtime_summary(self):
        """Update real-time summary information at end of file"""
        # Read existing content
        with open(self.log_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Remove previous real-time summary (if exists)
        if "\n[Real-time Summary]" in content:
            content = content.split("\n[Real-time Summary]")[0]
        
        # Add new real-time summary
        realtime_summary = f"\n[Real-time Summary] - Update time: {datetime.datetime.now().strftime('%H:%M:%S')}\n"
        realtime_summary += f"Files processed: {self.file_count}\n"
        realtime_summary += f"Total input tokens: {self.total_input_tokens}\n"
        realtime_summary += f"Total output tokens: {self.total_output_tokens}\n"
        realtime_summary += f"Total token consumption: {self.total_input_tokens + self.total_output_tokens}\n"
        realtime_summary += f"Successful insertions: {self.successful_insertions}\n"
        realtime_summary += f"Failed insertions: {self.failed_insertions}\n"
        
        with open(self.log_file, "w", encoding="utf-8") as f:
            f.write(content + realtime_summary)
    
    def log_summary(self):
        """Record final summary information"""
        # Record summary of last file
        if self.current_file:
            self._log_file_summary()
        
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(f"\n{'='*80}\n")
            f.write(f"Final Processing Summary\n")
            f.write(f"{'='*80}\n")
            f.write(f"Processing completion time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total files processed: {self.file_count}\n")
            f.write(f"Total input tokens: {self.total_input_tokens}\n")
            f.write(f"Total output tokens: {self.total_output_tokens}\n")
            f.write(f"Total token consumption: {self.total_input_tokens + self.total_output_tokens}\n")
            f.write(f"Total unmatched titles: {self.total_unmatched_titles}\n")
            f.write(f"Successfully inserted titles: {self.successful_insertions}\n")
            f.write(f"Failed inserted titles: {self.failed_insertions}\n")
            f.write(f"Insertion success rate: {(self.successful_insertions/(self.successful_insertions+self.failed_insertions)*100):.1f}% (if insertion operations exist)\n")
            f.write(f"{'='*80}\n")

# Initialize token logger for English report processing
token_logger = TokenLogger()

# Add current directory to Python path for direct import support
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from deepseek_title import deepseek_api, SYSTEM_PROMPT_SELECT_TITLE, SYSTEM_PROMPT_INSERT_POSITION

def extract_alphanumeric(text: str) -> str:
    """Extract English letters, numbers, and common punctuation for English reports"""
    return ''.join(char for char in text if (
        'A' <= char <= 'Z' or 'a' <= char <= 'z' or
        '0' <= char <= '9' or
        char in '.,;:!?()-[]{}"\' '
    ))

def clean_md_title(title: str) -> str:
    """Clean markdown title for English reports by removing common prefixes and formatting"""
    # Remove leading numbers and dots (e.g., "1.1", "2.3.4")
    cleaned = re.sub(r'^[\d\s\.\-]+', '', title)
    
    # Remove common English section prefixes
    cleaned = re.sub(r'^(Chapter|Section|Part|Appendix|Article)\s*[\d\s]*[:\-\s]*', '', cleaned, flags=re.IGNORECASE)
    
    # Remove parenthetical numbering (e.g., "(1)", "(a)", "(i)")
    cleaned = re.sub(r'^[\(\[]([\d\w]+)[\)\]][\s]*', '', cleaned)
    
    # Remove bullet points and list markers
    cleaned = re.sub(r'^[•\-\*\+][\s]*', '', cleaned)
    
    # Clean up multiple spaces
    cleaned = re.sub(r'\s+', ' ', cleaned)
    cleaned = cleaned.strip()
    return cleaned

def normalize_title(title: str) -> str:
    """Normalize title for English reports by extracting alphanumeric content and standardizing case"""
    # Extract alphanumeric content and common punctuation
    text = extract_alphanumeric(title)
    # Convert to lowercase for comparison
    text = text.lower()
    # Remove extra spaces
    return re.sub(r'\s+', '', text)

def get_title_level(entry: dict, is_top_level: bool = False, parent_level: int = 0, is_in_third_level: bool = False) -> Tuple[int, str]:
    """Determine title level and parent title based on JSON structure
    Args:
        entry: JSON title entry
        is_top_level: Whether it's a top-level title (direct element in JSON array)
        parent_level: Parent title level
        is_in_third_level: Whether it's in third-level subtitles
    Returns:
        Tuple[int, str]: (level, parent_title)
        
    Rules:
    1. Top-level titles (direct elements in JSON array) are level 1 titles (#)
    2. Second-level nesting:
       - titles in subtitles are level 2 titles (##)
    3. Third-level nesting:
       - strings in subtitles of subtitles are level 3 titles (###)
    4. Fourth-level titles:
       - titles under level 3 titles are level 4 titles (####)
    """
    # If it's a title in third-level subtitles, return level 3 directly
    if is_in_third_level:
        return (3, None)
        
    if not isinstance(entry, dict):
        # String type title
        if parent_level == 1:
            return (3, None)  # String under level 1 title is level 3 title
        elif parent_level == 2:
            return (3, None)  # String under level 2 title is level 3 title
        elif parent_level == 3:
            return (4, None)  # String under level 3 title is level 4 title
        return (4, None)  # Other cases are level 4 titles
        
    title = entry.get('title', '')
    if not title:
        return (1, None)
        
    # Top-level titles (direct elements in JSON array) are always level 1 titles
    if is_top_level:
        return (1, None)
        
    # Determine based on parent level and subtitles structure
    if 'subtitles' in entry:
        # Check the type of first element in subtitles
        first_subtitle = entry['subtitles'][0]
        if isinstance(first_subtitle, str):
            # If subtitles contains strings, this is a level 2 title
            return (2, None)
        elif isinstance(first_subtitle, dict) and 'subtitles' in first_subtitle:
            # If elements in subtitles have subtitles, this is a level 2 title
            return (2, None)
            
    # Determine based on parent level
    if parent_level == 1:
        return (2, None)  # Title under level 1 title is level 2 title
    elif parent_level == 2:
        return (3, None)  # Title under level 2 title is level 3 title
    elif parent_level == 3:
        return (4, None)  # Title under level 3 title is level 4 title
        
    return (4, None)  # Default case is level 4 title

def is_title_match(md_title: str, json_title: str) -> tuple:
    """Check if markdown title matches JSON title for English reports"""
    cleaned_md_title = clean_md_title(md_title)
    cleaned_json_title = clean_md_title(json_title)
    # Normalize for comparison
    norm_md = normalize_title(cleaned_md_title)
    norm_json = normalize_title(cleaned_json_title)
    # Exact match
    if norm_md == norm_json:
        return True, 1.0, True
    # Fuzzy matching with higher threshold for English
    from rapidfuzz import fuzz
    similarity = fuzz.ratio(norm_md, norm_json) / 100.0
    if similarity >= 0.80:  # Higher threshold for English
        return True, similarity, False
    # Substring matching
    if norm_json in norm_md or norm_md in norm_json:
        return True, 0.85, False
    return False, 0.0, False

def process_json_titles(titles_json: List) -> List[Tuple[str, int, int, str]]:
    """Process JSON titles, return list of (title, level, original_index, parent_title)"""
    result = []
    
    def process_entry(entry: dict, index: int, parent: str = None, parent_level: int = 0, is_top_level: bool = False, is_in_third_level: bool = False):
        if isinstance(entry, str):
            # Determine string title level based on parent level and third-level status
            level, _ = get_title_level(entry, is_top_level, parent_level, is_in_third_level)
            result.append((entry, level, index, parent))
            return
            
        title = entry.get('title', '')
        if not title:
            return
            
        # Get current title level
        level, _ = get_title_level(entry, is_top_level, parent_level, is_in_third_level)
        result.append((title, level, index, parent))
        
        # Process subtitles
        if 'subtitles' in entry:
            # Check if in third level
            # If current is level 2 title, strings in its subtitles are level 3 titles
            is_third_level = level == 2
            
            for sub in entry['subtitles']:
                if isinstance(sub, str):
                    # String type subtitle, determine level based on current level and third-level status
                    sub_level, _ = get_title_level(sub, False, level, is_third_level)
                    result.append((sub, sub_level, index, title))
                else:
                    # Recursively process subtitles, non-top-level
                    process_entry(sub, index, title, level, False, is_third_level)
    
    # Process all titles
    for i, entry in enumerate(titles_json):
        # Process top-level titles
        process_entry(entry, i, None, 0, True, False)
        # Print level information for each title for debugging
        level, _ = get_title_level(entry, True)
        print(f"JSON title: '{entry.get('title', '')}' -> Level: {level} (top-level title)")
    
    return result

def find_best_match_in_range(md_titles: List[Tuple[str, int, int]], start_title: str, end_title: str, target_title: str, level: int, api_key: str) -> Tuple[int, float, int]:
    """在指定范围内查找最佳匹配
    Args:
        md_titles: Markdown标题列表，每个元素为(标题文本, 行号, 层级)
        start_title: 开始标题（目标标题在JSON中的前一个标题）
        end_title: 结束标题（目标标题在JSON中的后一个标题）
        target_title: 目标标题
        level: 目标标题的层级
        api_key: DeepSeek API密钥
    Returns:
        Tuple[int, float, int]: (最佳匹配行号, 相似度, 匹配的层级)
    """
    # 确保输入有效
    if not md_titles:
        print("Warning: md_titles list is empty")
        return -1, 0.0, -1
    
    # 找到开始和结束的行号
    start_line = 0
    end_line = len(md_titles) - 1  # 使用列表长度作为默认结束位置
    
    print(f"\nStarting title matching: '{target_title}' (target level: {level})")
    print(f"Search range: from title '{start_title}' to '{end_title}'")
    
    # 找到开始标题的行号（目标标题在JSON中的前一个标题）
    if start_title:
        for md_title, line_num, _ in md_titles:
            if is_title_match(md_title, start_title)[0]:
                start_line = line_num  # 从当前行开始搜索
                print(f"Found start title '{start_title}' at line: {line_num}")
                break
    
    # 找到结束标题的行号（目标标题在JSON中的后一个标题）
    if end_title:
        for md_title, line_num, _ in md_titles:
            if is_title_match(md_title, end_title)[0]:
                end_line = line_num - 1  # 到前一行结束搜索
                print(f"Found end title '{end_title}' at line: {line_num}")
                break
    
    print(f"Actual search range: line {start_line} to {end_line}")
    
    # 直接使用完整的目标标题
    print(f"Target title: '{target_title}'")
    
    # 根据目标标题级别执行不同的搜索策略
    if level == 1:  # 一级标题
        print("\n目标是一级标题，按顺序搜索：")
        print("1. 先搜索二级标题")
        best_line, best_similarity, best_level = search_level_titles(2, target_title, md_titles, start_line, end_line, start_title, end_title, api_key)
        if best_line != -1:
            return best_line, best_similarity, best_level
            
        print("\n2. 未找到匹配的二级标题，搜索三级标题")
        best_line, best_similarity, best_level = search_level_titles(3, target_title, md_titles, start_line, end_line, start_title, end_title, api_key)
        if best_line != -1:
            return best_line, best_similarity, best_level
            
        print("\n3. 未找到匹配的三级标题，搜索四级标题")
        best_line, best_similarity, best_level = search_level_titles(4, target_title, md_titles, start_line, end_line, start_title, end_title, api_key)
        if best_line != -1:
            return best_line, best_similarity, best_level
            
        print("\n4. 所有级别的标题都未找到匹配，尝试在内容中查找插入位置")
        with open("aligned_output.md", 'r', encoding='utf-8') as f:
            content = f.readlines()
        # 直接返回-1，因为我们现在在process_unmatched_titles中处理所有未匹配的标题
        return -1, 0.0, -1
            
    elif level == 2:  # 二级标题
        print("\n目标是二级标题，按顺序搜索：")
        print("1. 先搜索三级标题")
        best_line, best_similarity, best_level = search_level_titles(3, target_title, md_titles, start_line, end_line, start_title, end_title, api_key)
        if best_line != -1:
            return best_line, best_similarity, best_level
            
        print("\n2. 未找到匹配的三级标题，搜索四级标题")
        best_line, best_similarity, best_level = search_level_titles(4, target_title, md_titles, start_line, end_line, start_title, end_title, api_key)
        if best_line != -1:
            return best_line, best_similarity, best_level
            
        print("\n3. 所有级别的标题都未找到匹配，尝试在内容中查找插入位置")
        with open("aligned_output.md", 'r', encoding='utf-8') as f:
            content = f.readlines()
        # 直接返回-1，因为我们现在在process_unmatched_titles中处理所有未匹配的标题
        return -1, 0.0, -1
            
    elif level == 3:  # 三级标题
        print("\n目标是三级标题，按顺序搜索：")
        print("1. 搜索四级标题")
        best_line, best_similarity, best_level = search_level_titles(4, target_title, md_titles, start_line, end_line, start_title, end_title, api_key)
        if best_line != -1:
            return best_line, best_similarity, best_level
            
        print("\n2. 未找到匹配的四级标题，尝试在内容中查找插入位置")
        with open("aligned_output.md", 'r', encoding='utf-8') as f:
            content = f.readlines()
        # 直接返回-1，因为我们现在在process_unmatched_titles中处理所有未匹配的标题
        return -1, 0.0, -1
    
    return -1, 0.0, -1

def align_titles(content: str, titles_json_path: str, output_md_path: str) -> Tuple[bool, List[Tuple[str, int, int, str, str, str]]]:
    """对齐标题并返回未匹配的标题列表（含前后标题信息）
    Returns:
        Tuple[bool, List[Tuple[str, int, int, str, str, str]]]: (是否成功, 未匹配的标题列表，每项为(标题, 层级, 原始索引, 父标题, prev_title, next_title))
    """
    try:
        with open(titles_json_path, 'r', encoding='utf-8') as f:
            titles_json = json.load(f)
        print(f"成功读取JSON文件，包含 {len(titles_json)} 个标题")
        json_titles = process_json_titles(titles_json)
        print(f"Number of processed JSON titles: {len(json_titles)}")
        lines = content.splitlines(True)
        heading_re = re.compile(r'^(#+)\s*(.+?)\s*$')
        processed_lines = list(lines)
        md_titles = []  # (标题文本, 行号, 原始层级)
        for i, line in enumerate(lines):
            m = heading_re.match(line)
            if m:
                level = len(m.group(1))
                title = m.group(2).strip()
                md_titles.append((title, i, level))
        print(f"在MD文件中找到 {len(md_titles)} 个标题")
        matched_md_idx = set()  # 已被匹配的md标题行号
        matched_json_idx = set()  # 已被匹配的json标题索引
        json2md = {}  # json索引->md索引
        md2json = {}  # md行号->json索引
        unmatched_titles = []  # (json_title, json_level, json_index, parent, prev_title, next_title)
        md_ptr = 0  # md标题指针
        for j, (json_title, json_level, json_index, parent) in enumerate(json_titles):
            # 1. 精确匹配
            found = False
            for m in range(md_ptr, len(md_titles)):
                md_title, md_line, md_level = md_titles[m]
                if md_line in matched_md_idx:
                    continue
                # Clean MD title for comparison
                cleaned_md_title = clean_md_title(md_title)
                # Exact match after cleaning
                if cleaned_md_title.lower() == json_title.lower() or normalize_title(cleaned_md_title) == normalize_title(json_title):
                    processed_lines[md_line] = f"{'#'*json_level} {md_title}\n"
                    matched_md_idx.add(md_line)
                    matched_json_idx.add(j)
                    json2md[j] = md_line
                    md2json[md_line] = j
                    md_ptr = m + 1
                    print(f"Exact match: MD title '{md_title}' (cleaned: '{cleaned_md_title}') -> JSON title '{json_title}' (level: {json_level})")
                    found = True
                    break
            if found:
                continue
            # 2. 模糊匹配
            best_m = -1
            best_sim = 0
            for m in range(md_ptr, len(md_titles)):
                md_title, md_line, md_level = md_titles[m]
                if md_line in matched_md_idx:
                    continue
                is_match, similarity, is_exact = is_title_match(md_title, json_title)
                if is_match and similarity > best_sim:
                    best_sim = similarity
                    best_m = m
            if best_m != -1:
                md_title, md_line, md_level = md_titles[best_m]
                processed_lines[md_line] = f"{'#'*json_level} {md_title}\n"
                matched_md_idx.add(md_line)
                matched_json_idx.add(j)
                json2md[j] = md_line
                md2json[md_line] = j
                md_ptr = best_m + 1
                print(f"Fuzzy match: MD title '{md_title}' -> JSON title '{json_title}' (level: {json_level}, similarity: {best_sim:.2f})")
                continue
            # 3. 未匹配，记录前后json标题
            prev_title = json_titles[j-1][0] if j > 0 else None
            next_title = json_titles[j+1][0] if j < len(json_titles)-1 else None
            unmatched_titles.append((json_title, json_level, json_index, parent, prev_title, next_title))
            print(f"Unmatched: JSON title '{json_title}' (level: {json_level})")
        # 未匹配的md标题全部降级为####
        for m, (md_title, md_line, md_level) in enumerate(md_titles):
            if md_line not in matched_md_idx:
                processed_lines[md_line] = f"#### {md_title}\n"
        # 写入输出文件
        output_dir = os.path.dirname(output_md_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        print(f"准备写入输出文件: {output_md_path}")
        with open(output_md_path, 'w', encoding='utf-8') as f:
            f.writelines(processed_lines)
        print(f"成功写入输出文件，共 {len(processed_lines)} 行")
        return True, unmatched_titles
    except Exception as e:
        print(f"Error processing file: {str(e)}")
        import traceback
        print(f"Error details:\n{traceback.format_exc()}")
        return False, []

def insert_title_at_line(lines: List[str], title: str, level: int, line_num: int):
    """在指定行号插入新标题"""
    new_title_line = f"{'#' * level} {title}\n"
    if 0 <= line_num <= len(lines):
        lines.insert(line_num, new_title_line)
        print(f"已将标题 '{title}' (层级 {level}) 插入到行号 {line_num + 1}")
    else:
        print(f"Warning: Invalid insertion line number {line_num + 1}, title '{title}' not inserted")

def find_adjacent_titles(titles_json: List, target_title: str) -> Tuple[str, str]:
    """查找目标标题的前后标题
    Args:
        titles_json: JSON标题列表
        target_title: 目标标题
    Returns:
        Tuple[str, str]: (前一个标题, 后一个标题)
    """
    def flatten_titles(json_data: List) -> List[str]:
        """将JSON结构扁平化为标题列表"""
        titles = []
        for item in json_data:
            if isinstance(item, dict):
                if 'title' in item:
                    titles.append(item['title'])
                if 'subtitles' in item:
                    titles.extend(flatten_titles(item['subtitles']))
        return titles

    # 将所有标题扁平化为列表
    all_titles = flatten_titles(titles_json)
    
    # 找到目标标题的索引
    try:
        target_index = all_titles.index(target_title)
    except ValueError:
        return None, None
    
    # 获取前一个标题
    prev_title = all_titles[target_index - 1] if target_index > 0 else None
    
    # 获取后一个标题
    next_title = all_titles[target_index + 1] if target_index < len(all_titles) - 1 else None
    
    return prev_title, next_title

def find_next_title(titles_json: List, current_title: str, depth: int = 0) -> str:
    """Recursively find the next title after current title
    Args:
        titles_json: JSON title list
        current_title: Current title
        depth: Recursion depth for controlling search range
    Returns:
        str: Found next title, return None if not found
    """
    def flatten_titles(json_data: List) -> List[str]:
        """Flatten JSON structure to title list"""
        titles = []
        for item in json_data:
            if isinstance(item, dict):
                if 'title' in item:
                    titles.append(item['title'])
                if 'subtitles' in item:
                    titles.extend(flatten_titles(item['subtitles']))
        return titles

    # Flatten all titles to list
    all_titles = flatten_titles(titles_json)
    
    try:
        current_index = all_titles.index(current_title)
        # If current title is not the last one, return next title
        if current_index + 1 < len(all_titles):
            return all_titles[current_index + 1]
        return None
    except ValueError:
        return None

def parse_page_blocks(md_path: str) -> List[Tuple[str, List[str]]]:
    print(f"[parse_page_blocks] 解析MD文件: {md_path}")
    page_blocks = []
    with open(md_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith('<page_idx:'):
            m = re.match(r'<page_idx:(\d+)>', line)
            if m:
                page_idx = m.group(1)
                i += 1
                while i < len(lines) and lines[i].strip() != '[':
                    i += 1
                i += 1
                content = []
                while i < len(lines) and lines[i].strip() != ']':
                    content.append(lines[i].rstrip('\n'))
                    i += 1
                page_blocks.append((page_idx, content))
        i += 1
    print(f"[parse_page_blocks] Parsing completed, total {len(page_blocks)} page blocks")
    return page_blocks

def filter_page_blocks_by_lines(all_blocks, start_line, end_line, strict_only=False):
    """
    根据全局行号范围，筛选出所有在 start_line ~ end_line 范围内有交集的页块。
    如果没有交集，则自动扩展后续最多5个页块（仅在 strict_only=False 时）。
    strict_only: True 时只返回严格交集页块，不做扩展。
    返回: [{"page_idx": 页号, "content": [该页全部段落行]} ...]
    """
    result = []
    current_line = 0
    for page_idx, paras in all_blocks:
        page_start = current_line
        page_end = current_line + len(paras) - 1
        if page_end >= start_line and page_start <= end_line:
            result.append({"page_idx": page_idx, "content": paras})
        current_line += len(paras)
    if strict_only:
        return result
    # 如果没有任何页块被选中，则扩展后续最多5个页块
    if not result:
        current_line = 0
        for page_idx, paras in all_blocks:
            page_start = current_line
            if page_start > start_line:
                result.append({"page_idx": page_idx, "content": paras})
                if len(result) >= 5:
                    break
            current_line += len(paras)
    return result

def process_unmatched_titles(aligned_md_path: str, unmatched_titles: List[Tuple[str, int, int, str, str, str]], titles_json: List, api_key: str) -> bool:
    print("[process_unmatched_titles] Starting to process unmatched titles...")
    
    print(f"[process_unmatched_titles] Total unmatched titles: {len(unmatched_titles)}")
    # 记录未匹配标题数量
    token_logger.log_unmatched_titles_count(len(unmatched_titles))
    title_idx = 0
    
    try:
        while title_idx < len(unmatched_titles):
            with open(aligned_md_path, 'r', encoding='utf-8') as f:
                content = f.read()
            lines = content.splitlines(True)
            heading_re = re.compile(r'^(#+)\s*(.+?)\s*$')
            md_titles = []
            for line_idx, line in enumerate(lines):
                m = heading_re.match(line)
                if m:
                    level = len(m.group(1))
                    title = m.group(2).strip()
                    md_titles.append((title, line_idx, level))
            current_title_info = unmatched_titles[title_idx]
            json_title, json_level, json_index, parent, prev_title, next_title = current_title_info
            print(f"[process_unmatched_titles] Processing unmatched title: '{json_title}' (level: {json_level})")
            # Find physical location context
            prev_line = 0
            next_line = len(lines) - 1
            # 找到前一个标题的行号
            if prev_title:
                for md_title, line_num, _ in md_titles:
                    cleaned_md_title = clean_md_title(md_title)
                    if extract_alphanumeric(cleaned_md_title) == extract_alphanumeric(prev_title):
                        prev_line = line_num
                        break
            # 找到后一个标题的行号
            if next_title:
                for md_title, line_num, _ in md_titles:
                    cleaned_md_title = clean_md_title(md_title)
                    if extract_alphanumeric(cleaned_md_title) == extract_alphanumeric(next_title):
                        next_line = line_num
                        break
            # 自动扩展end_line，保证LLM能看到正文
            # 如果范围太小（如只覆盖1-2页），则扩展到文档结尾或多给几页
            all_page_blocks = parse_page_blocks(aligned_md_path)
            print(f"[process_unmatched_titles] 解析出 {len(all_page_blocks)} 个页块")
            # Count pages within range
            # 新增：严格范围页块
            strict_page_blocks = filter_page_blocks_by_lines(all_page_blocks, prev_line, next_line, strict_only=True)
            strict_page_range = [int(page['page_idx']) for page in strict_page_blocks]
            # 宽松范围用于内容生成
            page_blocks_in_range = filter_page_blocks_by_lines(all_page_blocks, prev_line, next_line)
            if len(page_blocks_in_range) <= 2:
                # 扩展到文档结尾或多给5页
                last_line = len(lines) - 1
                next_line = min(last_line, prev_line + 200)  # 200行或结尾
                page_blocks_in_range = filter_page_blocks_by_lines(all_page_blocks, prev_line, next_line)
            # 生成 page_blocks_str，保留原始 Markdown 层级和全局行号，并标记类型
            # 先构建全局行号到内容的映射
            line_to_type = {}
            for idx, line in enumerate(lines):
                m = heading_re.match(line)
                if m:
                    line_to_type[idx] = '[标题]'
                else:
                    line_to_type[idx] = '[正文]'
            # 生成 page_blocks_str
            if not page_blocks_in_range:
                print("[process_unmatched_titles] 没有找到任何分页内容块，将直接截取原始行范围")
                raw_lines = lines[prev_line:next_line+1]
                processed_raw_lines = []
                for i, line in enumerate(raw_lines):
                    line_content = line.rstrip()
                    # Check if it's a title line and clean it
                    m = heading_re.match(line)
                    if m:
                        level_marks = m.group(1)  # 获取 # 标记
                        original_title = m.group(2).strip()
                        cleaned_title = clean_md_title(original_title)
                        line_content = f"{level_marks} {cleaned_title}"
                        processed_raw_lines.append(f"{i+prev_line+1}. [标题] {line_content}")
                    else:
                        processed_raw_lines.append(f"{i+prev_line+1}. [正文] {line_content}")
                page_blocks_str = "\n".join(processed_raw_lines)
            else:
                # 保留原有逻辑
                page_blocks_str = ""
                for page in page_blocks_in_range:
                    page_idx = page['page_idx']
                    content_lines = []
                    last_found = prev_line - 1
                    for i, line in enumerate(page['content']):
                        search_start = prev_line if i == 0 else last_found+1
                        found = False
                        for j in range(search_start, len(lines)):
                            if lines[j].strip('\n') == line.strip('\n'):
                                global_line_no = j
                                last_found = j
                                found = True
                                break
                        if not found:
                            global_line_no = prev_line + i
                        type_tag = line_to_type.get(global_line_no, '[正文]')
                        # 如果是标题行，应用清洗函数
                        line_content = lines[global_line_no].rstrip() if found else line.rstrip()
                        if type_tag == '[标题]' and found:
                            # 对标题行进行清洗，保留层级标记
                            m = heading_re.match(lines[global_line_no])
                            if m:
                                level_marks = m.group(1)  # 获取 # 标记
                                original_title = m.group(2).strip()
                                cleaned_title = clean_md_title(original_title)
                                line_content = f"{level_marks} {cleaned_title}"
                        content_lines.append(f"{global_line_no+1}. {type_tag} {line_content}")
                    page_blocks_str += f"第{page_idx}页:\n" + "\n".join(content_lines) + "\n"

            # Print current search range and surrounding title line numbers
            print(f"[process_unmatched_titles] LLM搜索范围：全局行号 {prev_line} 到 {next_line}，严格页码范围 {strict_page_range} (prev_title='{prev_title}'@{prev_line}, next_title='{next_title}'@{next_line})")

            # Check content length, truncate if too long
            max_content_length = 8000  # 限制内容长度
            if len(page_blocks_str) > max_content_length:
                print(f"[process_unmatched_titles] Warning: Content too long ({len(page_blocks_str)} characters), truncating to {max_content_length} characters")
                page_blocks_str = page_blocks_str[:max_content_length] + "\n\n[内容已截断...]"

            # 新prompt（覆盖和替换）
            prompt = f'''
Take a deep breath and work on this step by step.
你需要帮助我们判断一个标题应该插入在文档的哪个位置。

目标标题是："{json_title}" (层级: {json_level})

上下文信息：
    • 开始标题："{prev_title}"
    • 结束标题："{next_title}"

以下是该标题可插入的文档范围内容，已按页分块显示。每一页里包含Markdown行，标题已清洗（去除数字和编号前缀），保留了所有的#、##、###层级标记，以及每行的行号。请仔细阅读：

{page_blocks_str}

【分析任务背景】
该未匹配标题出现在目录结构中“{prev_title}”和“{next_title}”之间。这个标题可能是为了“总揽”或“概括”这部分内容，也可能是为了补充具体“内容性”细节。

【分析步骤要求】
1️⃣ 先对提供的范围内容逐段逐行进行分析总结，标注所有标题和正文的主题点。
2️⃣ 评估该范围内容是否存在缺失的总揽性主题，目标标题能否作为此范围的总揽或概括标题。
3️⃣ 同时分析是否有需要在内容性细节里插入该标题的位置，使其与上下文紧密衔接。
4️⃣ 🔍 **特别注意四级标题替换逻辑**：范围内的"####"标题不一定是真正的四级标题，它们可能是由于之前匹配失败而被降级的标题。如果你发现某个"####"标题与目标标题在语义上高度相关或本质上是同一个概念，可以考虑用目标标题替换该"####"标题。
5️⃣ 在两种角度（总揽性与内容性）都分析后，以及考虑四级标题替换的可能性后，给出最合理的处理建议。

【输出格式要求】

✅ 你可以输出以下两种格式之一：

**选项1 - 新位置插入：**
插入全局行号：<行号>
原因：<详细分析，包括对范围内容的总结、总揽性分析、内容性分析、最终决策理由>

**选项2 - 替换四级标题：**
替换全局行号：<行号>
原因：<说明为什么选择替换该四级标题，包括语义相关性分析、替换的合理性等>

⚠️ 严禁输出页码+行号格式，只能输出"插入全局行号：<行号>"或"替换全局行号：<行号>"！否则会被判为无效答案。
'''
            print(f"[process_unmatched_titles] 调用DeepSeek R1判断插入位置...\nPrompt内容如下:\n{prompt}")
            # 调用API
            # 调用API并记录token使用情况
            response, input_tokens, output_tokens = deepseek_api(prompt, api_key, system_prompt=SYSTEM_PROMPT_INSERT_POSITION)
            
            # Initialize insertion status
            insert_status = "API调用失败"
            if response:
                if "插入位置：无" in response:
                    insert_status = "无合适位置"
                else:
                    insert_status = "待处理"
            
            token_logger.log_api_call(input_tokens, output_tokens, f"插入位置分析", insert_status, json_title)
            print(f"[process_unmatched_titles] DeepSeek R1返回: {response}")
            
            if not response:
                print("[process_unmatched_titles] API调用失败")
                token_logger.log_insertion_result(json_title, False, "API调用失败")
                title_idx += 1
                continue
            if "插入位置：无" in response:
                print(f"[process_unmatched_titles] 标题 '{json_title}' 未找到合适的插入位置")
                token_logger.log_insertion_result(json_title, False, "未找到合适位置")
                title_idx += 1
                continue
            # 解析LLM响应，支持插入和替换两种操作
            insert_match = re.search(r'插入全局行号[:：]\s*(\d+)', response)
            replace_match = re.search(r'替换全局行号[:：]\s*(\d+)', response)
            
            if insert_match:
                # Handle insertion operation (LLM returns 1-based line numbers, need to convert to 0-based)
                global_line_1based = int(insert_match.group(1))
                global_line_0based = global_line_1based - 1
                if not (prev_line <= global_line_0based <= next_line):
                    print(f"[process_unmatched_titles] DeepSeek R1返回的插入行号 {global_line_1based} 不在允许范围 {prev_line+1}~{next_line+1}，将使用范围起点作为兜底插入位置。")
                    global_line_0based = prev_line
                insert_title_at_line(lines, json_title, json_level, global_line_0based)
                with open(aligned_md_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                print(f"已将标题 '{json_title}' (层级 {json_level}) 插入到行号 {global_line_1based}")
                token_logger.log_insertion_result(json_title, True, f"插入到行号 {global_line_1based}")
            elif replace_match:
                # Handle replacement operation (LLM returns 1-based line numbers, need to convert to 0-based)
                replace_line_1based = int(replace_match.group(1))
                replace_line_0based = replace_line_1based - 1
                if not (prev_line <= replace_line_0based <= next_line):
                    print(f"[process_unmatched_titles] DeepSeek R1返回的替换行号 {replace_line_1based} 不在允许范围 {prev_line+1}~{next_line+1}，将使用范围起点插入。")
                    insert_title_at_line(lines, json_title, json_level, prev_line)
                else:
                    # Check if target line is indeed a level 4 title (note: LLM returns 1-based line numbers, need to convert to 0-based)
                    if 0 <= replace_line_0based < len(lines):
                        target_line = lines[replace_line_0based]
                        if target_line.strip().startswith('####'):
                            # Execute replacement operation
                            lines[replace_line_0based] = f"{'#' * json_level} {json_title}\n"
                            print(f"已将行号 {replace_line_1based} 的四级标题替换为 '{json_title}' (层级 {json_level})")
                            token_logger.log_insertion_result(json_title, True, f"替换行号 {replace_line_1based} 的四级标题")
                        else:
                            print(f"[process_unmatched_titles] 行号 {replace_line_1based} 不是四级标题，将改为插入操作。")
                            insert_title_at_line(lines, json_title, json_level, replace_line_0based)
                            token_logger.log_insertion_result(json_title, True, f"改为插入到行号 {replace_line_1based}")
                    else:
                        print(f"[process_unmatched_titles] 替换行号 {replace_line_1based} 超出文件范围，将改为插入操作。")
                        insert_title_at_line(lines, json_title, json_level, prev_line)
                        token_logger.log_insertion_result(json_title, True, f"改为插入到范围起点行号 {prev_line+1}")
                with open(aligned_md_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
            else:
                print(f"[process_unmatched_titles] DeepSeek R1输出格式不规范，未找到可用行号，将尝试在范围起点插入。")
                insert_title_at_line(lines, json_title, json_level, prev_line)
                with open(aligned_md_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                print(f"已将标题 '{json_title}' (层级 {json_level}) 作为总揽性标题插入到范围起点行号 {prev_line}")
                token_logger.log_insertion_result(json_title, True, f"兜底插入到范围起点行号 {prev_line+1}")
            title_idx += 1
        print("[process_unmatched_titles] All unmatched titles processed.\n")
        return True
    except Exception as e:
        print(f"[process_unmatched_titles] Error processing unmatched titles: {str(e)}")
        import traceback
        print(f"[process_unmatched_titles] Error details:\n{traceback.format_exc()}")
        return False

def search_level_titles(target_level: int, target_title: str, md_titles: List[Tuple[str, int, int]], start_line: int, end_line: int, prev_title: str, next_title: str, api_key: str) -> Tuple[int, float, int]:
    """在指定范围内搜索特定级别的标题"""
    level_titles = []
    for md_title, line_num, md_level in md_titles:
        if line_num < start_line or line_num > end_line:
            continue
        if md_level == target_level:
            level_titles.append((md_title, line_num, md_level))
            print(f"找到候选标题: '{md_title}' (行号: {line_num}, 级别: {md_level})")
    
    if level_titles:
        print(f"\n在范围内找到 {len(level_titles)} 个 {target_level} 级标题")
        # 直接返回-1，因为我们现在在process_unmatched_titles中处理所有未匹配的标题
        return -1, 0.0, -1
    else:
        print(f"\n在范围内未找到任何 {target_level} 级标题")
        # 直接返回-1，因为我们现在在process_unmatched_titles中处理所有未匹配的标题
        return -1, 0.0, -1

def process_directory(base_path: str, api_key: str):
    """
    处理目录下的所有markdown文件
    :param base_path: 基础路径
    :param api_key: DeepSeek API密钥
    """
    base_path = Path(base_path)
    
    # 获取md_files目录
    md_files_dir = base_path / "md_files"
    if not md_files_dir.exists():
        print(f"Error: md_files directory not found: {md_files_dir}")
        return
    
    print(f"\nStarting to process directory: {md_files_dir}")
    
    # Statistics
    total_files = 0
    processed_files = 0
    failed_files = 0
    
    # Traverse all subdirectories
    for report_dir in md_files_dir.iterdir():
        if report_dir.is_dir():
            # Check directory name format
            parts = report_dir.name.split('_')
            if len(parts) < 3:  # 至少需要股票代码、公司名和报告名
                print(f"Warning: Incorrect directory name format: {report_dir.name}")
                continue
                
            # Check if first part is a date (8 digits)
            is_date_format = len(parts[0]) == 8 and parts[0].isdigit()
            
            # 查找处理后的markdown文件和titles.json文件
            processed_md = next(report_dir.glob("*_without_toc_processed.md"), None)
            titles_json = next(report_dir.glob("titles.json"), None)
            
            if not processed_md or not titles_json:
                print(f"Warning: Required files not found in {report_dir}")
                continue
            
            total_files += 1
            print(f"\nProcessing file: {processed_md}")
            
            try:
                # 读取文件内容
                with open(processed_md, 'r', encoding='utf-8') as f:
                    content = f.read()
                with open(titles_json, 'r', encoding='utf-8') as f:
                    titles = json.load(f)
                
                # 设置输出文件路径
                output_md = report_dir / f"{report_dir.name}_align.md"
                
                # 对齐标题
                success, unmatched_titles = align_titles(content, str(titles_json), str(output_md))
                
                if success:
                    # Process unmatched titles
                    if unmatched_titles:
                        process_unmatched_titles(str(output_md), unmatched_titles, titles, api_key)
                    processed_files += 1
                else:
                    failed_files += 1
                    
            except Exception as e:
                print(f"处理文件时出错: {str(e)}")
                failed_files += 1
                continue
    
    # Print statistics
    print(f"\nProcessing completed! Statistics:")
    print(f"- 总文件数: {total_files}")
    print(f"- 成功处理: {processed_files}")
    print(f"- 处理失败: {failed_files}")

def write_page_blocks(page_blocks: List[Tuple[str, List[str]]], out_path: str):
    print(f"[write_page_blocks] 写入MD文件: {out_path}，共 {len(page_blocks)} 个页块")
    with open(out_path, 'w', encoding='utf-8') as f:
        for page_idx, paragraphs in page_blocks:
            f.write(f'<page_idx:{page_idx}>\n[\n')
            for para in paragraphs:
                f.write(para + '\n')
            f.write(']\n\n')
    print(f"[write_page_blocks] 写入完成。\n")

def align_titles_in_lines(paragraphs, titles_json, api_key=None):
    print("[align_titles_in_lines] Starting to align paragraph titles...")
    heading_re = re.compile(r'^(#+)\s*(.+?)\s*$')
    md_titles = []
    for idx, para in enumerate(paragraphs):
        m = heading_re.match(para)
        if m:
            level = len(m.group(1))
            title = m.group(2).strip()
            md_titles.append((title, idx, level))
    print(f"[align_titles_in_lines] 检测到 {len(md_titles)} 个MD标题")

    def flatten_titles(json_data, level=1):
        result = []
        for item in json_data:
            if isinstance(item, dict):
                title = item.get('title', '')
                if title:
                    result.append((title, level))
                if 'subtitles' in item:
                    result.extend(flatten_titles(item['subtitles'], level+1))
            elif isinstance(item, str):
                result.append((item, level))
        return result

    json_titles = flatten_titles(titles_json)
    json_title_texts = [t for t, _ in json_titles]
    json_title_levels = {t: l for t, l in json_titles}
    print(f"[align_titles_in_lines] JSON目录共 {len(json_title_texts)} 个标题")

    aligned = list(paragraphs)
    used_json_titles = set()

    for idx, (md_title, para_idx, md_level) in enumerate(md_titles):
        print(f"[align_titles_in_lines] Processing MD title: '{md_title}' (original level: {md_level})")
        # 清洗MD标题
        cleaned_md_title = clean_md_title(md_title)
        print(f"[align_titles_in_lines] 清洗后的MD标题: '{cleaned_md_title}'")
        
        # 首先检查清洗后的标题是否直接匹配
        if cleaned_md_title in json_title_texts:
            json_level = json_title_levels[cleaned_md_title]
            aligned[para_idx] = f"{'#'*json_level} {md_title}"
            used_json_titles.add(cleaned_md_title)
            print(f"[align_titles_in_lines] 完全匹配: '{md_title}' (清洗后: '{cleaned_md_title}') -> 层级 {json_level}")
        else:
            candidates = rapidfuzz_process.extract(cleaned_md_title, json_title_texts, scorer=fuzz.ratio, limit=3)
            print(f"[align_titles_in_lines] Top-3候选: {candidates}")
            prompt = f"""你是一个结构化文档标题对齐专家，你的任务是从给定的候选标题列表中，选择最符合目标文本上下文的标题。\n目标Markdown标题：{md_title}\n"""
            for i, (cand, score, _) in enumerate(candidates):
                prompt += f"候选{i+1}: {cand} (相似度: {score})\n"
            prompt += "\n只能从候选中选择一个，不要生成新标题。输出格式：选择：<你选的标题>"
            if api_key:
                print(f"[align_titles_in_lines] 调用DeepSeek R1进行候选选择...")
                # 这里暂时保持原有逻辑，如果需要也可以添加深度思考控制
                # 调用API并记录token使用情况
                llm_result, input_tokens, output_tokens = deepseek_api(prompt, api_key, system_prompt=SYSTEM_PROMPT_SELECT_TITLE)
                token_logger.log_api_call(input_tokens, output_tokens, f"标题选择-{token_logger.current_file}")
                print(f"[align_titles_in_lines] DeepSeek R1返回: {llm_result}")
                match = re.search(r'选择[:：]\s*(.+)', llm_result)
                if match:
                    llm_result = match.group(1).strip()
                else:
                    llm_result = llm_result.strip().split('\n')[0]
            else:
                llm_result = candidates[0][0]
            if llm_result in json_title_levels:
                json_level = json_title_levels[llm_result]
                aligned[para_idx] = f"{'#'*json_level} {llm_result}"
                used_json_titles.add(llm_result)
                print(f"[align_titles_in_lines] DeepSeek R1选择: '{llm_result}' -> 层级 {json_level}")
            else:
                print(f"[align_titles_in_lines] DeepSeek R1未返回有效标题，保持原样")
    print("[align_titles_in_lines] Title alignment completed.\n")
    return aligned

def align_titles_in_paragraphs(paragraphs, titles_json, api_key=None):
    return align_titles_in_lines(paragraphs, titles_json, api_key=api_key)

def find_grouped_files(base_path):
    """查找所有grouped.md文件"""
    base_path = Path(base_path)
    grouped_files = []
    
    # 递归查找所有grouped.md文件
    for md_file in base_path.rglob("grouped.md"):
        grouped_files.append(md_file)
    
    return grouped_files

def batch_process_align_titles(base_path: str, api_key: str):
    """批量处理所有grouped.md文件"""
    base_path = Path(base_path)
    
    print(f"🚀 Starting batch title alignment processing...")
    print(f"📁 基础目录: {base_path}")
    print(f"🔑 API密钥: {api_key[:10]}...")
    print("=" * 80)
    
    # 初始化token日志记录（如果已经初始化过则不会重复创建文件）
    global token_logger
    token_logger = TokenLogger()
    
    # Find all grouped.md files
    grouped_files = find_grouped_files(base_path)
    
    if not grouped_files:
        print("❌ 未找到任何grouped.md文件")
        print("请检查目录路径和文件命名规则（grouped.md）")
        return
    
    print(f"📄 找到 {len(grouped_files)} 个grouped.md文件")
    print("=" * 80)
    
    # Statistics for processing results
    total_files = len(grouped_files)
    successful_files = 0
    failed_files = 0
    
    # 逐个处理文件
    for i, grouped_file in enumerate(grouped_files, 1):
        print(f"\n📋 Processing progress: {i}/{total_files}")
        print(f"📄 文件: {grouped_file.name}")
        print(f"📁 目录: {grouped_file.parent}")
        
        try:
            # 记录当前处理的文件
            file_relative_path = str(grouped_file.relative_to(base_path))
            token_logger.log_file_start(file_relative_path)
            
            # Find corresponding titles.json file
            titles_json_path = grouped_file.parent / "titles.json"
            
            if not titles_json_path.exists():
                print(f"❌ 未找到对应的titles.json文件: {titles_json_path}")
                failed_files += 1
                continue
            
            # Build output file path
            output_md_path = grouped_file.parent / "markdown_aligned.md"
            
            print(f"🔧 Starting to process: {grouped_file.name}")
            print(f"📋 目录结构: {titles_json_path.name}")
            print(f"📤 输出文件: {output_md_path.name}")
            
            # Read input files
            with open(grouped_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Read directory structure
            with open(titles_json_path, 'r', encoding='utf-8') as f:
                titles_json = json.load(f)
            
            print(f"📊 文件统计:")
            print(f"   - Markdown内容: {len(content)} 字符")
            print(f"   - 目录标题数: {len(titles_json)} 个")
            
            # Execute title alignment
            print("🔄 Executing title alignment (exact + fuzzy matching)...")
            success, unmatched_titles = align_titles(content, str(titles_json_path), str(output_md_path))
            
            if success:
                print("✅ 标题对齐完成")
                
                # 处理未匹配的标题
                if unmatched_titles:
                    print(f"🔍 Found {len(unmatched_titles)} unmatched titles, starting intelligent insertion...")
                    process_unmatched_titles(str(output_md_path), unmatched_titles, titles_json, api_key)
                    print("✅ Unmatched title processing completed")
                else:
                    print("✅ All titles matched, no additional processing needed")
                
                successful_files += 1
                print(f"✅ {grouped_file.name} processing completed!")
                
            else:
                print(f"❌ {grouped_file.name} title alignment failed")
                failed_files += 1
                
        except FileNotFoundError as e:
            print(f"❌ File not found: {e}")
            failed_files += 1
        except PermissionError as e:
            print(f"❌ Permission error: {e}")
            failed_files += 1
        except json.JSONDecodeError as e:
            print(f"❌ JSON format error: {e}")
            failed_files += 1
        except Exception as e:
            print(f"❌ Processing failed: {e}")
            import traceback
            print(f"Error details:\n{traceback.format_exc()}")
            failed_files += 1
    
    # Display final statistics
    print("\n" + "=" * 80)
    print("📊 Batch processing completed!")
    print(f"📄 Total files: {total_files}")
    print(f"✅ Successfully processed: {successful_files}")
    print(f"❌ Processing failed: {failed_files}")
    print(f"📈 Success rate: {successful_files/total_files*100:.1f}%")
    
    # Record token usage summary
    token_logger.log_summary()
    print(f"📊 Token usage statistics:")
    print(f"   - Total input tokens: {token_logger.total_input_tokens}")
    print(f"   - Total output tokens: {token_logger.total_output_tokens}")
    print(f"   - Total consumed tokens: {token_logger.total_input_tokens + token_logger.total_output_tokens}")
    print(f"   - Detailed log saved to: {token_logger.log_file}")
    
    print(f"\n📁 All output files have been saved to their respective subfolders (markdown_aligned.md)")

def main():
    print("[main] Starting main process...")
    
    # Hard-coded input folder path
    BASE_PATH = r"E:\US_Preprocess\yhr\2001-2500\ESGdata\ESGdata\success"
    API_KEY = "3f5bbaf1-6d3a-4a21-92db-db1aa317915e"
    
    # Batch processing
    batch_process_align_titles(BASE_PATH, API_KEY)
    
    print("[main] Main process completed.\n")

if __name__ == '__main__':
    main()
