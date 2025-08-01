"""
结构增强模块核心处理器

包含：
- TitleExtractor: 标题提取处理器
- PageGrouper: 页面分组处理器  
- TitleAligner: 标题对齐处理器
- StructureEnhancer: 结构优化处理器
"""

import json
import re
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict

from .config import StructureEnhancementConfig
from .utils import (
    setup_logging, 
    timing_context, 
    safe_file_operation,
    backup_file,
    ProcessingStats,
    normalize_title,
    is_title_match,
    parse_page_index,
    is_table_line,
    get_title_level_from_markdown,
    format_title_with_level
)
from .api_clients import create_api_client


class BaseProcessor(ABC):
    """处理器基类"""
    
    def __init__(self, config: StructureEnhancementConfig):
        self.config = config
        self.logger = setup_logging(
            config.log_level, 
            config.log_file_path if config.log_to_file else None,
            f"structure_enhancement.{self.__class__.__name__}"
        )
        self.stats = ProcessingStats()
    
    @abstractmethod
    def process(self, *args, **kwargs) -> Dict[str, Any]:
        """处理方法的抽象接口"""
        pass
    
    def get_stats(self) -> Dict[str, Any]:
        """获取处理统计信息"""
        return self.stats.to_dict()


class TitleExtractor(BaseProcessor):
    """标题提取处理器"""
    
    def __init__(self, config: StructureEnhancementConfig):
        super().__init__(config)
        self.qwen_client = create_api_client("qwen", config.get_api_config("qwen"), self.logger)
        self.extraction_config = config.get_title_extraction_config()
    
    def process(self, image_path: str, output_json_path: Optional[str] = None) -> Dict[str, Any]:
        """从图片中提取标题结构"""
        self.stats.reset()
        
        with timing_context(self.logger, "标题提取"):
            try:
                if not Path(image_path).exists():
                    raise FileNotFoundError(f"图片文件不存在: {image_path}")
                
                self.logger.info(f"开始提取标题: {image_path}")
                
                # 调用API提取标题
                result_text = self.qwen_client.extract_titles_from_image(
                    image_path=image_path,
                    sample_base64_files=self.extraction_config["sample_base64_files"],
                    max_tokens=self.extraction_config["max_tokens"],
                    temperature=self.extraction_config["temperature"],
                    top_p=self.extraction_config["top_p"]
                )
                
                if not result_text:
                    raise Exception("API返回空结果")
                
                # 显示LLM输出结果（调试用）
                self.logger.info("=== LLM输出结果 ===")
                self.logger.info(result_text)
                self.logger.info("=" * 30)
                
                # 解析提取结果
                titles_data = self._parse_extraction_result(result_text)
                
                # 保存结果
                if output_json_path:
                    self._save_titles_json(titles_data, output_json_path)
                
                self.stats.add_success()
                self.stats.finish()
                
                return {
                    "success": True,
                    "titles_data": titles_data,
                    "output_path": output_json_path,
                    "stats": self.stats.to_dict()
                }
                
            except Exception as e:
                self.logger.error(f"标题提取失败: {e}")
                self.stats.add_failure(str(e))
                self.stats.finish()
                
                return {
                    "success": False,
                    "error": str(e),
                    "stats": self.stats.to_dict()
                }
    
    def _parse_extraction_result(self, result_text: str) -> List[Dict]:
        """解析API返回的标题提取结果"""
        try:
            # 清理响应文本
            cleaned_text = result_text.strip()
            
            # 尝试找到JSON部分
            json_start = cleaned_text.find('[')
            json_end = cleaned_text.rfind(']') + 1
            
            if json_start != -1 and json_end > json_start:
                json_text = cleaned_text[json_start:json_end]
                return json.loads(json_text)
            else:
                # 如果没有找到JSON，尝试解析文本格式
                return self._parse_text_format(cleaned_text)
                
        except json.JSONDecodeError as e:
            self.logger.warning(f"JSON解析失败，尝试文本解析: {e}")
            return self._parse_text_format(result_text)
    
    def _parse_text_format(self, text: str) -> List[Dict]:
        """解析文本格式的标题结构"""
        # 使用与extract_title.py相同的解析逻辑
        self.logger.info("使用文本格式解析标题结构")
        
        # 找到"### 最终输出结果"的位置
        start_marker = "### 最终输出结果"
        start_index = text.find(start_marker)
        
        if start_index == -1:
            self.logger.error("未找到'### 最终输出结果'标记")
            return []
        
        # 获取标记后的内容
        content = text[start_index + len(start_marker):].strip()
        
        lines = content.splitlines()
        result = []
        current_h1 = None
        current_h2 = None
        
        for line in lines:
            line = line.strip('\r\n')
            if not line.strip():
                continue
                
            # 判断是否为一级标题（无缩进且不以特殊符号开头）
            if not line.startswith('    ') and not line.startswith('-') and not line.startswith('·') and not line.startswith('•'):
                # 如果已经有标题在处理中，保存它
                if current_h1:
                    result.append(current_h1)
                # 开始新的一级标题
                current_h1 = {"title": line.strip()}
                current_h2 = None
            # 判断是否为二级标题（缩进4个空格）
            elif line.startswith('    ') and not line.startswith('        '):
                if current_h1:
                    # 如果一级标题还没有subtitles字段，创建它
                    if "subtitles" not in current_h1:
                        current_h1["subtitles"] = []
                    # 开始新的二级标题
                    current_h2 = {"title": line.lstrip('    ').strip()}
                    current_h1["subtitles"].append(current_h2)
            # 判断是否为三级标题（缩进8个空格）
            elif line.startswith('        '):
                if current_h2:
                    # 如果二级标题还没有subtitles字段，创建它
                    if "subtitles" not in current_h2:
                        current_h2["subtitles"] = []
                    # 添加三级标题
                    current_h2["subtitles"].append(line.lstrip('        ').strip())
        
        # 保存最后一个标题
        if current_h1:
            result.append(current_h1)
        
        self.logger.info(f"成功解析文本格式，提取到 {len(result)} 个一级标题")
        return result
    
    def _save_titles_json(self, titles_data: List[Dict], output_path: str):
        """保存标题JSON文件"""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(titles_data, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"标题JSON已保存: {output_path}")


