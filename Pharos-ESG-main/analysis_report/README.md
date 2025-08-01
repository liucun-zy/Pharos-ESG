# ESG报告分析处理工具集

本文件夹包含用于处理ESG报告的完整工具链，从原始PDF到最终结构化数据的全流程处理工具。

## 📁 文件夹结构概览

```
analysis_report/
├── README.md                    # 本文档
├── 跨平台使用说明.md            # 跨平台部署指南
├── URL_FORMATS_README.md        # URL格式说明文档
│
├── 🔄 阶段1：初始数据处理工具（模块化）
│   └── preprocess_module/       # 预处理模块包
│       ├── __init__.py          # 模块初始化和公共接口
│       ├── config.py            # 配置管理（支持消融实验）
│       ├── processors.py        # 核心处理器类
│       ├── pipeline.py          # 处理管道和批量处理
│       ├── utils.py             # 工具函数和日志管理
│       ├── example_usage.py     # 使用示例和最佳实践
│       ├── json_to_md.py        # 原始脚本（兼容性保留）
│       ├── convert_image_links.py # 原始脚本（兼容性保留）
│       └── image_detector.py    # 原始脚本（兼容性保留）
│
├── 🔀 阶段2：并行处理工具
│   ├── extract_title.py         # 目录标题提取（并行分支1）
│   └── group_by_page_idx.py     # 按页面索引分组（并行分支2）
│
├── 🎯 阶段3：标题对齐工具
│   ├── align_title.py           # 标题对齐处理主程序
│   └── deepseek_title.py        # DeepSeek API智能标题匹配
│
├── 🧠 阶段4：智能分析工具
│   ├── md_to_json.py            # Markdown转JSON格式
│   ├── image_clustering.py      # 图像聚类工具
│   ├── detectVLM.py            # VLM图像分析主程序
│   └── split_cluster.py         # 聚类数据拆分重组
│
├── 🌐 阶段5：跨平台查看工具
│   ├── fix_cross_platform_urls.py # 跨平台URL修复
│   └── start_local_server.py    # 本地HTTP服务器
│
├── 📊 通用工具
│   └── add_metadata.py          # 通用元数据添加工具
│
└── 📄 示例文件（extract_title.py专用）
    ├── sample1base64.txt        # 标题提取示例图像1的Base64编码
    ├── sample2base64.txt        # 标题提取示例图像2的Base64编码
    ├── prompt样例1.png          # 标题提取提示词示例图1
    └── prompt样例2.png          # 标题提取提示词示例图2
```

## 🔄 完整处理流程

### 阶段1：初始数据处理
```bash
# 1. JSON转Markdown
python json_to_md.py
# 输入：原始JSON数据
# 输出：Markdown格式文件

# 2. 图片链接格式转换
python convert_image_links.py
# 输入：Markdown文件
# 输出：标准化图片链接格式的Markdown

# 3. 无文本图片过滤
python image_detector.py
# 输入：Markdown文件
# 输出：删除无文本图片链接后的Markdown
```

### 阶段2：并行处理（标题提取 + 页面分组）
```bash
# 4a. 目录标题提取（并行分支1）
python extract_title.py
# 输入：PDF目录页面图片
# 输出：titles.json

# 4b. 页面分组（并行分支2）
python group_by_page_idx.py
# 输入：处理后的Markdown文件
# 输出：按页面分组的Markdown文件
```

### 阶段3：标题对齐处理
```bash
# 5. 标题对齐处理
python align_title.py
# 输入：titles.json + 分组后的Markdown
# 输出：标题对齐后的Markdown
# 注：内部会调用deepseek_title.py进行智能对齐
```

### 阶段4：数据结构化与智能分析
```bash
# 6. Markdown转JSON
python md_to_json.py
# 输入：对齐后的Markdown
# 输出：结构化JSON数据

# 7. 图像聚类
python image_clustering.py
# 输入：结构化JSON
# 输出：聚类后的JSON

# 8. VLM图像分析
python detectVLM.py
# 输入：聚类后的JSON
# 输出：包含VLM分析结果的JSON

# 9. 数据拆分重组
python split_cluster.py
# 输入：VLM分析后的JSON
# 输出：按页面组织的最终JSON数据
```

