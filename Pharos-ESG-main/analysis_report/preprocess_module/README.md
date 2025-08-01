# 预处理模块 (Preprocess Module)

## 概述

预处理模块是ESG报告分析系统的第一阶段处理组件，负责将原始JSON数据转换为可用于后续分析的格式。该模块采用工程化的模块化设计，支持消融实验、批量处理和灵活配置。

## 核心功能

- **JSON转Markdown**: 将结构化JSON数据转换为Markdown格式
- **图片链接处理**: 提取、转换和验证图片链接
- **文本检测**: 使用OCR技术检测图片中的文本内容
- **消融实验**: 支持多种实验配置用于参数优化
- **批量处理**: 支持大规模文件批量处理
- **详细统计**: 提供完整的处理统计和报告

## 模块架构

### 文件结构

```
preprocess_module/
├── __init__.py              # 模块公共接口，提供quick_preprocess()函数
├── config.py                # 配置管理，支持消融实验配置
├── processors.py            # 三个核心处理器实现
├── pipeline.py              # 处理管道，组合处理器形成完整流程
├── utils.py                 # 工具函数，日志、统计、文件操作等
├── example_usage.py         # 使用示例和最佳实践
├── json_to_md.py           # 原始脚本（向后兼容）
├── convert_image_links.py  # 原始脚本（向后兼容）
└── image_detector.py       # 原始脚本（向后兼容）
```

### 核心组件

#### 1. 配置管理 (`config.py`)

**PreprocessConfig类**：统一管理所有处理参数

```python
class PreprocessConfig:
    """预处理配置类"""
    
    # 核心配置项
    experiment_name: str = "default"
    base_dir: str = "."
    output_dir: str = "./output"
    
    # 处理步骤开关
    json_to_md_enabled: bool = True
    image_link_conversion_enabled: bool = True
    text_detection_enabled: bool = True
    
    # OCR配置
    ocr_confidence_threshold: float = 0.5
    ocr_min_text_length: int = 3
    ocr_languages: List[str] = ["chi_sim", "eng"]
    
    # 图片处理配置
    image_validation_enabled: bool = True
    image_copy_enabled: bool = True
    supported_image_formats: List[str] = [".jpg", ".jpeg", ".png", ".bmp", ".gif"]
    
    # 日志配置
    log_level: str = "INFO"
    log_to_file: bool = True
    log_file_path: str = "preprocess.log"
```

**消融实验支持**：
- `no_text_detection`: 禁用OCR文本检测
- `no_image_validation`: 跳过图片文件验证
- `minimal_processing`: 最小化处理（仅JSON转MD）
- `high_confidence`: 高置信度OCR阈值
- `low_confidence`: 低置信度OCR阈值

#### 2. 处理器 (`processors.py`)

**JsonToMarkdownProcessor**：JSON转Markdown处理器

```python
class JsonToMarkdownProcessor:
    """JSON转Markdown处理器"""
    
    def process(self, input_json_path: str, output_md_path: str) -> Dict[str, Any]:
        """
        处理逻辑：
        1. 加载JSON数据并验证格式
        2. 解析页面、图片、表格等结构化数据
        3. 按页面顺序生成Markdown内容
        4. 处理图片引用和表格格式
        5. 保存Markdown文件
        """
```

**技术细节**：
- 支持多种JSON结构（pages、images、tables）
- 自动处理Base64编码的图片数据
- 智能格式化表格和列表
- 保持原始数据的层次结构

**ImageLinkConverter**：图片链接转换器

```python
class ImageLinkConverter:
    """图片链接转换器"""
    
    def process(self, md_file_path: str, images_dir: str) -> Dict[str, Any]:
        """
        处理逻辑：
        1. 解析Markdown文件中的图片引用
        2. 提取Base64编码的图片数据
        3. 将图片数据保存为独立文件
        4. 更新Markdown中的图片链接
        5. 验证图片文件完整性
        """
```

**技术细节**：
- 支持多种图片格式（JPEG、PNG、BMP、GIF）
- Base64解码和图片格式检测
- 自动生成唯一文件名避免冲突
- 图片完整性验证（文件大小、格式）
- 支持相对路径和绝对路径

