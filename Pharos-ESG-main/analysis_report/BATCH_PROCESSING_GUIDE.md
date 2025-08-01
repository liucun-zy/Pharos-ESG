# ESG报告批量预处理指南

## 📋 概述

这个批量处理系统可以帮你同时处理多个ESG报告JSON文件，支持并行处理、错误恢复、进度监控等功能。

## 🚀 快速开始

### 1. 准备工作

确保你已经安装了必要的依赖：
```bash
# 安装Tesseract OCR
brew install tesseract tesseract-lang

# 安装Python依赖
pip install pytesseract pillow
```

### 2. 配置文件设置

编辑 `batch_config.py` 文件：

```python
# 输入文件配置
INPUT_CONFIG = {
    "specific_files": [
        "/path/to/your/file1.json",
        "/path/to/your/file2.json"
    ],
    "directory_scan": {
        "enabled": True,
        "directory": "/path/to/your/directory",
        "pattern": "**/*.json"
    }
}
```

### 3. 运行批量处理

```bash
# 运行批量处理
python run_batch_preprocess.py

# 或者先检查配置
python batch_config.py
```

## 🔧 配置选项

### 输入文件配置

```python
INPUT_CONFIG = {
    # 方式1: 指定具体文件
    "specific_files": [
        "/Users/liucun/Desktop/file1.json",
        "/Users/liucun/Desktop/file2.json"
    ],
    
    # 方式2: 目录扫描
    "directory_scan": {
        "enabled": True,
        "directory": "/Users/liucun/Desktop",
        "pattern": "**/*.json",
        "recursive": True,
        "exclude_patterns": ["**/temp/**", "**/cache/**"]
    },
    
    # 方式3: 子文件夹处理模式 (推荐)
    "subfolder_processing": {
        "enabled": True,
        "base_directory": "/Users/liucun/Desktop/yuancailiao",
        "exclude_folder_patterns": ["*_temp_pages"],  # 排除特定文件夹
        "output_in_source": True,  # 输出到源文件夹
        "create_output_subfolder": False
    }
}
```

### 性能配置

```python
PERFORMANCE_CONFIG = {
    "parallel_processing": {
        "enabled": True,
        "max_workers": 3,  # 建议值：CPU核心数 - 1
        "chunk_size": 5
    },
    "timeouts": {
        "single_file_timeout": 600,  # 10分钟
        "ocr_timeout": 120,          # 2分钟
        "image_processing_timeout": 60  # 1分钟
    }
}
```

### 错误处理配置

```python
ERROR_HANDLING_CONFIG = {
    "continue_on_error": True,  # 遇到错误继续处理其他文件
    "max_retries": 2,          # 失败重试次数
    "retry_delay": 2.0,        # 重试间隔
    "save_error_details": True  # 保存错误详情
}
```

## 🎯 配置模板

系统提供了三种预设配置：

### 1. 快速模式 (fast)
- 跳过OCR文本检测
- 适合快速预览
- 处理速度最快

### 2. 高质量模式 (high_quality)
- 开启所有功能
- 支持中文繁体
- 最低置信度阈值

### 3. 调试模式 (debug)
- 详细日志输出
- 保存中间结果
- 便于问题排查

在 `run_batch_preprocess.py` 中修改：
```python
ENVIRONMENT = "production"  # 可选：development, testing, production
```

## 📊 输出文件

处理完成后，会生成以下文件：

```
batch_processed/
├── file1_processed/
│   ├── file1_preprocessed.md
│   ├── file1_temp_images/
│   └── preprocess_report.json
├── file2_processed/
│   ├── file2_preprocessed.md
│   ├── file2_temp_images/
│   └── preprocess_report.json
└── batch_processing_report.json  # 总结报告
```

## 🔍 监控和调试

### 1. 实时监控

```bash
# 查看实时日志
tail -f batch_processed/preprocess.log

# 查看系统资源
top -p $(pgrep -f run_batch_preprocess.py)
```

### 2. 性能优化建议

```python
# 内存不足时
PERFORMANCE_CONFIG["parallel_processing"]["max_workers"] = 1

# CPU较多时
PERFORMANCE_CONFIG["parallel_processing"]["max_workers"] = os.cpu_count() - 1

# 处理大文件时
PERFORMANCE_CONFIG["timeouts"]["single_file_timeout"] = 1200  # 20分钟
```

### 3. 常见问题

