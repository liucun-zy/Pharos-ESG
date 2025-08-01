"""
结构增强模块配置管理

提供配置类和消融实验支持，管理所有处理参数和API设置
"""

import json
import os
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional
from pathlib import Path


@dataclass
class StructureEnhancementConfig:
    """结构增强模块配置类"""
    
    # ========== 基础配置 ==========
    experiment_name: str = "default"
    base_dir: str = ""
    output_dir: str = ""
    
    # ========== 日志配置 ==========
    log_level: str = "INFO"
    log_to_file: bool = True
    log_file_path: str = "structure_enhancement.log"
    
    # ========== API配置 ==========
    # DeepSeek V3 API配置
    deepseek_api_key: str = ""
    deepseek_api_url: str = "https://api.siliconflow.cn/v1/chat/completions"
    deepseek_model: str = "Pro/deepseek-ai/DeepSeek-V3"
    
    # DeepSeek R1 API配置（专门用于插入未匹配章节标题）
    deepseek_r1_api_key: str = ""
    deepseek_r1_api_url: str = "https://deepseek-r1-0528.ibswufe.com:21112/v1/chat/completions"
    deepseek_r1_model: str = "deepseek-r1-0528"
    
    # Qwen VL API配置
    qwen_api_key: str = ""
    qwen_api_url: str = "https://api.siliconflow.cn/v1/chat/completions"
    qwen_model: str = ""
    
    # API通用配置
    api_timeout: int = 60
    max_retries: int = 3
    retry_delay: int = 5
    
    # ========== 标题提取配置 ==========
    # 图片压缩配置
    max_image_size_mb: float = 1.0
    image_quality_reduction: int = 5
    
    # 标题提取参数
    extract_max_tokens: int = 2048
    extract_temperature: float = 0.0
    extract_top_p: float = 1.0
    
    # 示例文件路径
    # 注意：按照extract_title.py的映射
    # sample2base64.txt -> example1_base64 (用于规则C)
    # sample1base64.txt -> example2_base64 (用于规则D)
    sample_base64_files: List[str] = field(default_factory=lambda: [
        str(Path(__file__).parent / "sample2base64.txt"),  # example1_base64
        str(Path(__file__).parent / "sample1base64.txt")   # example2_base64
    ])
    
    # ========== 页面分组配置 ==========
    # 页面索引模式
    page_idx_pattern: str = r'<page_idx:(\d+)>'
    
    # 表格检测配置
    table_detection_enabled: bool = True
    table_patterns: List[str] = field(default_factory=lambda: [
        r'^\s*<table',
        r'^\s*\|',
        r'^\s*---',
        r'.*\|.*(?<!^#)'
    ])
    
    # ========== 标题对齐配置 ==========
    # 标题匹配阈值
    title_similarity_threshold: float = 0.8
    fuzzy_match_enabled: bool = True
    
    # 标题层级配置
    max_title_levels: int = 4
    default_title_level: int = 3
    
    # 智能匹配配置
    use_llm_matching: bool = True
    llm_matching_temperature: float = 0.1
    llm_matching_max_tokens: int = 512
    
    # 标题插入配置
    auto_insert_missing_titles: bool = True
    insert_confidence_threshold: float = 0.7
    
    # ========== 结构优化配置 ==========
    # 层级调整
    auto_adjust_levels: bool = True
    preserve_original_structure: bool = True
    
    # 内容处理
    preserve_non_title_content: bool = True
    merge_adjacent_content: bool = False
    
    # ========== 消融实验配置 ==========
    ablation_config: Dict[str, Any] = field(default_factory=dict)
    
    # 预定义的消融实验
    ABLATION_EXPERIMENTS = {
        "no_llm_matching": {
            "use_llm_matching": False,
            "experiment_name": "no_llm_matching"
        },
        "no_fuzzy_match": {
            "fuzzy_match_enabled": False,
            "experiment_name": "no_fuzzy_match"
        },
        "strict_matching": {
            "title_similarity_threshold": 0.95,
            "fuzzy_match_enabled": False,
            "use_llm_matching": False,
            "experiment_name": "strict_matching"
        },
        "high_similarity": {
            "title_similarity_threshold": 0.9,
            "insert_confidence_threshold": 0.8,
            "experiment_name": "high_similarity"
        },
        "low_similarity": {
            "title_similarity_threshold": 0.6,
            "insert_confidence_threshold": 0.5,
            "experiment_name": "low_similarity"
        },
        "no_auto_insert": {
            "auto_insert_missing_titles": False,
            "experiment_name": "no_auto_insert"
        },
        "minimal_processing": {
            "use_llm_matching": False,
            "fuzzy_match_enabled": False,
            "auto_insert_missing_titles": False,
            "auto_adjust_levels": False,
            "experiment_name": "minimal_processing"
        }
    }
    
    def __post_init__(self):
        """初始化后的验证和设置"""
        # 确保目录路径存在
        if self.base_dir:
            Path(self.base_dir).mkdir(parents=True, exist_ok=True)
        if self.output_dir:
            Path(self.output_dir).mkdir(parents=True, exist_ok=True)
    
    def apply_ablation(self, experiment_name: str):
        """应用消融实验配置"""
        if experiment_name not in self.ABLATION_EXPERIMENTS:
            raise ValueError(f"未知的消融实验: {experiment_name}")
        
        config = self.ABLATION_EXPERIMENTS[experiment_name]
        self.ablation_config = config.copy()
        
        # 应用配置
        for key, value in config.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def validate(self) -> List[str]:
        """验证配置有效性"""
        errors = []
        
        # 验证API密钥
        if not self.deepseek_api_key and self.use_llm_matching:
            errors.append("启用LLM匹配时需要配置DeepSeek API密钥")
        
        if not self.qwen_api_key:
            errors.append("需要配置Qwen API密钥用于标题提取")
        
        # 验证阈值范围
        if not 0.0 <= self.title_similarity_threshold <= 1.0:
            errors.append("标题相似度阈值必须在0.0-1.0之间")
        
        if not 0.0 <= self.insert_confidence_threshold <= 1.0:
            errors.append("插入置信度阈值必须在0.0-1.0之间")
        
        # 验证层级设置
        if self.max_title_levels < 1 or self.max_title_levels > 6:
            errors.append("标题层级数必须在1-6之间")
        
        if self.default_title_level < 1 or self.default_title_level > self.max_title_levels:
            errors.append("默认标题层级必须在1到最大层级之间")
        
        # 验证文件路径
        if self.sample_base64_files:
            for file_path in self.sample_base64_files:
                if not Path(file_path).exists():
                    errors.append(f"示例文件不存在: {file_path}")
        
        return errors
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return asdict(self)
    
    def to_json(self, file_path: str):
        """保存为JSON文件"""
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
    
    @classmethod
    def from_json(cls, file_path: str) -> 'StructureEnhancementConfig':
        """从JSON文件加载配置"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls(**data)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StructureEnhancementConfig':
        """从字典创建配置"""
        return cls(**data)
    
    def get_api_config(self, api_type: str) -> Dict[str, Any]:
        """获取特定API的配置"""
        if api_type.lower() == "deepseek":
            return {
                "api_key": self.deepseek_api_key,
                "api_url": self.deepseek_api_url,
                "model": self.deepseek_model,
                "timeout": self.api_timeout,
                "max_retries": self.max_retries,
                "retry_delay": self.retry_delay
            }
        elif api_type.lower() == "deepseek_r1":
            return {
                "api_key": self.deepseek_r1_api_key,
                "api_url": self.deepseek_r1_api_url,
                "model": self.deepseek_r1_model,
                "timeout": self.api_timeout,
                "max_retries": self.max_retries,
                "retry_delay": self.retry_delay
            }
        elif api_type.lower() == "qwen":
            return {
                "api_key": self.qwen_api_key,
                "api_url": self.qwen_api_url,
                "model": self.qwen_model,
                "timeout": self.api_timeout,
                "max_retries": self.max_retries,
                "retry_delay": self.retry_delay
            }
        else:
            raise ValueError(f"不支持的API类型: {api_type}")
    
    def get_title_extraction_config(self) -> Dict[str, Any]:
        """获取标题提取配置"""
        return {
            "max_image_size_mb": self.max_image_size_mb,
            "image_quality_reduction": self.image_quality_reduction,
            "max_tokens": self.extract_max_tokens,
            "temperature": self.extract_temperature,
            "top_p": self.extract_top_p,
            "sample_base64_files": self.sample_base64_files
        }
    
    def get_title_alignment_config(self) -> Dict[str, Any]:
        """获取标题对齐配置"""
        return {
            "similarity_threshold": self.title_similarity_threshold,
            "fuzzy_match_enabled": self.fuzzy_match_enabled,
            "use_llm_matching": self.use_llm_matching,
            "llm_temperature": self.llm_matching_temperature,
            "llm_max_tokens": self.llm_matching_max_tokens,
            "auto_insert_missing": self.auto_insert_missing_titles,
            "insert_confidence_threshold": self.insert_confidence_threshold,
            "max_title_levels": self.max_title_levels,
            "default_title_level": self.default_title_level
        }
    
    def get_page_grouping_config(self) -> Dict[str, Any]:
        """获取页面分组配置"""
        return {
            "page_idx_pattern": self.page_idx_pattern,
            "table_detection_enabled": self.table_detection_enabled,
            "table_patterns": self.table_patterns
        }
    
    def copy(self) -> 'StructureEnhancementConfig':
        """创建配置副本"""
        return StructureEnhancementConfig(**self.to_dict())
    
    def __str__(self) -> str:
        """字符串表示"""
        return f"StructureEnhancementConfig(experiment={self.experiment_name})"
    
    def __repr__(self) -> str:
        """详细字符串表示"""
        return f"StructureEnhancementConfig({self.to_dict()})" 