class PageGrouper(BaseProcessor):
    """页面分组处理器"""
    
    def __init__(self, config: StructureEnhancementConfig):
        super().__init__(config)
        self.grouping_config = config.get_page_grouping_config()
    
    def process(self, input_md_path: str, output_md_path: Optional[str] = None) -> Dict[str, Any]:
        """按页面索引重新组织Markdown内容"""
        self.stats.reset()
        
        with timing_context(self.logger, "页面分组"):
            try:
                # 读取输入文件
                with open(input_md_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                self.logger.info(f"开始页面分组: {input_md_path}")
                
                # 按页面索引分组
                grouped_content = self._group_by_page_index(lines)
                
                # 生成输出内容
                output_content = self._format_grouped_content(grouped_content)
                
                # 保存结果
                if output_md_path:
                    with open(output_md_path, 'w', encoding='utf-8') as f:
                        f.write(output_content)
                    self.logger.info(f"分组结果已保存: {output_md_path}")
                
                self.stats.add_success()
                self.stats.finish()
                
                return {
                    "success": True,
                    "output_content": output_content,
                    "output_path": output_md_path,
                    "page_count": len(grouped_content),
                    "stats": self.stats.to_dict()
                }
                
            except Exception as e:
                self.logger.error(f"页面分组失败: {e}")
                self.stats.add_failure(str(e))
                self.stats.finish()
                
                return {
                    "success": False,
                    "error": str(e),
                    "stats": self.stats.to_dict()
                }
    
    def _group_by_page_index(self, lines: List[str]) -> Dict[str, List[str]]:
        """按页面索引分组内容"""
        pattern = self.grouping_config["page_idx_pattern"]
        grouped = defaultdict(list)
        current_idx = None
        
        for line in lines:
            line = line.rstrip()
            page_idx = parse_page_index(line, pattern)
            
            if page_idx is not None:
                current_idx = str(page_idx)
            else:
                if current_idx is not None:
                    grouped[current_idx].append(line)
        
        return dict(grouped)
    
    def _format_grouped_content(self, grouped_content: Dict[str, List[str]]) -> str:
        """格式化分组后的内容"""
        output_lines = []
        sorted_indices = sorted(grouped_content.keys(), key=lambda x: int(x))
        
        for i, idx in enumerate(sorted_indices):
            content_lines = [l for l in grouped_content[idx] if l.strip()]
            
            # 添加页面索引标记
            output_lines.append(f'<page_idx:{idx}>')
            output_lines.append('[')
            output_lines.append('')  # 在[后加空行
            
            # 添加内容行
            for j, line in enumerate(content_lines):
                output_lines.append(line)
                
                # 智能空行处理
                if self._should_add_empty_line(line, content_lines, j):
                    output_lines.append('')
            
            output_lines.append('')  # 在]前加空行
            output_lines.append(']')
            
            # 分组间空行
            if i < len(sorted_indices) - 1:
                output_lines.append('')
        
        return '\n'.join(output_lines)
    
    def _should_add_empty_line(self, current_line: str, all_lines: List[str], index: int) -> bool:
        """判断是否应该添加空行"""
        if index == len(all_lines) - 1:  # 最后一行
            return False
        
        # 检查图片-表格关系
        if (current_line.strip().startswith('![') and 
            index + 1 < len(all_lines) and
            self.grouping_config["table_detection_enabled"] and
            is_table_line(all_lines[index + 1], self.grouping_config["table_patterns"])):
            return False  # 图片后紧跟表格，不加空行
        
        return True


class TitleAligner(BaseProcessor):
    """标题对齐处理器"""
    
    def __init__(self, config: StructureEnhancementConfig):
        super().__init__(config)
        self.alignment_config = config.get_title_alignment_config()
        
        # 初始化API客户端（如果启用LLM匹配）
        self.deepseek_client = None
        if self.alignment_config["use_llm_matching"]:
            try:
                self.deepseek_client = create_api_client(
                    "deepseek", 
                    config.get_api_config("deepseek"), 
                    self.logger
                )
            except Exception as e:
                self.logger.warning(f"DeepSeek客户端初始化失败，将使用规则匹配: {e}")
    
    def process(self, md_content: str, titles_json_path: str, 
                output_md_path: Optional[str] = None) -> Dict[str, Any]:
        """执行标题对齐处理"""
        self.stats.reset()
        
        with timing_context(self.logger, "标题对齐"):
            try:
                # 处理输入内容
                if isinstance(md_content, str) and Path(md_content).exists():
                    # 如果是文件路径
                    with open(md_content, 'r', encoding='utf-8') as f:
                        content = f.read()
                else:
                    # 如果是内容字符串
                    content = md_content
                
                # 加载标题JSON
                with open(titles_json_path, 'r', encoding='utf-8') as f:
                    titles_json = json.load(f)
                
                self.logger.info("开始标题对齐处理")
                
                # 执行对齐处理
                aligned_content, unmatched_titles = self._align_titles(content, titles_json)
                
                # 处理未匹配的标题
                if unmatched_titles and self.alignment_config["auto_insert_missing"]:
                    aligned_content = self._process_unmatched_titles(
                        aligned_content, unmatched_titles, titles_json
                    )
                
                # 保存结果
                if output_md_path:
                    # 备份原文件
                    if Path(output_md_path).exists():
                        backup_file(output_md_path)
                    
                    with open(output_md_path, 'w', encoding='utf-8') as f:
                        f.write(aligned_content)
                    self.logger.info(f"对齐结果已保存: {output_md_path}")
                
                self.stats.add_success()
                self.stats.finish()
                
                return {
                    "success": True,
                    "aligned_content": aligned_content,
                    "output_path": output_md_path,
                    "unmatched_count": len(unmatched_titles),
                    "stats": self.stats.to_dict()
                }
                
            except Exception as e:
                self.logger.error(f"标题对齐失败: {e}")
                self.stats.add_failure(str(e))
                self.stats.finish()
                
                return {
                    "success": False,
                    "error": str(e),
                    "stats": self.stats.to_dict()
                }
    
    def _align_titles(self, content: str, titles_json: List[Dict]) -> Tuple[str, List[Tuple]]:
        """执行标题对齐"""
        lines = content.split('\n')
        
        # 提取现有标题
        md_titles = self._extract_markdown_titles(lines)
        
        # 处理JSON标题
        json_titles = self._process_json_titles(titles_json)
        
        # 执行匹配
        matched_titles = []
        unmatched_titles = []
        
        for json_title, level, orig_idx, parent in json_titles:
            match_result = self._find_best_match(json_title, md_titles, level)
            
            if match_result:
                matched_titles.append((json_title, level, match_result))
            else:
                unmatched_titles.append((json_title, level, orig_idx, parent, "", ""))
        
        # 应用匹配结果
        aligned_lines = self._apply_title_alignments(lines, matched_titles)
        
        return '\n'.join(aligned_lines), unmatched_titles
    
    def _extract_markdown_titles(self, lines: List[str]) -> List[Tuple[str, int, int]]:
        """提取Markdown中的标题"""
        titles = []
        for i, line in enumerate(lines):
            level = get_title_level_from_markdown(line)
            if level > 0:
                title_text = line.strip().lstrip('#').strip()
                titles.append((title_text, i, level))
        return titles
    
    def _process_json_titles(self, titles_json: List[Dict]) -> List[Tuple[str, int, int, str]]:
        """处理JSON标题，返回(标题, 层级, 原始索引, 父标题)的列表"""
        result = []
        
        def process_entry(entry, index: int, parent: str = None, parent_level: int = 0, 
                         is_top_level: bool = False, is_in_third_level: bool = False):
            if isinstance(entry, str):
                # 字符串类型的标题
                level = self._determine_string_title_level(parent_level, is_in_third_level)
                result.append((entry, level, index, parent))
                return
            
            title = entry.get('title', '')
            if not title:
                return
            
            # 获取当前标题的层级
            level = self._determine_title_level(entry, is_top_level, parent_level, is_in_third_level)
            result.append((title, level, index, parent))
            
            # 处理子标题
            if 'subtitles' in entry:
                is_third_level = level == 2
                
                for sub in entry['subtitles']:
                    if isinstance(sub, str):
                        sub_level = self._determine_string_title_level(level, is_third_level)
                        result.append((sub, sub_level, index, title))
                    else:
                        process_entry(sub, index, title, level, False, is_third_level)
        
        # 处理所有顶级标题
        for i, entry in enumerate(titles_json):
            process_entry(entry, i, None, 0, True, False)
        
        return result
    
    def _determine_title_level(self, entry: Dict, is_top_level: bool, 
                              parent_level: int, is_in_third_level: bool) -> int:
        """确定标题层级"""
        if is_in_third_level:
            return 3
        
        if is_top_level:
            return 1
        
        if 'subtitles' in entry:
            first_subtitle = entry['subtitles'][0] if entry['subtitles'] else None
            if isinstance(first_subtitle, str):
                return 2
            elif isinstance(first_subtitle, dict) and 'subtitles' in first_subtitle:
                return 2
        
        # 根据父层级判断
        level_map = {0: 1, 1: 2, 2: 3, 3: 4}
        return level_map.get(parent_level, 4)
    
    def _determine_string_title_level(self, parent_level: int, is_in_third_level: bool) -> int:
        """确定字符串标题的层级"""
        if is_in_third_level:
            return 3
        
        level_map = {1: 3, 2: 3, 3: 4}
        return level_map.get(parent_level, 4)
    
    def _find_best_match(self, json_title: str, md_titles: List[Tuple], target_level: int) -> Optional[Tuple]:
        """找到最佳匹配的标题"""
        best_match = None
        best_score = 0.0
        
        for md_title, line_num, level in md_titles:
            is_match, score, is_exact = is_title_match(
                md_title, json_title, self.alignment_config["similarity_threshold"]
            )
            
            if is_match and score > best_score:
                best_score = score
                best_match = (md_title, line_num, level)
        
        # 如果启用了LLM匹配且没有找到好的匹配
        if (not best_match and self.deepseek_client and 
            self.alignment_config["use_llm_matching"]):
            candidates = [title for title, _, _ in md_titles]
            if candidates:
                selected = self.deepseek_client.select_title(
                    f"目标标题: {json_title}", candidates
                )
                if selected:
                    for md_title, line_num, level in md_titles:
                        if md_title == selected:
                            best_match = (md_title, line_num, level)
                            break
        
        return best_match
    
    def _apply_title_alignments(self, lines: List[str], matched_titles: List[Tuple]) -> List[str]:
        """应用标题对齐结果"""
        # 这里实现标题对齐的具体逻辑
        # 根据匹配结果调整标题格式和层级
        aligned_lines = lines.copy()
        
        for json_title, target_level, (md_title, line_num, current_level) in matched_titles:
            if target_level != current_level:
                # 调整标题层级
                new_title = format_title_with_level(md_title, target_level)
                aligned_lines[line_num] = new_title
                self.logger.debug(f"调整标题层级: {md_title} ({current_level} -> {target_level})")
        
        return aligned_lines
    
    def _process_unmatched_titles(self, content: str, unmatched_titles: List[Tuple], 
                                 titles_json: List[Dict]) -> str:
        """处理未匹配的标题"""
        if not self.deepseek_client:
            self.logger.warning("未配置DeepSeek客户端，跳过未匹配标题处理")
            return content
        
        lines = content.split('\n')
        
        for title, level, orig_idx, parent, _, _ in unmatched_titles:
            # 使用LLM分析插入位置
            insert_position = self.deepseek_client.find_insert_position(content, title)
            
            if insert_position and 0 <= insert_position < len(lines):
                # 插入标题
                new_title = format_title_with_level(title, level)
                lines.insert(insert_position, new_title)
                self.logger.info(f"插入缺失标题: {title} (位置: {insert_position})")
        
        return '\n'.join(lines)


class StructureEnhancer(BaseProcessor):
    """结构优化处理器"""
    
    def __init__(self, config: StructureEnhancementConfig):
        super().__init__(config)
        self.title_extractor = TitleExtractor(config)
        self.page_grouper = PageGrouper(config)
        self.title_aligner = TitleAligner(config)
    
    def process(self, input_md_path: str, titles_json_path: Optional[str] = None,
                output_dir: Optional[str] = None) -> Dict[str, Any]:
        """执行完整的结构增强流程"""
        self.stats.reset()
        
        with timing_context(self.logger, "结构增强"):
            try:
                results = {}
                
                # 1. 页面分组
                grouped_result = self.page_grouper.process(
                    input_md_path,
                    os.path.join(output_dir, "grouped.md") if output_dir else None
                )
                results["page_grouping"] = grouped_result
                
                # 2. 标题对齐（如果提供了标题JSON）
                if titles_json_path and Path(titles_json_path).exists():
                    aligned_result = self.title_aligner.process(
                        grouped_result["output_content"],
                        titles_json_path,
                        os.path.join(output_dir, "aligned.md") if output_dir else None
                    )
                    results["title_alignment"] = aligned_result
                
                self.stats.add_success()
                self.stats.finish()
                
                return {
                    "success": True,
                    "results": results,
                    "stats": self.stats.to_dict()
                }
                
            except Exception as e:
                self.logger.error(f"结构增强失败: {e}")
                self.stats.add_failure(str(e))
                self.stats.finish()
                
                return {
                    "success": False,
                    "error": str(e),
                    "stats": self.stats.to_dict()
                } 