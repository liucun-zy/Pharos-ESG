"""
ESG报告预处理模块 - 阶段1数据预处理工具集

这个模块提供了ESG报告处理流程第一阶段的所有预处理功能：
- JSON到Markdown的转换
- 图片链接格式标准化  
- 无文本图片的智能过滤

特性：
- 模块化设计，支持独立使用和组合使用
- 配置驱动，支持自定义参数
- 完整的日志记录和错误处理
- 支持消融实验和A/B测试
"""

__version__ = "1.0.0"
__author__ = "ZzYy"

# 导入主要的处理器类
from .processors import (
    JsonToMarkdownProcessor,
    ImageLinkConverter, 
    ImageTextDetector
)

# 导入预处理管道
from .pipeline import PreprocessPipeline, BatchPreprocessPipeline

# 导入配置管理
from .config import PreprocessConfig

# 导入工具函数
from .utils import setup_logging, validate_paths

# 定义公共接口
__all__ = [
    'JsonToMarkdownProcessor',
    'ImageLinkConverter',
    'ImageTextDetector', 
    'PreprocessPipeline',
    'BatchPreprocessPipeline',
    'PreprocessConfig',
    'setup_logging',
    'validate_paths'
]

# 版本兼容性检查
def check_dependencies():
    """检查必要的依赖是否安装"""
    try:
        import pytesseract
        import PIL
        return True
    except ImportError as e:
        print(f"缺少必要依赖: {e}")
        return False

# 快速使用接口
def quick_preprocess(input_json_path, output_dir, config=None):
    """
    快速预处理接口，适用于简单场景
    
    Args:
        input_json_path: 输入JSON文件路径
        output_dir: 输出目录路径
        config: 可选的配置对象
    
    Returns:
        dict: 处理结果统计
    """
    if not check_dependencies():
        raise ImportError("请安装必要的依赖包")
    
    pipeline = PreprocessPipeline(config or PreprocessConfig())
    return pipeline.run(input_json_path, output_dir) 