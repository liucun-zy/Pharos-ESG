"""
预处理模块工具函数

提供：
- 日志设置和管理
- 路径验证和处理
- 文件操作工具
- 性能监控工具
"""

import os
import logging
import time
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional
from functools import wraps
from contextlib import contextmanager


def setup_logging(log_level: str = "INFO", 
                 log_file: Optional[str] = None,
                 logger_name: str = "preprocess") -> logging.Logger:
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
        if "输出目录" in desc or "output" in desc.lower():
            # 对于输出目录，我们检查其父目录是否存在
            # 如果输出目录本身不存在，这是正常的（我们会创建它）
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


def get_file_stats(file_path: str) -> Dict[str, Any]:
    """
    获取文件统计信息
    
    Args:
        file_path: 文件路径
    
    Returns:
        文件统计信息字典
    """
    path = Path(file_path)
    
    if not path.exists():
        return {"exists": False}
    
    stat = path.stat()
    
    return {
        "exists": True,
        "size": stat.st_size,
        "size_mb": round(stat.st_size / (1024 * 1024), 2),
        "modified_time": time.ctime(stat.st_mtime),
        "is_file": path.is_file(),
        "is_dir": path.is_dir(),
        "extension": path.suffix.lower() if path.is_file() else None
    }


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
        source_path = Path(file_path)
        if not source_path.exists():
            return None
        
        backup_path = source_path.with_suffix(source_path.suffix + backup_suffix)
        shutil.copy2(source_path, backup_path)
        
        return str(backup_path)
    except Exception:
        return None


def count_lines(file_path: str) -> int:
    """
    统计文件行数
    
    Args:
        file_path: 文件路径
    
    Returns:
        行数
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return sum(1 for _ in f)
    except Exception:
        return 0


def get_image_files(directory: str, extensions: List[str] = None) -> List[str]:
    """
    获取目录下的所有图片文件
    
    Args:
        directory: 目录路径
        extensions: 支持的扩展名列表
    
    Returns:
        图片文件路径列表
    """
    if extensions is None:
        extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
    
    directory = Path(directory)
    if not directory.exists():
        return []
    
    image_files = []
    for ext in extensions:
        image_files.extend(directory.glob(f"*{ext}"))
        image_files.extend(directory.glob(f"*{ext.upper()}"))
    
    return [str(f) for f in sorted(image_files)]


class ProgressTracker:
    """进度跟踪器"""
    
    def __init__(self, total: int, logger: logging.Logger = None):
        self.total = total
        self.current = 0
        self.logger = logger or logging.getLogger(__name__)
        self.start_time = time.time()
    
    def update(self, increment: int = 1, message: str = ""):
        """更新进度"""
        self.current += increment
        progress = (self.current / self.total) * 100
        
        elapsed_time = time.time() - self.start_time
        if self.current > 0:
            eta = (elapsed_time / self.current) * (self.total - self.current)
            eta_str = f", 预计剩余: {eta:.1f}秒"
        else:
            eta_str = ""
        
        log_message = f"进度: {self.current}/{self.total} ({progress:.1f}%){eta_str}"
        if message:
            log_message += f" - {message}"
        
        self.logger.info(log_message)
    
    def finish(self, message: str = "处理完成"):
        """完成处理"""
        total_time = time.time() - self.start_time
        self.logger.info(f"{message}，总耗时: {total_time:.2f}秒")


class ProcessingStats:
    """处理统计信息"""
    
    def __init__(self):
        self.stats = {
            "start_time": time.time(),
            "end_time": None,
            "total_files_processed": 0,
            "successful_operations": 0,
            "failed_operations": 0,
            "errors": [],
            "warnings": []
        }
    
    def add_success(self):
        """添加成功操作"""
        self.stats["successful_operations"] += 1
    
    def add_failure(self, error_msg: str):
        """添加失败操作"""
        self.stats["failed_operations"] += 1
        self.stats["errors"].append(error_msg)
    
    def add_warning(self, warning_msg: str):
        """添加警告"""
        self.stats["warnings"].append(warning_msg)
    
    def increment_files(self):
        """增加处理文件数"""
        self.stats["total_files_processed"] += 1
    
    def finish(self):
        """完成统计"""
        self.stats["end_time"] = time.time()
        self.stats["total_time"] = self.stats["end_time"] - self.stats["start_time"]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return self.stats.copy()
    
    def summary(self) -> str:
        """生成摘要字符串"""
        if self.stats["end_time"] is None:
            self.finish()
        
        return f"""
处理统计摘要:
- 总处理时间: {self.stats['total_time']:.2f}秒
- 处理文件数: {self.stats['total_files_processed']}
- 成功操作数: {self.stats['successful_operations']}
- 失败操作数: {self.stats['failed_operations']}
- 错误数: {len(self.stats['errors'])}
- 警告数: {len(self.stats['warnings'])}
        """.strip() 