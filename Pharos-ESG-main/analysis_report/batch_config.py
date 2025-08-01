#!/usr/bin/env python3
"""
批量处理配置文件

这个文件包含了所有批量处理的配置选项，
修改这个文件比直接修改主脚本更安全和方便。
"""

import os
from pathlib import Path
from preprocess_module import PreprocessConfig

# ==================== 文件路径配置 ====================

# 输入文件配置
INPUT_CONFIG = {
    # 方式1: 指定具体文件列表
    "specific_files": [
        # 在这里添加更多文件路径
    ],
    
    # 方式2: 目录扫描配置
    "directory_scan": {
        "enabled": True,
        "directory": "/Users/liucun/Desktop/yuancailiao",
        "pattern": "**/*.json",  # 搜索模式
        "recursive": True,       # 是否递归搜索子目录
        "exclude_patterns": [    # 排除的模式
            "**/*_temp_pages/**",  # 排除 _temp_pages 结尾的文件夹
            "**/temp/**",
            "**/cache/**",
            "**/backup/**"
        ]
    },
    
    # 子文件夹处理配置
    "subfolder_processing": {
        "enabled": True,
        "base_directory": "/Users/liucun/Desktop/yuancailiao",
        "exclude_folder_patterns": ["*_temp_pages"],  # 排除的文件夹模式
        "output_in_source": True,  # 输出放在源文件夹中
        "create_output_subfolder": False  # 不创建额外的输出子文件夹
    },
    
    # 输出目录（当不使用子文件夹处理时）
    "output_base_dir": "/Users/liucun/Desktop/batch_processed"
}

# ==================== 性能配置 ====================

PERFORMANCE_CONFIG = {
    # 并行处理配置
    "parallel_processing": {
        "enabled": True,
        "max_workers": 3,  # 建议值：CPU核心数 - 1
        "chunk_size": 5    # 每批处理的文件数
    },
    
    # 内存管理
    "memory_management": {
        "max_memory_per_worker": "2GB",
        "cleanup_temp_files": True,
        "force_garbage_collection": True
    },
    
    # 超时设置
    "timeouts": {
        "single_file_timeout": 600,  # 单文件处理超时（秒）
        "ocr_timeout": 120,          # OCR超时（秒）
        "image_processing_timeout": 60  # 图像处理超时（秒）
    }
}

# ==================== 错误处理配置 ====================

ERROR_HANDLING_CONFIG = {
    "continue_on_error": True,  # 遇到错误是否继续处理其他文件
    "max_retries": 2,          # 失败重试次数
    "retry_delay": 2.0,        # 重试间隔（秒）
    "save_error_details": True, # 是否保存详细错误信息
    "create_error_log": True    # 是否创建错误日志文件
}

# ==================== 预处理配置 ====================

def create_preprocess_config() -> PreprocessConfig:
    """创建预处理配置对象"""
    config = PreprocessConfig()
    
    # 基础配置
    config.experiment_name = "batch_processing"
    config.log_level = "INFO"
    config.log_to_file = True
    
    # 模块开关
    config.json_to_md_enabled = True
    config.image_link_conversion_enabled = True
    config.text_detection_enabled = True
    
    # OCR配置
    config.tesseract_path = "/opt/homebrew/bin/tesseract"  # macOS
    config.ocr_languages = "chi_sim+eng"
    config.confidence_threshold = 30.0
    config.min_text_length = 3
    
    # 性能配置
    config.enable_parallel_processing = PERFORMANCE_CONFIG["parallel_processing"]["enabled"]
    config.max_workers = PERFORMANCE_CONFIG["parallel_processing"]["max_workers"]
    
    return config

# ==================== 专用配置模板 ====================

# 快速处理配置（跳过一些耗时步骤）
FAST_CONFIG = {
    "json_to_md_enabled": True,
    "image_link_conversion_enabled": True,
    "text_detection_enabled": False,  # 跳过OCR
    "confidence_threshold": 50.0,
    "min_text_length": 5
}

# 高质量配置（所有功能开启）
HIGH_QUALITY_CONFIG = {
    "json_to_md_enabled": True,
    "image_link_conversion_enabled": True,
    "text_detection_enabled": True,
    "confidence_threshold": 20.0,
    "min_text_length": 1,
    "ocr_languages": "chi_sim+chi_tra+eng"
}

# 调试配置（详细日志）
DEBUG_CONFIG = {
    "log_level": "DEBUG",
    "log_to_file": True,
    "json_to_md_enabled": True,
    "image_link_conversion_enabled": True,
    "text_detection_enabled": True,
    "confidence_threshold": 30.0
}

# ==================== 配置应用函数 ====================

def apply_config_template(config: PreprocessConfig, template_name: str) -> PreprocessConfig:
    """应用配置模板"""
    templates = {
        "fast": FAST_CONFIG,
        "high_quality": HIGH_QUALITY_CONFIG,
        "debug": DEBUG_CONFIG
    }
    
    if template_name in templates:
        template = templates[template_name]
        for key, value in template.items():
            if hasattr(config, key):
                setattr(config, key, value)
        config.experiment_name = f"batch_{template_name}"
    
    return config