**问题1：Tesseract未找到**
```bash
# macOS
brew install tesseract

# 更新配置中的路径
config.tesseract_path = "/opt/homebrew/bin/tesseract"
```

**问题2：内存不足**
```python
# 减少并行数
PERFORMANCE_CONFIG["parallel_processing"]["max_workers"] = 1

# 启用内存清理
PERFORMANCE_CONFIG["memory_management"]["cleanup_temp_files"] = True
```

**问题3：处理速度慢**
```python
# 快速模式
ENVIRONMENT = "testing"  # 跳过OCR

# 或者单独禁用OCR
config.text_detection_enabled = False
```

## 🎯 子文件夹处理模式

### 什么是子文件夹处理模式？

子文件夹处理模式是专门为以下场景设计的：
- 你有一个包含多个子文件夹的目录
- 每个子文件夹包含一个或多个JSON文件
- 你希望处理结果保存在原始子文件夹中，而不是创建新的输出目录

### 使用场景

```
yuancailiao/
├── 公司A-ESG报告/
│   ├── report.json
│   └── data.json
├── 公司B-ESG报告/
│   ├── esg_report.json
│   └── financial.json
├── 公司C-ESG报告/
│   └── annual_report.json
└── temp_pages/         # 这个会被排除
    └── cache.json
```

### 配置示例

```python
INPUT_CONFIG = {
    "subfolder_processing": {
        "enabled": True,
        "base_directory": "/Users/liucun/Desktop/yuancailiao",
        "exclude_folder_patterns": ["*_temp_pages", "*_backup"],
        "output_in_source": True,
        "create_output_subfolder": False
    }
}
```

### 处理结果

处理后，每个子文件夹将包含：
```
yuancailiao/
├── 公司A-ESG报告/
│   ├── report.json                    # 原始文件
│   ├── report_preprocessed.md         # 处理后的Markdown
│   ├── preprocess_report.json         # 处理报告
│   └── 公司A-ESG报告_temp_images/      # 图片文件
├── 公司B-ESG报告/
│   ├── esg_report.json
│   ├── esg_report_preprocessed.md
│   └── ...
└── batch_processing_report.json       # 总体处理报告
```

### 测试配置

运行测试脚本验证配置：
```bash
python test_subfolder_config.py
```

## 📈 批量处理示例

### 示例1：子文件夹处理模式 (推荐)

```python
INPUT_CONFIG = {
    "subfolder_processing": {
        "enabled": True,
        "base_directory": "/Users/liucun/Desktop/yuancailiao",
        "exclude_folder_patterns": ["*_temp_pages"],
        "output_in_source": True
    }
}
```

### 示例2：处理单个目录

```python
INPUT_CONFIG = {
    "specific_files": [],
    "directory_scan": {
        "enabled": True,
        "directory": "/Users/liucun/Desktop/esg_reports",
        "pattern": "*.json"
    }
}
```

### 示例3：处理特定类型文件

```python
INPUT_CONFIG = {
    "directory_scan": {
        "pattern": "**/*ESG*.json",  # 只处理包含ESG的文件
        "exclude_patterns": ["**/备份/**", "**/测试/**"]
    }
}
```

## 🛠️ 高级功能

### 1. 消融实验

```python
# 在配置中启用消融实验
config.apply_ablation("no_text_detection")
config.apply_ablation("high_confidence") 
```

### 2. 自定义处理流程

```python
# 只运行特定步骤
config.json_to_md_enabled = True
config.image_link_conversion_enabled = False
config.text_detection_enabled = True
```

### 3. 并行处理优化

```python
# 根据系统自动调整
import os
max_workers = min(os.cpu_count() - 1, len(input_files))
```

## 📋 检查清单

运行前请确认：

- [ ] 输入文件路径正确
- [ ] 输出目录有写入权限
- [ ] Tesseract正确安装
- [ ] 系统内存充足（建议4GB+）
- [ ] 配置参数合理

## 🚨 注意事项

1. **并行处理**：过多的并行线程可能导致内存不足
2. **OCR处理**：文本检测比较耗时，可以考虑禁用
3. **临时文件**：处理过程中会生成临时图片文件
4. **错误恢复**：启用重试机制可以提高成功率
5. **日志文件**：定期清理日志文件防止占用过多空间

## 🎉 完成

批量处理完成后，检查：
- 处理报告（`batch_processing_report.json`）
- 各文件的输出目录
- 错误日志（如果有）

如需帮助，请查看详细的错误日志或联系技术支持。 