"""
预处理器模块

包含三个主要处理器：
1. JsonToMarkdownProcessor - JSON转Markdown
2. ImageLinkConverter - 图片链接转换  
3. ImageTextDetector - 图片文本检测
"""

import json
import re
import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod

import pytesseract
from PIL import Image

from .config import PreprocessConfig
from .utils import safe_file_operation, get_file_stats, backup_file, timing_context


class BaseProcessor(ABC):
    """处理器基类"""
    
    def __init__(self, config: PreprocessConfig, logger: logging.Logger = None):
        self.config = config
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.stats = {
            "processed_files": 0,
            "successful_operations": 0,
            "failed_operations": 0,
            "errors": []
        }
    
    @abstractmethod
    def process(self, *args, **kwargs) -> Dict[str, Any]:
        """抽象处理方法"""
        pass
    
    def get_stats(self) -> Dict[str, Any]:
        """获取处理统计信息"""
        return self.stats.copy()
    
    def reset_stats(self):
        """重置统计信息"""
        self.stats = {
            "processed_files": 0,
            "successful_operations": 0,
            "failed_operations": 0,
            "errors": []
        }


class JsonToMarkdownProcessor(BaseProcessor):
    """JSON转Markdown处理器"""
    
    def __init__(self, config: PreprocessConfig, logger: logging.Logger = None):
        super().__init__(config, logger)
        self.logger.info("初始化JSON转Markdown处理器")
    
    @safe_file_operation("JSON转Markdown")
    def process(self, input_json_path: str, output_md_path: str) -> Dict[str, Any]:
        """
        将JSON文件转换为Markdown格式
        
        Args:
            input_json_path: 输入JSON文件路径
            output_md_path: 输出Markdown文件路径
        
        Returns:
            处理结果字典
        """
        with timing_context(self.logger, f"JSON转Markdown: {input_json_path}"):
            # 读取JSON文件
            with open(input_json_path, 'r', encoding='utf-8') as f:
                objs = json.load(f)
            
            # 转换为Markdown
            md_lines = self._convert_objects_to_markdown(objs)
            
            # 备份原文件（如果存在）
            if os.path.exists(output_md_path):
                backup_path = backup_file(output_md_path)
                if backup_path:
                    self.logger.info(f"已备份原文件: {backup_path}")
            
            # 写入Markdown文件
            with open(output_md_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(md_lines).strip() + '\n')
            
            # 更新统计信息
            self.stats["processed_files"] += 1
            self.stats["successful_operations"] += 1
            
            # 获取文件统计信息
            input_stats = get_file_stats(input_json_path)
            output_stats = get_file_stats(output_md_path)
            
            result = {
                "status": "success",
                "input_file": input_json_path,
                "output_file": output_md_path,
                "input_size_mb": input_stats.get("size_mb", 0),
                "output_size_mb": output_stats.get("size_mb", 0),
                "objects_processed": len(objs),
                "lines_generated": len(md_lines)
            }
            
            self.logger.info(f"转换完成: {len(objs)}个对象 -> {len(md_lines)}行Markdown")
            return result
    
    def _convert_objects_to_markdown(self, objs: List[Dict]) -> List[str]:
        """将对象列表转换为Markdown行"""
        md_lines = []
        
        for obj in objs:
            page_idx = obj.get('page_idx', '')
            prefix = f'<page_idx:{page_idx}>' if self.config.add_page_markers else ''
            
            if obj['type'] == 'image':
                if prefix:
                    md_lines.append(prefix)
                md_lines.append(f"{obj['img_path']}")
                md_lines.extend(['', ''])
                
            elif obj['type'] == 'table':
                if prefix:
                    md_lines.append(prefix)
                md_lines.append(f"{obj['img_path']}")
                
                table_body = obj.get('table_body', '').replace('\n', '').strip()
                if table_body:
                    if self.config.preserve_html_tables:
                        # 保留原始HTML格式
                        if prefix:
                            md_lines.append(prefix)
                        md_lines.append(table_body)
                    else:
                        # 转换为Markdown表格
                        md_table = self._html_table_to_markdown(table_body)
                        if md_table:
                            md_lines.append(md_table)
                
                md_lines.extend(['', ''])
                
            elif obj['type'] == 'text':
                text = obj.get('text', '').strip()
                text_level = obj.get('text_level')
                
                if prefix:
                    md_lines.append(prefix)
                
                if text_level:
                    md_lines.append(f"{'#' * text_level} {text}")
                else:
                    md_lines.append(text)
                
                md_lines.extend(['', ''])
        
        return md_lines
    
    def _html_table_to_markdown(self, html_table: str) -> str:
        """将HTML表格转换为Markdown表格"""
        try:
            # 提取表格行
            rows = re.findall(r'<tr>(.*?)</tr>', html_table, re.S)
            md_rows = []
            
            for i, row in enumerate(rows):
                # 提取单元格
                cells = re.findall(r'<t[dh]>(.*?)</t[dh]>', row, re.S)
                # 去除HTML标签和多余空白
                cells = [re.sub(r'<.*?>', '', cell).replace('\n', '').strip() for cell in cells]
                md_rows.append(' | '.join(cells))
            
            if not md_rows:
                return ''
            
            # 添加分隔行
            if len(md_rows) > 1:
                md_rows.insert(1, ' | '.join(['---'] * len(md_rows[0].split(' | '))))
            
            return '\n'.join(md_rows)
        except Exception as e:
            self.logger.warning(f"HTML表格转换失败: {e}")
            return html_table  # 返回原始HTML


