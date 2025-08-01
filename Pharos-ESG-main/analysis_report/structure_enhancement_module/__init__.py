"""
ESG报告结构增强模块 - 阶段2标题结构化处理工具集

这个模块提供了ESG报告处理流程第二阶段的所有结构增强功能：
- 目录标题提取与识别
- 页面内容分组重组
- 智能标题对齐与匹配
- 层级结构优化处理

特性：
- 模块化设计，支持独立使用和组合使用
- 配置驱动，支持自定义参数和消融实验
- 完整的日志记录和错误处理
- 支持多种API后端（DeepSeek、Qwen等）
- 智能标题匹配算法，支持模糊匹配和语义理解
"""

__version__ = "1.0.0"
__author__ = "ZzYy"

# 导入核心处理器类
from .processors import (
    TitleExtractor,
    PageGrouper,
    TitleAligner,
    StructureEnhancer
)

# 导入配置管理
from .config import StructureEnhancementConfig

# 导入工具函数
from .utils import (
    setup_logging,
    validate_paths,
    normalize_title,
    extract_chinese
)

# 导入API客户端
from .api_clients import (
    DeepSeekClient,
    DeepSeekR1Client,
    QwenVLClient,
    APIClientBase
)

# 导入处理管道
from .pipeline import (
    StructureEnhancementPipeline,
    BatchStructureEnhancementPipeline,
    AblationExperimentRunner
)

# 定义公共接口
__all__ = [
    # 核心处理器
    'TitleExtractor',
    'PageGrouper', 
    'TitleAligner',
    'StructureEnhancer',
    
    # 配置管理
    'StructureEnhancementConfig',
    
    # 工具函数
    'setup_logging',
    'validate_paths',
    'normalize_title',
    'extract_chinese',
    
    # API客户端
    'DeepSeekClient',
    'DeepSeekR1Client',
    'QwenVLClient',
    'APIClientBase',
    
    # 处理管道
    'StructureEnhancementPipeline',
    'BatchStructureEnhancementPipeline',
    'AblationExperimentRunner'
]

# 版本兼容性检查
def check_dependencies():
    """检查必要的依赖是否安装"""
    try:
        import requests
        import rapidfuzz
        import PIL
        import tenacity
        return True
    except ImportError as e:
        print(f"缺少必要依赖: {e}")
        return False

# 快速使用接口
def quick_structure_enhancement(input_md_path, titles_json_path, output_dir, config=None):
    """
    快速结构增强接口，适用于简单场景
    
    Args:
        input_md_path: 输入Markdown文件路径
        titles_json_path: 标题JSON文件路径
        output_dir: 输出目录路径
        config: 可选的配置对象
    
    Returns:
        dict: 处理结果统计
    """
    if not check_dependencies():
        raise ImportError("请安装必要的依赖包")
    
    pipeline = StructureEnhancementPipeline(config or StructureEnhancementConfig())
    return pipeline.run(input_md_path, titles_json_path, output_dir) 