### 阶段5：跨平台图片查看（可选）
```bash
# 10. 跨平台URL修复（如需要）
python fix_cross_platform_urls.py
# 功能：适应Mac和Windows的不同URL格式要求

# 11. 启动HTTP服务器查看图片
python start_local_server.py
# 功能：通过本地HTTP服务器访问JSON中的图片URL
```

## 📋 核心工具详细说明

### 🖼️ VLM图像分析 (`detectVLM.py`)
**功能**：使用视觉语言模型分析图像内容
- **输入**：聚类后的JSON文件，包含图像块
- **输出**：包含图像分析结果的JSON文件
- **特性**：
  - 支持7种图像类型识别（表格图、流程图、统计图等）
  - 多线程处理，支持API重试机制
  - 生成4种URL格式（markdown_url, file_url, relative_path, http_url）
  - 缓存机制提高处理效率

### 🔗 图像聚类 (`image_clustering.py`)
**功能**：将相邻的文本和图像块进行智能聚类
- **输入**：标准JSON格式的块数据
- **输出**：聚类后的JSON，包含cluster块
- **聚类规则**：
  - 相邻文本块自动合并
  - 图像与相邻文本形成语义单元
  - 保持原始reading_order

### 📄 标题提取与对齐

#### `extract_title.py` - 标题提取
**功能**：从PDF目录页面提取标题结构
- **输入**：目录页面图片
- **输出**：titles.json（层级化标题结构）
- **示例文件**：
  - `sample1base64.txt` / `sample2base64.txt`：标题提取的示例图像Base64编码
  - `prompt样例1.png` / `prompt样例2.png`：提示词示例图片，展示标题提取的预期效果
- **特性**：
  - 智能识别标题层级
  - 支持篇标签处理
  - 多示例引导提取（使用示例文件进行few-shot学习）

#### `align_title.py` - 标题对齐
**功能**：将提取的标题结构与内容进行智能对齐
- **输入**：titles.json + 分组后的Markdown文件
- **输出**：标题对齐后的Markdown文件
- **内部调用**：`deepseek_title.py`进行智能标题匹配
- **特性**：
  - 自动匹配标题与内容
  - 智能层级调整
  - 支持标题缺失补全

### 🌐 HTTP服务 (`start_local_server.py`)
**功能**：启动本地HTTP服务器以查看图片
- **端口**：8000
- **支持**：跨域访问，中文路径
- **用途**：让JSON中的http_url链接可以直接点击查看

## 🔧 配置要求

### API配置
```python
# detectVLM.py 中的API配置
API_CONFIG = {
    "api_key": "your_api_key_here",
    "api_url": "https://api.siliconflow.cn/v1/chat/completions",
    "model": "Qwen/Qwen2.5-VL-72B-Instruct",
}
```

### 路径配置
大多数脚本使用硬编码路径，使用前需要修改为实际路径：
```python
# 示例路径配置
input_path = "/Users/liucun/Desktop/report_analysis/..."
output_path = "/Users/liucun/Desktop/report_analysis/..."
```

## 📊 数据格式规范

### 完整JSON文件结构（含元数据）
```json
{
  "metadata": {
    "stock_code": "300497.SZ",
    "company_name": "富祥药业",
    "report_year": 2024,
    "report_name": "2024年度环境、社会及公司治理(ESG)报告",
    "report_type": "环境、社会及公司治理(ESG)报告",
    "original_filename": "300497.SZ-富祥药业-2024年度环境、社会及公司治理(ESG)报告_grouped.json",
    "processing_timestamp": "2024-12-20 15:30:25",
    "file_size_bytes": 529964,
    "data_source": "ESG_REPORT_PROCESSING"
  },
  "pages": [...]  // 或 "data": [...] 根据文件类型
}
```

### JSON块结构
```json
{
  "h1": "一级标题",
  "h2": "二级标题", 
  "h3": "三级标题",
  "h4": "四级标题",
  "data_type": "text|image<表格图、流程图、统计图...>|table|",
  "data": "内容数据",
  "reading_order": 0,
  "page_idx": 1
}
```