class ImageLinkConverter(BaseProcessor):
    """图片链接转换处理器"""
    
    def __init__(self, config: PreprocessConfig, logger: logging.Logger = None):
        super().__init__(config, logger)
        self.logger.info("初始化图片链接转换处理器")
    
    @safe_file_operation("图片链接转换")
    def process(self, md_file_path: str, images_dir: str) -> Dict[str, Any]:
        """
        转换Markdown文件中的图片链接为标准格式
        
        Args:
            md_file_path: Markdown文件路径
            images_dir: 图片目录路径
        
        Returns:
            处理结果字典
        """
        with timing_context(self.logger, f"图片链接转换: {md_file_path}"):
            # 读取文件内容
            with open(md_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            lines = content.split('\n')
            new_lines = []
            converted_count = 0
            
            self.logger.info(f"开始处理文件: {md_file_path}")
            self.logger.info(f"图片目录: {images_dir}")
            
            # 处理每一行
            for line in lines:
                line = line.strip()
                
                # 检查是否为图片路径
                if self._is_image_path(line):
                    converted_line, converted = self._convert_image_line(line, images_dir)
                    new_lines.append(converted_line)
                    if converted:
                        converted_count += 1
                        self.logger.debug(f"转换: {line} -> {converted_line}")
                else:
                    new_lines.append(line)
            
            # 备份原文件
            backup_path = backup_file(md_file_path)
            if backup_path:
                self.logger.info(f"已备份原文件: {backup_path}")
            
            # 写回文件
            new_content = '\n'.join(new_lines)
            with open(md_file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            # 更新统计信息
            self.stats["processed_files"] += 1
            self.stats["successful_operations"] += converted_count
            
            result = {
                "status": "success",
                "file_path": md_file_path,
                "original_lines": len(lines),
                "processed_lines": len(new_lines),
                "converted_links": converted_count,
                "content_changed": original_content != new_content
            }
            
            self.logger.info(f"转换完成: {converted_count}个图片链接")
            return result
    
    def _is_image_path(self, line: str) -> bool:
        """检查是否为图片路径"""
        return ('_temp_images/' in line and 
                any(line.lower().endswith(ext) for ext in self.config.supported_image_extensions))
    
    def _convert_image_line(self, line: str, images_dir: str) -> tuple[str, bool]:
        """转换图片行"""
        filename = os.path.basename(line)
        full_image_path = Path(images_dir) / filename
        
        if self.config.validate_image_existence:
            if full_image_path.exists():
                return f"![]({line})", True
            else:
                self.logger.warning(f"图片文件不存在: {full_image_path}")
                return line, False
        else:
            return f"![]({line})", True


class ImageTextDetector(BaseProcessor):
    """图片文本检测处理器"""
    
    def __init__(self, config: PreprocessConfig, logger: logging.Logger = None):
        super().__init__(config, logger)
        self.logger.info("初始化图片文本检测处理器")
        
        # 设置Tesseract路径
        if self.config.tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = self.config.tesseract_path
    
    @safe_file_operation("图片文本检测")
    def process(self, md_file_path: str, images_dir: str) -> Dict[str, Any]:
        """
        检测并过滤Markdown文件中的无文本图片链接
        
        Args:
            md_file_path: Markdown文件路径
            images_dir: 图片目录路径
        
        Returns:
            处理结果字典
        """
        with timing_context(self.logger, f"图片文本检测: {md_file_path}"):
            # 读取文件内容
            with open(md_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # 匹配图片链接
            image_pattern = r'!\[.*?\]\((.+)\)'
            matches = list(re.finditer(image_pattern, content))
            
            links_to_remove = []
            processed_images = 0
            removed_images = 0
            
            self.logger.info(f"找到 {len(matches)} 个图片链接")
            
            # 检查每个图片链接
            for match in matches:
                image_path = match.group(1)
                image_filename = os.path.basename(image_path)
                full_image_path = Path(images_dir) / image_filename
                
                self.logger.debug(f"处理图片: {image_filename}")
                processed_images += 1
                
                if full_image_path.exists():
                    has_text = self._detect_text_in_image(str(full_image_path))
                    
                    if not has_text:
                        links_to_remove.append(match.group(0))
                        removed_images += 1
                        self.logger.info(f"移除无文本图片: {image_filename}")
                else:
                    self.logger.warning(f"图片文件不存在: {full_image_path}")
            
            # 从Markdown文件中删除无文本图片链接
            for link in links_to_remove:
                content = content.replace(link, '')
            
            # 备份原文件
            backup_path = backup_file(md_file_path)
            if backup_path:
                self.logger.info(f"已备份原文件: {backup_path}")
            
            # 保存更新后的文件
            with open(md_file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # 更新统计信息
            self.stats["processed_files"] += 1
            self.stats["successful_operations"] += processed_images
            
            result = {
                "status": "success",
                "file_path": md_file_path,
                "total_images_found": len(matches),
                "images_processed": processed_images,
                "images_removed": removed_images,
                "images_kept": processed_images - removed_images,
                "content_size_before": len(original_content),
                "content_size_after": len(content),
                "content_changed": original_content != content
            }
            
            self.logger.info(f"检测完成: 处理{processed_images}张图片，移除{removed_images}张无文本图片")
            return result
    
    def _detect_text_in_image(self, image_path: str) -> bool:
        """检测图片中是否包含文本"""
        try:
            # 打开图片
            img = Image.open(image_path)
            
            # 使用pytesseract识别文字
            text = pytesseract.image_to_string(
                img, 
                lang=self.config.ocr_languages,
                config=f'--psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
            )
            
            # 清理文本
            clean_text = re.sub(r'\s+', ' ', text).strip()
            
            # 检查文本长度和置信度
            has_meaningful_text = len(clean_text) >= self.config.min_text_length
            
            if has_meaningful_text:
                self.logger.debug(f"检测到文本: {clean_text[:50]}...")
            
            return has_meaningful_text
            
        except Exception as e:
            self.logger.error(f"文本检测失败 {image_path}: {e}")
            self.stats["errors"].append(f"文本检测失败 {image_path}: {e}")
            # 检测失败时，保守地认为有文本
            return True 