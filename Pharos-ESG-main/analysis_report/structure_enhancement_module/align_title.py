# -*- coding: utf-8 -*-

"""
Markdown标题对齐与格式化工具

功能描述：
    将Markdown文件中的标题结构与PDF目录结构进行对齐，确保标题的完整性和正确性。

主要功能：
1. 标题对齐
   - 确保所有在PDF目录中定义的标题都存在于Markdown文件中
   - 按照PDF目录的顺序排列标题
   - 自动补充缺失的主标题和子标题

2. 标题格式化
   - 主标题统一格式化为 "# Title"
   - 子标题统一格式化为 "## Subtitle"
   - 未对齐的标题转换为 "### Subtitle"

3. 标题匹配
   - 支持标题文本的模糊匹配（忽略空格差异）
   - 保持标题的原始格式和大小写

输入文件：
    - pdf_titles.json: PDF目录结构文件
    - markdown2_cleaned.md: 待处理的Markdown文件

输出文件：
    - markdown_aligned.md: 处理后的Markdown文件

注意事项：
    - 保持文档非标题内容不变
    - 保持标题的层级结构
    - 确保标题插入位置的合理性
"""

import json
import re
import os
from rapidfuzz import fuzz, process as rapidfuzz_process
from typing import List, Dict, Tuple, Set
from .deepseek_title import deepseek_api, SYSTEM_PROMPT_SELECT_TITLE, SYSTEM_PROMPT_INSERT_POSITION
from pathlib import Path

def extract_chinese(text: str) -> str:
    """提取文本中的中文字符"""
    return ''.join(char for char in text if '\u4e00' <= char <= '\u9fff')

def normalize_title(title: str) -> str:
    """标准化标题文本，只保留中文字符并移除空白"""
    # 只提取中文字符
    chinese_only = extract_chinese(title)
    # 移除所有空白字符
    return re.sub(r'\s+', '', chinese_only)

def get_title_level(entry: dict, is_top_level: bool = False, parent_level: int = 0, is_in_third_level: bool = False) -> Tuple[int, str]:
    """根据JSON结构确定标题层级和父标题
    Args:
        entry: JSON标题条目
        is_top_level: 是否是顶级标题（JSON数组中的直接元素）
        parent_level: 父标题的层级
        is_in_third_level: 是否在第三层subtitles中
    Returns:
        Tuple[int, str]: (层级, 父标题)
        
    规则：
    1. 顶级标题（JSON数组中的直接元素）为一级标题 (#)
    2. 二级嵌套：
       - 在subtitles中的title为二级标题 (##)
    3. 三级嵌套：
       - 在subtitles的subtitles中的字符串为三级标题 (###)
    4. 四级标题：
       - 三级标题下的标题为四级标题 (####)
    """
    # 如果是在第三层subtitles中的标题，直接返回三级标题
    if is_in_third_level:
        return (3, None)
        
    if not isinstance(entry, dict):
        # 字符串类型的标题
        if parent_level == 1:
            return (3, None)  # 一级标题下的字符串为三级标题
        elif parent_level == 2:
            return (3, None)  # 二级标题下的字符串为三级标题
        elif parent_level == 3:
            return (4, None)  # 三级标题下的字符串为四级标题
        return (4, None)  # 其他情况为四级标题
        
    title = entry.get('title', '')
    if not title:
        return (1, None)
        
    # 顶级标题（JSON数组中的直接元素）始终为一级标题
    if is_top_level:
        return (1, None)
        
    # 根据父层级和subtitles结构判断
    if 'subtitles' in entry:
        # 检查subtitles的第一个元素类型
        first_subtitle = entry['subtitles'][0]
        if isinstance(first_subtitle, str):
            # 如果subtitles中是字符串，说明这是二级标题
            return (2, None)
        elif isinstance(first_subtitle, dict) and 'subtitles' in first_subtitle:
            # 如果subtitles中的元素还有subtitles，说明这是二级标题
            return (2, None)
            
    # 根据父层级判断
    if parent_level == 1:
        return (2, None)  # 一级标题下的标题为二级标题
    elif parent_level == 2:
        return (3, None)  # 二级标题下的标题为三级标题
    elif parent_level == 3:
        return (4, None)  # 三级标题下的标题为四级标题
        
    return (4, None)  # 默认情况为四级标题