### 图像块附加字段
```json
{
  "image_markdown_url": "![](path/to/image.jpg)",
  "image_file_url": "file:///absolute/path/to/image.jpg",
  "image_relative_path": "relative/path/to/image.jpg", 
  "image_http_url": "http://localhost:8000/encoded/path"
}
```

### VLM分析结果
```json
{
  "data_type": "image<image[1][表格图]>",
  "data": "VLM分析的图像内容描述"
}
```

## 🚀 快速开始

### 1. 环境准备
```bash
pip install requests pillow pytesseract pathlib tenacity
```

### 2. 基础使用
```bash
# 处理单个报告的完整流程
cd analysis_report

# 第一阶段：初始数据处理（推荐使用模块化方式）
# 方式1: 使用模块化管道（推荐）
from preprocess_module import quick_preprocess
quick_preprocess(input_json_path, output_dir)

# 方式2: 使用原始脚本（兼容性）
python preprocess_module/json_to_md.py
python preprocess_module/convert_image_links.py  
python preprocess_module/image_detector.py

# 第二阶段：并行处理
python extract_title.py           # 标题提取（并行1）
python group_by_page_idx.py       # 页面分组（并行2）

# 第三阶段：标题对齐
python align_title.py             # 标题对齐（内部调用deepseek_title.py）

# 第四阶段：智能分析
python md_to_json.py              # Markdown转JSON
python image_clustering.py        # 图像聚类
python detectVLM.py               # VLM图像分析
python split_cluster.py           # 数据拆分重组

# 第五阶段：跨平台查看（可选）
python fix_cross_platform_urls.py # 跨平台URL修复
python start_local_server.py      # HTTP服务器查看图片

# 通用工具：为JSON文件添加元数据
python add_metadata.py report.json        # 单文件处理
python add_metadata.py /path/to/reports/  # 批量处理目录
```

### 3. 跨平台部署
参考 `跨平台使用说明.md` 获取详细的跨平台部署指南。

## 🛠️ 按处理阶段分类的工具

### 🔄 阶段1：初始数据处理工具（模块化）
- `preprocess_module/` - **工程化预处理模块包**
  - `PreprocessPipeline` - 主要处理管道类
  - `PreprocessConfig` - 配置管理（支持消融实验）
  - `JsonToMarkdownProcessor` - JSON转Markdown处理器
  - `ImageLinkConverter` - 图片链接转换处理器  
  - `ImageTextDetector` - 图片文本检测处理器
  - `BatchPreprocessPipeline` - 批量处理管道
  - `AblationExperimentRunner` - 消融实验运行器

### 🔀 阶段2：并行处理工具
- `extract_title.py` - 从目录页面提取标题结构（并行分支1）
- `group_by_page_idx.py` - 按页面索引重新组织内容（并行分支2）

### 🎯 阶段3：标题对齐工具
- `align_title.py` - 将提取的标题与内容进行智能对齐
- `deepseek_title.py` - 使用DeepSeek API进行智能标题匹配

### 🧠 阶段4：智能分析工具
- `md_to_json.py` - 将Markdown转换为结构化JSON
- `image_clustering.py` - 智能聚类相关的文本和图像块
- `detectVLM.py` - 主要的VLM图像分析工具
- `split_cluster.py` - 将聚类数据拆分为页面级组织

### 🌐 阶段5：跨平台查看工具
- `fix_cross_platform_urls.py` - 修复跨平台URL编码问题
- `start_local_server.py` - HTTP服务器，用于查看图片

### 📊 通用工具
- `add_metadata.py` - **通用元数据添加工具**
  - 自动从文件名提取股票代码、公司名称、报告年份等元数据
  - 支持单文件和批量处理
  - 支持多种JSON结构格式
  - 自动备份原文件
  - 命令行界面，易于集成到处理流程中

## 🏗️ 模块化特性（阶段1预处理）

### 🔧 工程化设计
- **配置驱动**: 支持JSON配置文件，易于管理和版本控制
- **模块化架构**: 每个处理器独立，支持单独使用和组合
- **错误处理**: 完善的异常处理和恢复机制
- **日志记录**: 详细的处理日志和性能监控
- **文件备份**: 自动备份原文件，支持回滚

