"""
结构增强模块工具函数

提供：
- 日志设置和管理
- 路径验证和处理
- 文本标准化和处理
- 性能监控工具
- 标题匹配算法
"""

import os
import logging
import time
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from functools import wraps
from contextlib import contextmanager
from rapidfuzz import fuzz


def setup_logging(log_level: str = "INFO", 
                 log_file: Optional[str] = None,
                 logger_name: str = "structure_enhancement") -> logging.Logger:
    """
    设置日志记录
    
    Args:
        log_level: 日志级别
        log_file: 日志文件路径（可选）
        logger_name: 日志器名称
    
    Returns:
        配置好的日志器
    """
    logger = logging.getLogger(logger_name)
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # 清除现有处理器
    logger.handlers.clear()
    
    # 创建格式器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 文件处理器（如果指定了文件路径）
    if log_file:
        # 确保日志目录存在
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def validate_paths(paths: Dict[str, str]) -> List[str]:
    """
    验证路径有效性
    
    Args:
        paths: 路径字典，键为路径描述，值为路径
    
    Returns:
        错误信息列表
    """
    errors = []
    
    for desc, path in paths.items():
        if not path:
            errors.append(f"{desc}路径不能为空")
            continue
        
        path_obj = Path(path)
        
        # 检查输出目录
        if "输出" in desc or "output" in desc.lower():
            # 对于输出目录，我们检查其父目录是否存在
            parent_dir = path_obj.parent
            if not parent_dir.exists():
                errors.append(f"输出目录的父目录不存在: {parent_dir}")
        # 检查输入路径是否存在
        else:
            if not path_obj.exists():
                errors.append(f"{desc}不存在: {path}")
    
    return errors