**ImageTextDetector**：图片文本检测器

```python
class ImageTextDetector:
    """图片文本检测器"""
    
    def process(self, md_file_path: str, images_dir: str) -> Dict[str, Any]:
        """
        处理逻辑：
        1. 扫描图片目录获取所有图片文件
        2. 使用Tesseract OCR检测图片中的文本
        3. 根据置信度阈值过滤文本内容
        4. 更新Markdown文件，移除纯图片内容
        5. 生成文本检测报告
        """
```

**技术细节**：
- 集成Tesseract OCR引擎
- 支持中英文文本检测
- 可配置置信度阈值和最小文本长度
- 智能过滤纯装饰性图片
- 详细的OCR结果统计

#### 3. 处理管道 (`pipeline.py`)

**PreprocessPipeline**：主处理管道

```python
class PreprocessPipeline:
    """预处理管道"""
    
    def run(self, input_json_path: str, output_dir: str) -> Dict[str, Any]:
        """
        完整处理流程：
        1. 输入验证和路径构建
        2. 步骤1: JSON转Markdown
        3. 步骤2: 图片链接转换
        4. 步骤3: 图片文本检测
        5. 生成处理报告
        """
```

**BatchPreprocessPipeline**：批量处理管道

```python
class BatchPreprocessPipeline:
    """批量处理管道"""
    
    def run_batch(self, input_files: List[str], output_base_dir: str) -> Dict[str, Any]:
        """
        批量处理逻辑：
        1. 为每个文件创建独立输出目录
        2. 并行或串行处理多个文件
        3. 错误隔离和恢复
        4. 生成批量处理报告
        """
```

**AblationExperimentRunner**：消融实验运行器

```python
class AblationExperimentRunner:
    """消融实验运行器"""
    
    def run_experiments(self, input_json_path: str, output_base_dir: str) -> Dict[str, Any]:
        """
        实验运行逻辑：
        1. 加载多个实验配置
        2. 为每个配置创建独立实验环境
        3. 并行运行实验避免相互干扰
        4. 收集和对比实验结果
        """
```

#### 4. 工具函数 (`utils.py`)

**日志管理**：
```python
def setup_logging(log_level: str = "INFO", log_file: str = None, logger_name: str = None) -> logging.Logger:
    """
    设置统一的日志格式和处理器
    - 支持控制台和文件双重输出
    - 自定义日志级别和格式
    - 线程安全的日志记录
    """
```

**统计管理**：
```python
class ProcessingStats:
    """处理统计类"""
    
    def __init__(self):
        self.start_time = time.time()
        self.processed_files = 0
        self.successful_operations = 0
        self.failed_operations = 0
        self.errors = []
        self.warnings = []
```

**文件操作**：
```python
def ensure_directory(path: str) -> None:
    """确保目录存在，支持递归创建"""

def backup_file(file_path: str, backup_dir: str) -> str:
    """创建文件备份，支持版本管理"""

def validate_paths(paths: Dict[str, str]) -> List[str]:
    """验证路径有效性，返回错误列表"""
```

## 处理流程详解

### 步骤1: JSON转Markdown

**输入**: 结构化JSON文件
**输出**: Markdown文件

**处理逻辑**：
1. **JSON解析**: 使用`json.load()`加载文件，验证JSON格式
2. **数据结构分析**: 识别pages、images、tables等关键字段
3. **内容提取**: 按页面顺序提取文本、图片、表格内容
4. **Markdown生成**: 
   - 页面标题转换为Markdown标题
   - 图片引用转换为`![]()`格式
   - 表格数据转换为Markdown表格
   - 保持原始层次结构

**技术要点**：
- 支持嵌套JSON结构
- 自动处理特殊字符转义
- 保持图片的Base64编码格式
- 智能识别表格结构

### 步骤2: 图片链接转换

**输入**: 包含Base64图片的Markdown文件
**输出**: 独立图片文件 + 更新的Markdown文件

**处理逻辑**：
1. **图片提取**: 使用正则表达式匹配`![](data:image/...)`格式
2. **Base64解码**: 解码图片数据并识别图片格式
3. **文件保存**: 
   - 生成唯一文件名（基于内容哈希）
   - 创建图片目录结构
   - 保存图片文件到磁盘
