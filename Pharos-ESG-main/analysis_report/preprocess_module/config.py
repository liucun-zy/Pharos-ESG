"""
预处理模块配置管理

支持：
- 默认配置和自定义配置
- 消融实验配置
- 配置验证和序列化
"""

import os
import json
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any


@dataclass
class PreprocessConfig:
    """预处理模块配置类"""
    
    # === 基础路径配置 ===
    base_dir: str = ""
    output_dir: str = ""
    
    # === JSON转Markdown配置 ===
    json_to_md_enabled: bool = True
    preserve_html_tables: bool = True
    add_page_markers: bool = True
    
    # === 图片链接转换配置 ===
    image_link_conversion_enabled: bool = True
    supported_image_extensions: List[str] = None
    validate_image_existence: bool = True
    
    # === 图片文本检测配置 ===
    text_detection_enabled: bool = True
    tesseract_path: str = "/opt/homebrew/bin/tesseract"  # macOS默认路径
    ocr_languages: str = "chi_sim+eng"
    min_text_length: int = 3  # 最小文本长度阈值
    confidence_threshold: float = 30.0  # OCR置信度阈值
    
    # === 日志配置 ===
    log_level: str = "INFO"
    log_to_file: bool = True
    log_file_path: str = ""
    
    # === 性能配置 ===
    enable_parallel_processing: bool = False
    max_workers: int = 4
    
    # === 消融实验配置 ===
    experiment_name: str = "default"
    ablation_config: Dict[str, Any] = None
    
    def __post_init__(self):
        """初始化后的配置处理"""
        if self.supported_image_extensions is None:
            self.supported_image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
        
        if self.ablation_config is None:
            self.ablation_config = {}
        
        # 设置默认日志文件路径
        if not self.log_file_path and self.output_dir:
            self.log_file_path = os.path.join(self.output_dir, "preprocess.log")
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'PreprocessConfig':
        """从字典创建配置对象"""
        return cls(**config_dict)
    
    @classmethod
    def from_json(cls, json_path: str) -> 'PreprocessConfig':
        """从JSON文件加载配置"""
        with open(json_path, 'r', encoding='utf-8') as f:
            config_dict = json.load(f)
        return cls.from_dict(config_dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    def to_json(self, json_path: str):
        """保存为JSON文件"""
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
    
    def validate(self) -> List[str]:
        """验证配置有效性"""
        errors = []
        
        # 验证路径
        if self.base_dir and not os.path.exists(self.base_dir):
            errors.append(f"基础目录不存在: {self.base_dir}")
        
        # 验证Tesseract路径
        if self.text_detection_enabled and not os.path.exists(self.tesseract_path):
            errors.append(f"Tesseract路径不存在: {self.tesseract_path}")
        
        # 验证阈值范围
        if not 0 <= self.confidence_threshold <= 100:
            errors.append("置信度阈值必须在0-100之间")
        
        if self.min_text_length < 0:
            errors.append("最小文本长度不能为负数")
        
        return errors
    
    def apply_ablation(self, ablation_name: str):
        """应用消融实验配置"""
        ablation_configs = {
            "no_text_detection": {
                "text_detection_enabled": False
            },
            "no_image_validation": {
                "validate_image_existence": False
            },
            "minimal_processing": {
                "json_to_md_enabled": True,
                "image_link_conversion_enabled": False,
                "text_detection_enabled": False
            },
            "high_confidence": {
                "confidence_threshold": 70.0,
                "min_text_length": 10
            },
            "low_confidence": {
                "confidence_threshold": 10.0,
                "min_text_length": 1
            }
        }
        
        if ablation_name in ablation_configs:
            config_updates = ablation_configs[ablation_name]
            for key, value in config_updates.items():
                setattr(self, key, value)
            self.experiment_name = ablation_name
            self.ablation_config = config_updates
        else:
            raise ValueError(f"未知的消融实验配置: {ablation_name}")


class ConfigManager:
    """配置管理器，支持多环境配置"""
    
    def __init__(self, config_dir: str = None):
        self.config_dir = Path(config_dir) if config_dir else Path.cwd() / "configs"
        self.config_dir.mkdir(exist_ok=True)
    
    def save_config(self, config: PreprocessConfig, name: str = "default"):
        """保存配置"""
        config_path = self.config_dir / f"{name}.json"
        config.to_json(str(config_path))
        return config_path
    
    def load_config(self, name: str = "default") -> PreprocessConfig:
        """加载配置"""
        config_path = self.config_dir / f"{name}.json"
        if config_path.exists():
            return PreprocessConfig.from_json(str(config_path))
        else:
            # 返回默认配置
            return PreprocessConfig()
    
    def list_configs(self) -> List[str]:
        """列出所有可用配置"""
        return [f.stem for f in self.config_dir.glob("*.json")]
    
    def create_ablation_configs(self):
        """创建所有消融实验配置文件"""
        base_config = PreprocessConfig()
        ablation_names = [
            "no_text_detection",
            "no_image_validation", 
            "minimal_processing",
            "high_confidence",
            "low_confidence"
        ]
        
        for name in ablation_names:
            config = PreprocessConfig()
            config.apply_ablation(name)
            self.save_config(config, f"ablation_{name}")
        
        # 保存默认配置
        self.save_config(base_config, "default")
        
        return ablation_names


# 预定义配置模板
def get_production_config(base_dir: str, output_dir: str) -> PreprocessConfig:
    """生产环境配置"""
    return PreprocessConfig(
        base_dir=base_dir,
        output_dir=output_dir,
        json_to_md_enabled=True,
        image_link_conversion_enabled=True,
        text_detection_enabled=True,
        log_level="INFO",
        log_to_file=True,
        enable_parallel_processing=True,
        confidence_threshold=30.0,
        experiment_name="production"
    )


def get_debug_config(base_dir: str, output_dir: str) -> PreprocessConfig:
    """调试环境配置"""
    return PreprocessConfig(
        base_dir=base_dir,
        output_dir=output_dir,
        json_to_md_enabled=True,
        image_link_conversion_enabled=True,
        text_detection_enabled=True,
        log_level="DEBUG",
        log_to_file=True,
        enable_parallel_processing=False,
        confidence_threshold=10.0,
        experiment_name="debug"
    ) 