### 🧪 消融实验支持
```python
# 预定义的消融实验配置
experiments = [
    "no_text_detection",      # 禁用文本检测
    "no_image_validation",    # 禁用图片验证
    "minimal_processing",     # 最小化处理
    "high_confidence",        # 高置信度阈值
    "low_confidence"          # 低置信度阈值
]

# 运行消融实验
runner = AblationExperimentRunner(base_config, experiments)
results = runner.run_experiments(input_json, output_dir)
```

### 📊 批量处理
```python
# 批量处理多个文件
batch_pipeline = BatchPreprocessPipeline(config)
results = batch_pipeline.run_batch(input_files, output_dir)
```

### ⚙️ 灵活配置
```python
# 自定义配置
config = PreprocessConfig(
    confidence_threshold=50.0,    # OCR置信度阈值
    min_text_length=5,           # 最小文本长度
    log_level="DEBUG",           # 日志级别
    experiment_name="custom"     # 实验名称
)
```

## 📊 元数据管理

### 自动元数据提取
系统会自动从文件名中提取以下元数据信息：

| 字段 | 说明 | 示例 |
|------|------|------|
| `stock_code` | 股票代码 | "300497.SZ" |
| `company_name` | 公司名称 | "富祥药业" |
| `report_year` | 报告年份 | 2024 |
| `report_name` | 完整报告名称 | "2024年度环境、社会及公司治理(ESG)报告" |
| `report_type` | 报告类型 | "环境、社会及公司治理(ESG)报告" |
| `processing_timestamp` | 处理时间戳 | "2024-12-20 15:30:25" |
| `file_size_bytes` | 文件大小 | 529964 |
| `data_source` | 数据来源标识 | "ESG_REPORT_PROCESSING" |

### 文件命名规范
为确保元数据正确提取，请遵循以下命名规范：
```
{股票代码}-{公司名称}-{年份}年度{报告类型}[_后缀].json
```

**示例**：
- `300497.SZ-富祥药业-2024年度环境、社会及公司治理(ESG)报告_grouped.json`
- `000001.SZ-平安银行-2023年度可持续发展报告_vlm.json`
- `BABA.US-阿里巴巴-2024年度环境报告.json`

### 元数据添加工具使用
```bash
# 单文件处理
python add_metadata.py report.json

# 批量处理目录
python add_metadata.py /path/to/reports/

# 指定输出目录
python add_metadata.py input.json -o output_with_metadata.json

# 批量处理特定模式文件
python add_metadata.py /reports/ -p "*_grouped.json"

# 不创建备份文件
python add_metadata.py report.json --no-backup

# 详细输出模式
python add_metadata.py report.json -v
```

## 🎯 最佳实践

### 1. 处理顺序
严格按照5个阶段的顺序执行：
1. **初始数据处理**：json_to_md → convert_image_links → image_detector
2. **并行处理**：extract_title（标题提取）与 group_by_page_idx（页面分组）可并行执行
3. **标题对齐**：align_title（内部调用deepseek_title）
4. **智能分析**：md_to_json → image_clustering → detectVLM → split_cluster
5. **跨平台查看**：fix_cross_platform_urls → start_local_server（可选）

### 2. 路径管理
- 使用绝对路径避免路径错误
- 图片目录和JSON文件保持同级
- 遵循命名规范：`报告名_功能.json`

### 3. 错误处理
- 检查API配置和网络连接
- 验证输入文件格式和内容
- 监控处理日志和错误信息

### 4. 性能优化
- VLM分析支持缓存，避免重复处理
- 大批量处理时注意API限制
- 图像文件大小控制在合理范围

## 📚 参考文档

- `URL_FORMATS_README.md` - 详细的URL格式说明
- `跨平台使用说明.md` - 跨平台部署指南
- 各脚本文件内的docstring和注释

## 🤝 贡献指南

1. 添加新功能时更新本README
2. 保持代码注释和文档同步
3. 遵循现有的命名和格式规范
4. 测试跨平台兼容性

## 📝 更新日志

- **v1.0** - 初始版本，包含基础处理流程
- **v1.1** - 添加VLM图像分析功能
- **v1.2** - 支持图像聚类和智能分组
- **v1.3** - 完善跨平台支持和URL格式化
- **v1.4** - 优化处理流程和错误处理机制 