4. **链接更新**: 将Markdown中的Base64链接替换为文件路径
5. **完整性验证**: 验证保存的图片文件完整性

**技术要点**：
- 支持JPEG、PNG、BMP、GIF等格式
- 使用SHA256哈希避免重复保存
- 自动检测图片格式和质量
- 支持相对路径和绝对路径

### 步骤3: 图片文本检测

**输入**: Markdown文件 + 图片目录
**输出**: 过滤后的Markdown文件 + OCR报告

**处理逻辑**：
1. **图片扫描**: 遍历图片目录，获取所有图片文件
2. **OCR处理**: 
   - 使用Tesseract引擎进行文本识别
   - 支持中文和英文识别
   - 获取文本内容和置信度
3. **文本过滤**: 
   - 根据置信度阈值过滤低质量文本
   - 根据文本长度过滤无意义内容
   - 识别纯装饰性图片
4. **内容更新**: 从Markdown中移除纯图片内容的引用
5. **报告生成**: 生成详细的OCR检测报告

**技术要点**：
- 集成Tesseract OCR引擎
- 支持多语言文本检测
- 可配置的置信度和长度阈值
- 智能过滤算法
- 详细的统计报告

## 使用指南

### 快速开始

```python
from preprocess_module import quick_preprocess

# 最简单的使用方式
result = quick_preprocess(
    input_json_path="data.json",
    output_dir="./output"
)
```

### 自定义配置

```python
from preprocess_module import PreprocessConfig, PreprocessPipeline

# 创建自定义配置
config = PreprocessConfig()
config.experiment_name = "high_quality_ocr"
config.ocr_confidence_threshold = 0.8
config.ocr_min_text_length = 5
config.log_level = "DEBUG"

# 运行处理管道
pipeline = PreprocessPipeline(config)
result = pipeline.run("data.json", "./output")
```

### 批量处理

```python
from preprocess_module import BatchPreprocessPipeline, PreprocessConfig

config = PreprocessConfig()
batch_pipeline = BatchPreprocessPipeline(config)

input_files = ["data1.json", "data2.json", "data3.json"]
result = batch_pipeline.run_batch(input_files, "./batch_output")
```

### 消融实验

```python
from preprocess_module import AblationExperimentRunner, PreprocessConfig

base_config = PreprocessConfig()
experiment_configs = [
    "no_text_detection",
    "high_confidence", 
    "low_confidence",
    "minimal_processing"
]

runner = AblationExperimentRunner(base_config, experiment_configs)
results = runner.run_experiments("data.json", "./experiments")
```

### 单步处理（调试）

```python
from preprocess_module import PreprocessPipeline, PreprocessConfig

config = PreprocessConfig()
pipeline = PreprocessPipeline(config)

# 只运行JSON转Markdown
result = pipeline.run_single_step(
    "json_to_md",
    input_json_path="data.json",
    output_md_path="output.md"
)
```

## 配置参数详解

### 核心配置

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `experiment_name` | str | "default" | 实验名称，用于标识不同的处理配置 |
| `base_dir` | str | "." | 基础工作目录 |
| `output_dir` | str | "./output" | 输出目录 |

### 处理步骤控制

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `json_to_md_enabled` | bool | True | 是否启用JSON转Markdown |
| `image_link_conversion_enabled` | bool | True | 是否启用图片链接转换 |
| `text_detection_enabled` | bool | True | 是否启用文本检测 |

### OCR配置

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `ocr_confidence_threshold` | float | 0.5 | OCR置信度阈值（0-1） |
| `ocr_min_text_length` | int | 3 | 最小文本长度 |
| `ocr_languages` | List[str] | ["chi_sim", "eng"] | OCR识别语言 |

### 图片处理配置

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `image_validation_enabled` | bool | True | 是否启用图片验证 |
| `image_copy_enabled` | bool | True | 是否复制图片文件 |
| `supported_image_formats` | List[str] | [".jpg", ".jpeg", ".png", ".bmp", ".gif"] | 支持的图片格式 |

### 日志配置

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `log_level` | str | "INFO" | 日志级别 |
| `log_to_file` | bool | True | 是否记录到文件 |
| `log_file_path` | str | "preprocess.log" | 日志文件路径 |