def is_title_match(md_title: str, json_title: str) -> Tuple[bool, float, bool]:
    """判断两个标题是否匹配，返回(是否匹配, 相似度, 是否完全匹配)
    匹配优先级：
    1. 完全匹配（包括中文部分完全匹配）
    2. 模糊匹配（使用rapidfuzz）
    3. 包含关系
    """
    # 提取中文部分
    md_chinese = extract_chinese(md_title)
    json_chinese = extract_chinese(json_title)
    
    # 1. 完全匹配
    if md_title == json_title:
        return True, 1.0, True
    if md_chinese == json_chinese:
        return True, 1.0, True
        
    # 2. 模糊匹配
    similarity = fuzz.ratio(md_chinese, json_chinese) / 100.0
    if similarity >= 0.8:
        return True, similarity, False
        
    # 3. 包含关系
    if json_chinese in md_chinese:
        return True, 0.9, False
        
    return False, 0.0, False

def process_json_titles(titles_json: List) -> List[Tuple[str, int, int, str]]:
    """处理JSON标题，返回(标题, 层级, 原始索引, 父标题)的列表"""
    result = []
    
    def process_entry(entry: dict, index: int, parent: str = None, parent_level: int = 0, is_top_level: bool = False, is_in_third_level: bool = False):
        if isinstance(entry, str):
            # 根据父层级和是否在第三层确定字符串标题的层级
            level, _ = get_title_level(entry, is_top_level, parent_level, is_in_third_level)
            result.append((entry, level, index, parent))
            return
            
        title = entry.get('title', '')
        if not title:
            return
            
        # 获取当前标题的层级
        level, _ = get_title_level(entry, is_top_level, parent_level, is_in_third_level)
        result.append((title, level, index, parent))
        
        # 处理子标题
        if 'subtitles' in entry:
            # 检查是否在第三层
            # 如果当前是二级标题，那么它的subtitles中的字符串就是三级标题
            is_third_level = level == 2
            
            for sub in entry['subtitles']:
                if isinstance(sub, str):
                    # 字符串类型的子标题，根据当前层级和是否在第三层确定其层级
                    sub_level, _ = get_title_level(sub, False, level, is_third_level)
                    result.append((sub, sub_level, index, title))
                else:
                    # 递归处理子标题，非顶级
                    process_entry(sub, index, title, level, False, is_third_level)
    
    # 处理所有标题
    for i, entry in enumerate(titles_json):
        # 处理顶级标题
        process_entry(entry, i, None, 0, True, False)
        # 打印每个标题的层级信息，用于调试
        level, _ = get_title_level(entry, True)
        print(f"JSON标题: '{entry.get('title', '')}' -> 层级: {level} (顶级标题)")
    
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
        print("警告：md_titles列表为空")
        return -1, 0.0, -1
    
    # 找到开始和结束的行号
    start_line = 0
    end_line = len(md_titles) - 1  # 使用列表长度作为默认结束位置
    
    print(f"\n开始匹配标题: '{target_title}' (目标层级: {level})")
    print(f"搜索范围：从标题 '{start_title}' 到 '{end_title}'")
    
    # 找到开始标题的行号（目标标题在JSON中的前一个标题）
    if start_title:
        for md_title, line_num, _ in md_titles:
            if is_title_match(md_title, start_title)[0]:
                start_line = line_num  # 从当前行开始搜索
                print(f"找到起始标题 '{start_title}' 在行号: {line_num}")
                break
    
    # 找到结束标题的行号（目标标题在JSON中的后一个标题）
    if end_title:
        for md_title, line_num, _ in md_titles:
            if is_title_match(md_title, end_title)[0]:
                end_line = line_num - 1  # 到前一行结束搜索
                print(f"找到结束标题 '{end_title}' 在行号: {line_num}")
                break
    
    print(f"实际搜索范围：行号 {start_line} 到 {end_line}")
    
    # 直接使用完整的目标标题
    print(f"目标标题: '{target_title}'")
    
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
        print(f"处理后的JSON标题数量: {len(json_titles)}")
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
                # 完全一致/中文一致
                if md_title == json_title or extract_chinese(md_title) == extract_chinese(json_title):
                    processed_lines[md_line] = f"{'#'*json_level} {md_title}\n"
                    matched_md_idx.add(md_line)
                    matched_json_idx.add(j)
                    json2md[j] = md_line
                    md2json[md_line] = j
                    md_ptr = m + 1
                    print(f"精确匹配: MD标题 '{md_title}' -> JSON标题 '{json_title}' (层级: {json_level})")
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
                print(f"模糊匹配: MD标题 '{md_title}' -> JSON标题 '{json_title}' (层级: {json_level}, 相似度: {best_sim:.2f})")
                continue
            # 3. 未匹配，记录前后json标题
            prev_title = json_titles[j-1][0] if j > 0 else None
            next_title = json_titles[j+1][0] if j < len(json_titles)-1 else None
            unmatched_titles.append((json_title, json_level, json_index, parent, prev_title, next_title))
            print(f"未匹配: JSON标题 '{json_title}' (层级: {json_level})")
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
        print(f"处理文件时出错: {str(e)}")
        import traceback
        print(f"错误详情:\n{traceback.format_exc()}")
        return False, []