def ensure_directory(dir_path: str) -> Path:
    """
    确保目录存在，如果不存在则创建
    
    Args:
        dir_path: 目录路径
    
    Returns:
        Path对象
    """
    path = Path(dir_path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def extract_chinese(text: str) -> str:
    """
    提取文本中的中文字符
    
    Args:
        text: 输入文本
    
    Returns:
        只包含中文字符的文本
    """
    return ''.join(char for char in text if '\u4e00' <= char <= '\u9fff')


def normalize_title(title: str) -> str:
    """
    标准化标题文本，只保留中文字符并移除空白
    
    Args:
        title: 原始标题
    
    Returns:
        标准化后的标题
    """
    # 只提取中文字符
    chinese_only = extract_chinese(title)
    # 移除所有空白字符
    return re.sub(r'\s+', '', chinese_only)


def is_title_match(md_title: str, json_title: str, similarity_threshold: float = 0.8) -> Tuple[bool, float, bool]:
    """
    判断两个标题是否匹配
    
    Args:
        md_title: Markdown中的标题
        json_title: JSON中的标题
        similarity_threshold: 相似度阈值
    
    Returns:
        Tuple[bool, float, bool]: (是否匹配, 相似度, 是否完全匹配)
        
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
    if similarity >= similarity_threshold:
        return True, similarity, False
        
    # 3. 包含关系
    if json_chinese in md_chinese:
        return True, 0.9, False
        
    return False, 0.0, False


def get_title_level_from_markdown(line: str) -> int:
    """
    从Markdown行中提取标题层级
    
    Args:
        line: Markdown行
    
    Returns:
        标题层级（1-6），如果不是标题返回0
    """
    line = line.strip()
    if line.startswith('#'):
        # 计算#的数量
        level = 0
        for char in line:
            if char == '#':
                level += 1
            else:
                break
        return min(level, 6)
    return 0


def format_title_with_level(title: str, level: int) -> str:
    """
    格式化标题为指定层级的Markdown格式
    
    Args:
        title: 标题文本
        level: 层级（1-6）
    
    Returns:
        格式化后的Markdown标题
    """
    if level < 1:
        level = 1
    elif level > 6:
        level = 6
    
    return '#' * level + ' ' + title.strip()


def parse_page_index(line: str, pattern: str = r'<page_idx:(\d+)>') -> Optional[int]:
    """
    从行中解析页面索引
    
    Args:
        line: 输入行
        pattern: 页面索引模式
    
    Returns:
        页面索引，如果没有匹配返回None
    """
    match = re.match(pattern, line.strip())
    if match:
        return int(match.group(1))
    return None


def is_table_line(line: str, table_patterns: List[str]) -> bool:
    """
    判断是否为表格行
    
    Args:
        line: 输入行
        table_patterns: 表格模式列表
    
    Returns:
        是否为表格行
    """
    line = line.strip()
    for pattern in table_patterns:
        if re.match(pattern, line):
            return True
    return False


@contextmanager
def timing_context(logger: logging.Logger, operation_name: str):
    """
    计时上下文管理器
    
    Args:
        logger: 日志器
        operation_name: 操作名称
    """
    start_time = time.time()
    logger.info(f"开始 {operation_name}")
    
    try:
        yield
    finally:
        elapsed_time = time.time() - start_time
        logger.info(f"完成 {operation_name}，耗时: {elapsed_time:.2f}秒")


def safe_file_operation(operation: str):
    """
    安全文件操作装饰器
    
    Args:
        operation: 操作描述
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except FileNotFoundError as e:
                raise FileNotFoundError(f"{operation}失败，文件未找到: {e}")
            except PermissionError as e:
                raise PermissionError(f"{operation}失败，权限不足: {e}")
            except Exception as e:
                raise Exception(f"{operation}失败: {e}")
        return wrapper
    return decorator


def backup_file(file_path: str, backup_suffix: str = ".backup") -> Optional[str]:
    """
    备份文件
    
    Args:
        file_path: 原文件路径
        backup_suffix: 备份文件后缀
    
    Returns:
        备份文件路径，如果备份失败返回None
    """
    try:
        import shutil
        source_path = Path(file_path)
        if not source_path.exists():
            return None
        
        backup_path = source_path.with_suffix(source_path.suffix + backup_suffix)
        shutil.copy2(source_path, backup_path)
        
        return str(backup_path)
    except Exception:
        return None


def clean_text(text: str) -> str:
    """
    清理文本，移除多余的空白字符
    
    Args:
        text: 输入文本
    
    Returns:
        清理后的文本
    """
    # 移除多余的空白字符
    text = re.sub(r'\s+', ' ', text)
    # 移除首尾空白
    return text.strip()


def split_lines_by_pattern(content: str, pattern: str) -> List[Tuple[str, List[str]]]:
    """
    按模式分割内容为多个部分
    
    Args:
        content: 输入内容
        pattern: 分割模式
    
    Returns:
        分割后的部分列表，每个部分包含(标识符, 内容行列表)
    """
    lines = content.split('\n')
    sections = []
    current_section = None
    current_lines = []
    
    for line in lines:
        match = re.match(pattern, line.strip())
        if match:
            # 保存上一个部分
            if current_section is not None:
                sections.append((current_section, current_lines))
            # 开始新部分
            current_section = match.group(1)
            current_lines = []
        else:
            if current_section is not None:
                current_lines.append(line)
    
    # 保存最后一个部分
    if current_section is not None:
        sections.append((current_section, current_lines))
    
    return sections


class ProcessingStats:
    """处理统计信息"""
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """重置统计信息"""
        self.start_time = time.time()
        self.end_time = None
        self.processed_files = 0
        self.successful_operations = 0
        self.failed_operations = 0
        self.warnings = []
        self.errors = []
    
    def add_success(self):
        """添加成功操作"""
        self.successful_operations += 1
    
    def add_failure(self, error_msg: str):
        """添加失败操作"""
        self.failed_operations += 1
        self.errors.append(error_msg)
    
    def add_warning(self, warning_msg: str):
        """添加警告"""
        self.warnings.append(warning_msg)
    
    def increment_files(self):
        """增加处理文件数"""
        self.processed_files += 1
    
    def finish(self):
        """完成处理"""
        self.end_time = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.end_time - self.start_time if self.end_time else None,
            "processed_files": self.processed_files,
            "successful_operations": self.successful_operations,
            "failed_operations": self.failed_operations,
            "total_operations": self.successful_operations + self.failed_operations,
            "success_rate": self.successful_operations / max(1, self.successful_operations + self.failed_operations),
            "warnings_count": len(self.warnings),
            "errors_count": len(self.errors),
            "warnings": self.warnings,
            "errors": self.errors
        }
    
    def summary(self) -> str:
        """生成统计摘要"""
        total_ops = self.successful_operations + self.failed_operations
        success_rate = self.successful_operations / max(1, total_ops) * 100
        duration = self.end_time - self.start_time if self.end_time else 0
        
        return (f"处理完成: {self.processed_files}个文件, "
                f"{total_ops}个操作 (成功率: {success_rate:.1f}%), "
                f"耗时: {duration:.2f}秒, "
                f"警告: {len(self.warnings)}个, 错误: {len(self.errors)}个")


def find_best_fuzzy_match(target: str, candidates: List[str], threshold: float = 0.8) -> Tuple[Optional[str], float]:
    """
    在候选列表中找到最佳模糊匹配
    
    Args:
        target: 目标字符串
        candidates: 候选字符串列表
        threshold: 匹配阈值
    
    Returns:
        Tuple[Optional[str], float]: (最佳匹配, 相似度)
    """
    if not candidates:
        return None, 0.0
    
    target_normalized = normalize_title(target)
    best_match = None
    best_score = 0.0
    
    for candidate in candidates:
        candidate_normalized = normalize_title(candidate)
        score = fuzz.ratio(target_normalized, candidate_normalized) / 100.0
        
        if score > best_score and score >= threshold:
            best_score = score
            best_match = candidate
    
    return best_match, best_score


def validate_json_structure(data: Any, required_fields: List[str]) -> List[str]:
    """
    验证JSON结构
    
    Args:
        data: JSON数据
        required_fields: 必需字段列表
    
    Returns:
        错误信息列表
    """
    errors = []
    
    if not isinstance(data, (dict, list)):
        errors.append("JSON数据必须是字典或列表")
        return errors
    
    if isinstance(data, dict):
        for field in required_fields:
            if field not in data:
                errors.append(f"缺少必需字段: {field}")
    
    return errors 