## 消融实验详解

### 预定义实验配置

#### 1. no_text_detection
- **目的**: 测试禁用OCR文本检测的影响
- **配置**: `text_detection_enabled = False`
- **用途**: 评估OCR处理的必要性

#### 2. no_image_validation
- **目的**: 测试跳过图片验证的性能影响
- **配置**: `image_validation_enabled = False`
- **用途**: 评估验证步骤的开销

#### 3. minimal_processing
- **目的**: 最小化处理，仅进行基础转换
- **配置**: 
  - `image_link_conversion_enabled = False`
  - `text_detection_enabled = False`
- **用途**: 建立性能基线

#### 4. high_confidence
- **目的**: 高置信度OCR设置
- **配置**: 
  - `ocr_confidence_threshold = 0.8`
  - `ocr_min_text_length = 5`
- **用途**: 提高OCR质量，减少噪声

#### 5. low_confidence
- **目的**: 低置信度OCR设置
- **配置**: 
  - `ocr_confidence_threshold = 0.2`
  - `ocr_min_text_length = 1`
- **用途**: 最大化文本检测覆盖率

### 实验结果分析

每个实验会生成详细的报告，包括：
- 处理时间统计
- 文件处理数量
- 错误和警告信息
- OCR检测结果
- 图片处理统计

## 错误处理和恢复

### 错误类型

1. **输入验证错误**: 文件不存在、格式错误等
2. **处理错误**: OCR失败、图片解码错误等
3. **输出错误**: 磁盘空间不足、权限问题等

### 恢复机制

1. **文件备份**: 自动创建输入文件备份
2. **断点续传**: 支持从失败点恢复处理
3. **错误隔离**: 单个文件错误不影响批量处理
4. **详细日志**: 记录所有错误信息用于调试

### 最佳实践

1. **配置验证**: 处理前验证所有配置参数
2. **路径检查**: 确保输入文件存在，输出目录可写
3. **资源监控**: 监控磁盘空间和内存使用
4. **定期备份**: 重要数据定期备份
5. **日志管理**: 定期清理日志文件

## 性能优化

### 处理性能

- **并行处理**: 支持多文件并行处理
- **内存管理**: 大文件流式处理，避免内存溢出
- **缓存机制**: 重复内容检测和缓存
- **资源复用**: 复用OCR引擎实例

### 存储优化

- **图片去重**: 基于内容哈希避免重复存储
- **格式转换**: 自动选择最优图片格式
- **压缩处理**: 支持图片质量调整和压缩

### 配置优化

- **参数调优**: 根据数据特点调整OCR参数
- **步骤优化**: 根据需求启用/禁用处理步骤
- **批量大小**: 优化批量处理的文件数量

## 扩展开发

### 添加新处理器

1. 继承`BaseProcessor`类
2. 实现`process()`方法
3. 添加配置参数
4. 更新管道逻辑

### 添加新实验配置

1. 在`config.py`中定义新的消融配置
2. 实现配置应用逻辑
3. 添加实验文档

### 集成新功能

1. 遵循现有的代码结构
2. 添加相应的测试用例
3. 更新文档和示例

## 故障排除

### 常见问题

1. **Tesseract未安装**: 安装Tesseract OCR引擎
2. **中文识别失败**: 安装中文语言包
3. **内存不足**: 调整批量处理大小
4. **权限问题**: 检查文件和目录权限

### 调试技巧

1. **启用DEBUG日志**: 设置`log_level = "DEBUG"`
2. **单步调试**: 使用`run_single_step()`方法
3. **配置验证**: 使用`config.validate()`检查配置
4. **统计分析**: 查看处理统计报告

## 版本兼容性

### 向后兼容

- 保留原始脚本文件
- 支持旧版本配置格式
- 提供迁移工具和指南

### 依赖管理

- Python 3.7+
- Tesseract OCR 4.0+
- PIL/Pillow
- 其他依赖见requirements.txt

## 许可证

本模块遵循MIT许可证，详见LICENSE文件。

---

*最后更新: 2024年* 

---

***From Reports to Insights, From Vision to Value***