def insert_title_at_line(lines: List[str], title: str, level: int, line_num: int):
    """在指定行号插入新标题"""
    new_title_line = f"{'#' * level} {title}\n"
    if 0 <= line_num <= len(lines):
        lines.insert(line_num, new_title_line)
        print(f"已将标题 '{title}' (层级 {level}) 插入到行号 {line_num + 1}")
    else:
        print(f"警告：无效的插入行号 {line_num + 1}，标题 '{title}' 未插入")

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
    """递归查找当前标题后的下一个标题
    Args:
        titles_json: JSON标题列表
        current_title: 当前标题
        depth: 递归深度，用于控制查找范围
    Returns:
        str: 找到的下一个标题，如果没找到则返回None
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
    
    try:
        current_index = all_titles.index(current_title)
        # 如果当前标题不是最后一个，返回下一个标题
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
    print(f"[parse_page_blocks] 解析完成，共 {len(page_blocks)} 个页块")
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
    print("[process_unmatched_titles] 开始处理未匹配标题...")
    try:
        print(f"[process_unmatched_titles] 未匹配标题总数: {len(unmatched_titles)}")
        title_idx = 0
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
            print(f"[process_unmatched_titles] 处理未匹配标题: '{json_title}' (层级: {json_level})")
            # 查找物理位置上下文
            prev_line = 0
            next_line = len(lines) - 1
            # 找到前一个标题的行号
            if prev_title:
                for md_title, line_num, _ in md_titles:
                    if extract_chinese(md_title) == extract_chinese(prev_title):
                        prev_line = line_num
                        break
            # 找到后一个标题的行号
            if next_title:
                for md_title, line_num, _ in md_titles:
                    if extract_chinese(md_title) == extract_chinese(next_title):
                        next_line = line_num
                        break
            # 自动扩展end_line，保证LLM能看到正文
            # 如果范围太小（如只覆盖1-2页），则扩展到文档结尾或多给几页
            all_page_blocks = parse_page_blocks(aligned_md_path)
            print(f"[process_unmatched_titles] 解析出 {len(all_page_blocks)} 个页块")
            # 统计范围内页数
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
                page_blocks_str = "\n".join([
                    f"{i+prev_line+1}. [RAW] {line.rstrip()}" for i, line in enumerate(raw_lines)
                ])
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
                        content_lines.append(f"{global_line_no+1}. {type_tag} {lines[global_line_no].rstrip()}" if found else f"?. {type_tag} {line.rstrip()}")
                    page_blocks_str += f"第{page_idx}页:\n" + "\n".join(content_lines) + "\n"

            # 打印本次搜索范围和前后标题行号
            print(f"[process_unmatched_titles] LLM搜索范围：全局行号 {prev_line} 到 {next_line}，严格页码范围 {strict_page_range} (prev_title='{prev_title}'@{prev_line}, next_title='{next_title}'@{next_line})")

            # 新prompt（覆盖和替换）
            prompt = f'''
你需要帮助我们判断一个标题应该插入在文档的哪个位置。

目标标题是："{json_title}" (层级: {json_level})

上下文信息：
    • 开始标题："{prev_title}"
    • 结束标题："{next_title}"

以下是该标题可插入的文档范围内容，已按页分块显示。每一页里包含原始的Markdown行，保留了所有的#、##、###层级标记，以及每行的行号。请仔细阅读：

{page_blocks_str}

【分析任务背景】
该未匹配标题出现在目录结构中“{prev_title}”和“{next_title}”之间。这个标题可能是为了“总揽”或“概括”这部分内容，也可能是为了补充具体“内容性”细节。

【分析步骤要求】
1️⃣ 先对提供的范围内容逐段逐行进行分析总结，标注所有标题和正文的主题点。
2️⃣ 评估该范围内容是否存在缺失的总揽性主题，目标标题能否作为此范围的总揽或概括标题。
3️⃣ 同时分析是否有需要在内容性细节里插入该标题的位置，使其与上下文紧密衔接。
4️⃣ 在两种角度（总揽性与内容性）都分析后，给出最合理的插入位置建议。

【输出格式要求】

✅ 你只能输出如下格式：
插入全局行号：<行号>
插入页码：<页码>
原因：<详细分析，包括对范围内容的总结、总揽性分析、内容性分析、最终决策理由>

🚫 如果在所有行都没有合适位置，请严格输出：
插入位置：无
原因：<详细说明为什么范围内没有任何位置适合作为插入点，并总结内容分析>

⚠️ 严禁输出页码+行号格式，只能输出"插入全局行号：<行号>"！否则会被判为无效答案。
'''
            print(f"[process_unmatched_titles] 调用DeepSeek R1判断插入位置...\nPrompt内容如下:\n{prompt}")
            response = deepseek_api(prompt, api_key, system_prompt=SYSTEM_PROMPT_INSERT_POSITION, use_r1=True)
            print(f"[process_unmatched_titles] DeepSeek R1返回: {response}")
            if not response:
                print("[process_unmatched_titles] API调用失败")
                title_idx += 1
                continue
            if "插入位置：无" in response:
                print(f"[process_unmatched_titles] 标题 '{json_title}' 未找到合适的插入位置")
                title_idx += 1
                continue
            # 只允许解析「插入全局行号：<行号>」
            global_line_match = re.search(r'插入全局行号[:：]\s*(\d+)', response)
            if global_line_match:
                global_line = int(global_line_match.group(1))
                if not (prev_line <= global_line <= next_line):
                    print(f"[process_unmatched_titles] DeepSeek R1返回的全局行号 {global_line} 不在允许范围 {prev_line}~{next_line}，将使用范围起点作为兜底插入位置。")
                    global_line = prev_line
                insert_title_at_line(lines, json_title, json_level, global_line)
                with open(aligned_md_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                print(f"已将标题 '{json_title}' (层级 {json_level}) 插入到行号 {global_line}")
            else:
                print(f"[process_unmatched_titles] DeepSeek R1输出格式不规范，未找到可用行号，将尝试在范围起点插入。")
                insert_title_at_line(lines, json_title, json_level, prev_line)
                with open(aligned_md_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                print(f"已将标题 '{json_title}' (层级 {json_level}) 作为总揽性标题插入到范围起点行号 {prev_line}")
            title_idx += 1
        print("[process_unmatched_titles] 所有未匹配标题处理完成。\n")
        return True
    except Exception as e:
        print(f"[process_unmatched_titles] 处理未匹配标题时出错: {str(e)}")
        import traceback
        print(f"[process_unmatched_titles] 错误详情:\n{traceback.format_exc()}")
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
        print(f"错误：未找到md_files目录: {md_files_dir}")
        return
    
    print(f"\n开始处理目录: {md_files_dir}")
    
    # 统计信息
    total_files = 0
    processed_files = 0
    failed_files = 0
    
    # 遍历所有子目录
    for report_dir in md_files_dir.iterdir():
        if report_dir.is_dir():
            # 检查目录名称格式
            parts = report_dir.name.split('_')
            if len(parts) < 3:  # 至少需要股票代码、公司名和报告名
                print(f"警告：目录名称格式不正确: {report_dir.name}")
                continue
                
            # 检查第一部分是否为日期（8位数字）
            is_date_format = len(parts[0]) == 8 and parts[0].isdigit()
            
            # 查找处理后的markdown文件和titles.json文件
            processed_md = next(report_dir.glob("*_without_toc_processed.md"), None)
            titles_json = next(report_dir.glob("titles.json"), None)
            
            if not processed_md or not titles_json:
                print(f"警告：在 {report_dir} 中未找到必要的文件")
                continue
            
            total_files += 1
            print(f"\n处理文件: {processed_md}")
            
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
                    # 处理未匹配的标题
                    if unmatched_titles:
                        process_unmatched_titles(str(output_md), unmatched_titles, titles, api_key)
                    processed_files += 1
                else:
                    failed_files += 1
                    
            except Exception as e:
                print(f"处理文件时出错: {str(e)}")
                failed_files += 1
                continue
    
    # 打印统计信息
    print(f"\n处理完成！统计信息:")
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
    print("[align_titles_in_lines] 开始对齐段落标题...")
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
        print(f"[align_titles_in_lines] 处理MD标题: '{md_title}' (原层级: {md_level})")
        if md_title in json_title_texts:
            json_level = json_title_levels[md_title]
            aligned[para_idx] = f"{'#'*json_level} {md_title}"
            used_json_titles.add(md_title)
            print(f"[align_titles_in_lines] 完全匹配: '{md_title}' -> 层级 {json_level}")
        else:
            candidates = rapidfuzz_process.extract(md_title, json_title_texts, scorer=fuzz.ratio, limit=3)
            print(f"[align_titles_in_lines] Top-3候选: {candidates}")
            prompt = f"""你是一个结构化文档标题对齐专家，你的任务是从给定的候选标题列表中，选择最符合目标文本上下文的标题。\n目标Markdown标题：{md_title}\n"""
            for i, (cand, score, _) in enumerate(candidates):
                prompt += f"候选{i+1}: {cand} (相似度: {score})\n"
            prompt += "\n只能从候选中选择一个，不要生成新标题。输出格式：选择：<你选的标题>"
            if api_key:
                print(f"[align_titles_in_lines] 调用DeepSeek R1进行候选选择...")
                llm_result = deepseek_api(prompt, api_key, system_prompt=SYSTEM_PROMPT_SELECT_TITLE, use_r1=True)
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
    print("[align_titles_in_lines] 标题对齐完成。\n")
    return aligned

def align_titles_in_paragraphs(paragraphs, titles_json, api_key=None):
    return align_titles_in_lines(paragraphs, titles_json, api_key=api_key)

def main():
    print("[main] 启动主流程...")
    input_md = '/Users/liucun/Desktop/yuancailiao/600801.SH-华新水泥-2024年华新水泥ESG报告/600801.SH-华新水泥-2024年华新水泥ESG报告_preprocessed.md'  # 输入md文件
    output_md = '/Users/liucun/Desktop/300573.SZ-兴齐眼药-2024年度环境,社会与治理(ESG)报告/markdown_aligned.md'   # 输出md文件
    titles_json_path = '/Users/liucun/Desktop/300573.SZ-兴齐眼药-2024年度环境,社会与治理(ESG)报告/titles.json'  # 目录结构json
    api_key = 'sk-igvmjaomyjwstzlsvtlktrpgsuqxdfqngaxizidcogdtgicu'

    print(f"[main] 读取输入MD: {input_md}")
    with open(input_md, 'r', encoding='utf-8') as f:
        content = f.read()

    print(f"[main] 读取目录结构: {titles_json_path}")
    with open(titles_json_path, 'r', encoding='utf-8') as f:
        titles_json = json.load(f)

    print("[main] 对整个MD做标题对齐（精确+模糊）...")
    success, unmatched_titles = align_titles(content, titles_json_path, output_md)

    if success:
        print("[main] 标题对齐完成，处理未匹配标题（智能插入）...")
        if unmatched_titles:
            process_unmatched_titles(output_md, unmatched_titles, titles_json, api_key)
        print(f"[main] 输出已写入: {output_md}")
    else:
        print("[main] 标题对齐失败！")
    print("[main] 主流程结束。\n")

if __name__ == '__main__':
    main()