def get_config_for_environment(env: str = "production") -> PreprocessConfig:
    """根据环境获取配置"""
    config = create_preprocess_config()
    
    if env == "development":
        config = apply_config_template(config, "debug")
        config.max_workers = 2
    elif env == "testing":
        config = apply_config_template(config, "fast")
        config.max_workers = 1
    elif env == "production":
        config = apply_config_template(config, "high_quality")
        config.max_workers = min(4, os.cpu_count() - 1)
    
    return config

# ==================== 系统检查函数 ====================

def check_system_requirements():
    """检查系统要求"""
    issues = []
    
    # 检查Tesseract
    tesseract_path = "/opt/homebrew/bin/tesseract"
    if not os.path.exists(tesseract_path):
        issues.append(f"Tesseract未找到: {tesseract_path}")
    
    # 检查可用内存
    try:
        import psutil
        memory = psutil.virtual_memory()
        if memory.available < 4 * 1024 * 1024 * 1024:  # 4GB
            issues.append(f"可用内存不足: {memory.available / (1024**3):.1f}GB")
    except ImportError:
        issues.append("建议安装psutil以监控系统资源")
    
    # 检查CPU核心数
    cpu_count = os.cpu_count()
    if cpu_count < 2:
        issues.append("CPU核心数较少，建议禁用并行处理")
    
    return issues

# ==================== 配置验证函数 ====================

def validate_config():
    """验证配置"""
    errors = []
    
    # 验证输入路径
    if INPUT_CONFIG["specific_files"]:
        for file_path in INPUT_CONFIG["specific_files"]:
            if not os.path.exists(file_path):
                errors.append(f"输入文件不存在: {file_path}")
    
    if INPUT_CONFIG["directory_scan"]["enabled"]:
        scan_dir = INPUT_CONFIG["directory_scan"]["directory"]
        if not os.path.exists(scan_dir):
            errors.append(f"扫描目录不存在: {scan_dir}")
    
    # 验证子文件夹处理配置
    if INPUT_CONFIG.get("subfolder_processing", {}).get("enabled", False):
        subfolder_config = INPUT_CONFIG["subfolder_processing"]
        base_directory = subfolder_config.get("base_directory")
        if base_directory and not os.path.exists(base_directory):
            errors.append(f"子文件夹基础目录不存在: {base_directory}")
    
    # 验证输出目录（仅在非子文件夹处理模式时）
    if not INPUT_CONFIG.get("subfolder_processing", {}).get("output_in_source", False):
        output_dir = INPUT_CONFIG["output_base_dir"]
        try:
            os.makedirs(output_dir, exist_ok=True)
        except PermissionError:
            errors.append(f"输出目录无写入权限: {output_dir}")
    
    # 验证性能配置
    max_workers = PERFORMANCE_CONFIG["parallel_processing"]["max_workers"]
    if max_workers > os.cpu_count():
        errors.append(f"并行线程数过多: {max_workers} > {os.cpu_count()}")
    
    return errors

if __name__ == "__main__":
    # 配置检查
    print("🔍 检查系统要求...")
    issues = check_system_requirements()
    if issues:
        print("⚠️ 系统检查发现以下问题:")
        for issue in issues:
            print(f"   - {issue}")
    else:
        print("✅ 系统检查通过")
    
    print("\n🔍 验证配置...")
    errors = validate_config()
    if errors:
        print("❌ 配置验证失败:")
        for error in errors:
            print(f"   - {error}")
    else:
        print("✅ 配置验证通过")
    
    # 显示配置信息
    config = create_preprocess_config()
    print(f"\n📋 当前配置:")
    print(f"   实验名称: {config.experiment_name}")
    print(f"   日志级别: {config.log_level}")
    print(f"   并行处理: {config.enable_parallel_processing}")
    print(f"   最大工作线程: {config.max_workers}")
    print(f"   OCR语言: {config.ocr_languages}")
    print(f"   置信度阈值: {config.confidence_threshold}")
    
    # 显示子文件夹处理配置
    if INPUT_CONFIG.get("subfolder_processing", {}).get("enabled", False):
        subfolder_config = INPUT_CONFIG["subfolder_processing"]
        print(f"\n📁 子文件夹处理配置:")
        print(f"   启用状态: {subfolder_config.get('enabled', False)}")
        print(f"   基础目录: {subfolder_config.get('base_directory', 'N/A')}")
        print(f"   排除模式: {subfolder_config.get('exclude_folder_patterns', [])}")
        print(f"   输出到源文件夹: {subfolder_config.get('output_in_source', False)}")
    else:
        print(f"\n📁 传统处理模式:")
        print(f"   扫描目录: {INPUT_CONFIG['directory_scan']['directory']}")
        print(f"   输出目录: {INPUT_CONFIG['output_base_dir']}") 