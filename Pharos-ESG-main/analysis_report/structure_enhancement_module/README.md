# ESG报告结构增强模块 (Structure Enhancement Module)

## 📋 模块概述

结构增强模块是ERLIC (ESG Reports Linearized in Context) 系统的第二阶段核心组件，专门负责ESG报告的标题结构化处理。该模块将预处理阶段产生的Markdown文档进行深度结构化，通过智能标题提取、页面分组、标题对齐等技术，将非结构化的报告内容转换为具有清晰层级关系的结构化文档。

### 🎯 核心功能

1. **标题提取 (Title Extraction)**: 从PDF目录页面图像中提取层级化标题结构
2. **页面分组 (Page Grouping)**: 按页面索引重新组织内容，优化阅读体验
3. **智能标题对齐 (Title Alignment)**: 将提取的标题与内容进行语义匹配和对齐
4. **结构优化 (Structure Enhancement)**: 统一处理管道，支持批量处理和消融实验

### 🏗️ 模块化设计特性

- **高度模块化**: 每个处理器独立设计，支持单独使用和灵活组合
- **配置驱动**: 统一配置管理，支持多种处理策略和参数调优
- **工程化架构**: 完善的错误处理、日志记录、性能监控
- **消融实验支持**: 内置7种预定义实验配置，支持算法效果评估
- **API抽象**: 统一的API客户端接口，支持多种后端模型

## 📁 模块结构

```
structure_enhancement_module/
├── __init__.py                 # 模块初始化和公共接口
├── config.py                   # 配置管理类，支持消融实验
├── utils.py                    # 工具函数集合
├── api_clients.py              # API客户端抽象层
├── processors.py               # 核心处理器类 (待创建)
├── pipeline.py                 # 处理管道和批量处理 (待创建)
├── README.md                   # 本文档
│
├── 🔄 原始脚本 (兼容性保留)
├── align_title.py              # 标题对齐主程序
├── deepseek_title.py           # DeepSeek API智能匹配
├── extract_title.py            # 目录标题提取
├── group_by_page_idx.py        # 页面内容分组
│
└── 📄 示例文件
    ├── sample1base64.txt       # 标题提取示例1
    ├── sample2base64.txt       # 标题提取示例2
    ├── prompt样例1.png         # 提示词示例图1
    └── prompt样例2.png         # 提示词示例图2
```

## 🔧 技术架构详解

### 1. 配置管理系统 (`config.py`)

#### 核心配置类: `StructureEnhancementConfig`

```python
@dataclass
class StructureEnhancementConfig:
    # 基础配置
    experiment_name: str = "default"
    base_dir: str = ""
    output_dir: str = ""
    
    # API配置 (支持DeepSeek和Qwen VL)
    deepseek_api_key: str = "..."
    qwen_api_key: str = "..."
    
    # 标题匹配算法参数
    title_similarity_threshold: float = 0.8
    fuzzy_match_enabled: bool = True
    use_llm_matching: bool = True
    
    # 标题层级控制
    max_title_levels: int = 4
    default_title_level: int = 3
    auto_adjust_levels: bool = True
```

#### 消融实验配置

模块内置7种预定义消融实验，支持算法组件的独立评估：

| 实验名称 | 描述 | 关键参数变化 |
|---------|------|-------------|
| `no_llm_matching` | 禁用LLM智能匹配 | `use_llm_matching: False` |
| `no_fuzzy_match` | 禁用模糊匹配 | `fuzzy_match_enabled: False` |
| `strict_matching` | 严格匹配模式 | `similarity_threshold: 0.95` |
| `high_similarity` | 高相似度阈值 | `similarity_threshold: 0.9` |
| `low_similarity` | 低相似度阈值 | `similarity_threshold: 0.6` |
| `no_auto_insert` | 禁用自动插入 | `auto_insert_missing_titles: False` |
| `minimal_processing` | 最小化处理 | 禁用所有智能功能 |

```python
# 使用消融实验
config = StructureEnhancementConfig()
config.apply_ablation("no_llm_matching")
```

### 2. API客户端抽象层 (`api_clients.py`)

#### 统一API接口设计

```python
class APIClientBase(ABC):
    @abstractmethod
    def call_api(self, messages: List[Dict], **kwargs) -> Dict[str, Any]:
        """调用API的抽象方法"""
        pass
```

#### DeepSeek V3客户端 - 智能标题匹配

**核心功能**:
- 标题候选选择: 从多个候选标题中选择最佳匹配
- 插入位置分析: 确定缺失标题的最佳插入位置

**技术特点**:
- 基于tenacity的自动重试机制
- 429错误的智能退避策略
- 双场景提示词优化 (选择 vs 插入)

```python
client = DeepSeekClient(config.get_api_config("deepseek"))
selected = client.select_title(content, candidates)
position = client.find_insert_position(content, target_title)
```

#### DeepSeek R1客户端 - 专业插入位置分析

**核心功能**:
- 专业插入位置分析: 专门优化的标题插入位置判断
- 上下文关系分析: 详细的标题与内容关系评估

**技术特点**:
- 专门针对插入位置分析优化的提示词
- 内容长度自动限制，避免API调用错误
- 多种位置表达方式的智能解析
- 支持详细的上下文关系分析

```python
r1_client = DeepSeekR1Client(config.get_api_config("deepseek_r1"))
position = r1_client.find_insert_position(content, target_title)
analysis = r1_client.analyze_title_context(content, target_title)
```

#### Qwen VL客户端 - 图像标题提取

**核心功能**:
- 多模态图像分析: 从目录页面提取层级化标题
- 智能图片压缩: 413错误时自动压缩重试
- Few-shot学习: 基于示例图片的标题提取

**技术特点**:
- 自适应图片压缩算法
- Base64编码优化
- 多示例引导的提取策略

```python
client = QwenVLClient(config.get_api_config("qwen"))
titles_json = client.extract_titles_from_image(image_path, sample_files)
```

### 3. 工具函数库 (`utils.py`)

#### 文本处理算法

**中文文本标准化**:
```python
def normalize_title(title: str) -> str:
    """标准化标题文本，只保留中文字符并移除空白"""
    chinese_only = extract_chinese(title)
    return re.sub(r'\s+', '', chinese_only)
```

**多层级标题匹配算法**:
```python
def is_title_match(md_title: str, json_title: str, threshold: float = 0.8) -> Tuple[bool, float, bool]:
    """
    三层匹配策略：
    1. 完全匹配 (优先级最高)
    2. 模糊匹配 (RapidFuzz算法)
    3. 包含关系 (语义包含)
    """
```

#### 性能监控工具

**统计信息追踪**:
```python
class ProcessingStats:
    def __init__(self):
        self.successful_operations = 0
        self.failed_operations = 0
        self.warnings = []
        self.errors = []
    
    def summary(self) -> str:
        """生成处理摘要报告"""
```

**计时上下文管理器**:
```python
@contextmanager
def timing_context(logger: logging.Logger, operation_name: str):
    """自动计时和日志记录"""
```

## 🚀 核心处理流程详解

### 阶段1: 标题提取 (Title Extraction)

#### 输入数据
- **目录页面图像**: PDF文档的目录页面截图 (JPG/PNG格式)
- **示例文件**: `sample1base64.txt`, `sample2base64.txt` (Few-shot学习样本)

#### 处理算法

1. **图像预处理**:
   ```python
   # 自适应压缩算法
   def compress_image(image_path: str, max_size_mb: float = 1.0) -> bytes:
       # 质量递减压缩策略
       quality = 95
       while size > max_size_bytes and quality > 5:
           quality -= quality_reduction
   ```

2. **多模态提示词工程**:
   - 7大规则引导的结构化提取
   - 篇标签智能处理机制
   - 层级关系自动识别
   - **附录类内容顺序对齐**: 自动识别并调整"附录"、"关键绩效表"、"指标索引"、"意见反馈"等内容的排列顺序

3. **Few-shot学习策略**:
   ```python
   # 构建多模态消息
   content = [
       {"type": "text", "text": prompt},
       {"type": "image_url", "url": f"data:image/jpeg;base64,{example1}"},
       {"type": "image_url", "url": f"data:image/jpeg;base64,{example2}"},
       {"type": "image_url", "url": f"data:image/jpeg;base64,{target_image}"}
   ]
   ```

#### 输出格式
```json
[
  {
    "title": "公司治理",
    "subtitles": [
      {
        "title": "治理架构",
        "subtitles": ["董事会构成", "独立董事制度"]
      },
      "股东权益保护"
    ]
  }
]
```

### 阶段2: 页面分组 (Page Grouping)

#### 核心算法

**页面索引解析**:
```python
def parse_page_index(line: str, pattern: str = r'<page_idx:(\d+)>') -> Optional[int]:
    """从标记行中提取页面索引"""
```

**智能表格检测**:
```python
def is_table_line(line: str, table_patterns: List[str]) -> bool:
    """多模式表格行识别"""
    patterns = [
        r'^\s*<table',      # HTML表格
        r'^\s*\|',          # Markdown表格
        r'^\s*---',         # 表格分隔线
        r'.*\|.*(?<!^#)'    # 表格行（排除标题）
    ]
```

**分组优化策略**:
- 相邻内容智能合并
- 图片-表格关系保持
- 空行处理优化

### 阶段3: 智能标题对齐 (Title Alignment)

#### 多层次匹配算法

1. **预处理阶段**:
   ```python
   def process_json_titles(titles_json: List) -> List[Tuple[str, int, int, str]]:
       """
       处理JSON标题，返回(标题, 层级, 原始索引, 父标题)
       层级规则：
       - 顶级标题: 1级 (#)
       - 二级嵌套: 2级 (##)
       - 三级嵌套: 3级 (###)
       - 四级标题: 4级 (####)
       """
   ```

2. **标题匹配策略**:
   ```python
   def find_best_match_in_range(md_titles, start_title, end_title, target_title, level, api_key):
       """
       范围内最佳匹配算法:
       1. 确定搜索范围 (前后标题之间)
       2. 计算相似度分数
       3. LLM智能验证
       4. 返回最佳匹配
       """
   ```

3. **缺失标题处理**:
   ```python
   def process_unmatched_titles(aligned_md_path, unmatched_titles, titles_json, api_key):
       """
       缺失标题智能插入:
       1. 分析上下文语义
       2. 确定插入位置
       3. 调整层级关系
       4. 执行插入操作
       """
   ```

#### 层级调整算法

**标题层级确定规则**:
```python
def get_title_level(entry: dict, is_top_level: bool, parent_level: int, is_in_third_level: bool) -> Tuple[int, str]:
    """
    层级判断规则:
    1. 顶级标题 (JSON数组直接元素) → 1级
    2. subtitles中的title → 2级
    3. subtitles的subtitles中的字符串 → 3级
    4. 三级标题下的标题 → 4级
    """
```

**自适应层级调整**:
- 基于父子关系的层级推断
- 上下文一致性检查
- 异常层级自动修正

## 📊 处理管道设计

### 统一处理管道 (`pipeline.py` - 待实现)

```python
class StructureEnhancementPipeline:
    def __init__(self, config: StructureEnhancementConfig):
        self.config = config
        self.title_extractor = TitleExtractor(config)
        self.page_grouper = PageGrouper(config)
        self.title_aligner = TitleAligner(config)
    
    def run(self, input_md_path: str, titles_json_path: str, output_dir: str) -> Dict[str, Any]:
        """执行完整的结构增强流程"""
        # 1. 页面分组
        grouped_md = self.page_grouper.process(input_md_path)
        
        # 2. 标题对齐
        aligned_md = self.title_aligner.process(grouped_md, titles_json_path)
        
        # 3. 结构优化
        enhanced_md = self.structure_enhancer.process(aligned_md)
        
        return self._generate_report(results)
```

### 批量处理支持

```python
class BatchStructureEnhancementPipeline:
    def run_batch(self, input_files: List[str], output_base_dir: str) -> Dict[str, Any]:
        """批量处理多个文件"""
        for input_file in input_files:
            pipeline = StructureEnhancementPipeline(self.config)
            result = pipeline.run(input_file, output_dir)
```

## 🧪 消融实验框架

### 实验设计原理

消融实验通过系统性地禁用或修改算法组件，评估每个组件对整体性能的贡献：

1. **基线实验** (`default`): 所有功能启用
2. **单组件消融**: 逐个禁用核心组件
3. **参数敏感性**: 调整关键阈值参数
4. **极端配置**: 最小化和最大化处理策略

### 实验执行流程

```python
# 1. 定义实验配置
experiments = ["no_llm_matching", "no_fuzzy_match", "strict_matching"]

# 2. 运行消融实验
runner = AblationExperimentRunner(base_config, experiments)
results = runner.run_experiments(input_json, output_dir)

# 3. 结果分析
for exp_name, result in results.items():
    print(f"实验 {exp_name}: 成功率 {result['success_rate']:.2%}")
```

### 评估指标

- **标题匹配准确率**: 正确匹配的标题比例
- **层级结构完整性**: 层级关系的正确性
- **处理效率**: 平均处理时间
- **API调用成本**: API使用量统计

## 🔧 使用方法

### 1. 快速开始

```python
from structure_enhancement_module import quick_structure_enhancement

# 一键处理
result = quick_structure_enhancement(
    input_md_path="report.md",
    titles_json_path="titles.json", 
    output_dir="output/"
)
```

### 2. 模块化使用

```python
from structure_enhancement_module import (
    StructureEnhancementConfig,
    TitleExtractor,
    PageGrouper,
    TitleAligner
)

# 配置初始化
config = StructureEnhancementConfig()
config.title_similarity_threshold = 0.85
config.use_llm_matching = True

# 独立使用各处理器
extractor = TitleExtractor(config)
titles_json = extractor.extract_from_image("toc_page.jpg")

grouper = PageGrouper(config)
grouped_md = grouper.process("input.md")

aligner = TitleAligner(config)
aligned_md = aligner.process(grouped_md, titles_json)
```

### 3. 消融实验

```python
# 应用预定义实验
config = StructureEnhancementConfig()
config.apply_ablation("no_llm_matching")

# 自定义实验配置
custom_config = StructureEnhancementConfig(
    title_similarity_threshold=0.95,
    fuzzy_match_enabled=False,
    experiment_name="custom_strict"
)
```

### 4. 批量处理

```python
from structure_enhancement_module import BatchStructureEnhancementPipeline

# 批量处理
batch_pipeline = BatchStructureEnhancementPipeline(config)
results = batch_pipeline.run_batch(
    input_files=["report1.md", "report2.md"],
    output_base_dir="batch_output/"
)
```

## 📈 性能优化策略

### 1. API调用优化

- **智能重试机制**: 基于tenacity的指数退避
- **请求合并**: 批量处理减少API调用
- **缓存策略**: 相同输入的结果缓存
- **并发控制**: 避免API速率限制

### 2. 图像处理优化

- **自适应压缩**: 根据API限制动态调整
- **格式转换**: 统一JPEG格式减少大小
- **质量递减**: 渐进式压缩策略

### 3. 内存管理

- **流式处理**: 大文件分块处理
- **及时释放**: 处理完成后清理资源
- **对象池**: 重用API客户端实例

## 🐛 错误处理机制

### 1. 分层错误处理

```python
try:
    result = processor.process(input_data)
except APIError as e:
    logger.error(f"API调用失败: {e}")
    # 降级策略: 使用规则匹配
    result = fallback_processor.process(input_data)
except ValidationError as e:
    logger.error(f"数据验证失败: {e}")
    # 数据修复尝试
    result = repair_and_retry(input_data)
```

### 2. 降级策略

- **API失败降级**: LLM匹配失败时使用模糊匹配
- **图像处理降级**: VLM失败时使用OCR文本提取
- **部分处理**: 允许部分成功的结果输出

### 3. 错误恢复

- **自动重试**: 临时性错误的智能重试
- **状态保存**: 中断恢复机制
- **错误报告**: 详细的错误日志和统计

## 📋 配置参数详解

### API配置参数

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `deepseek_api_key` | str | "" | DeepSeek V3 API密钥 |
| `deepseek_r1_api_key` | str | "" | DeepSeek R1 API密钥 |
| `qwen_api_key` | str | "" | Qwen VL API密钥 |
| `api_timeout` | int | 60 | API请求超时时间(秒) |
| `max_retries` | int | 3 | 最大重试次数 |
| `retry_delay` | int | 5 | 重试间隔(秒) |

### 标题匹配参数

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `title_similarity_threshold` | float | 0.8 | 标题相似度阈值 |
| `fuzzy_match_enabled` | bool | True | 是否启用模糊匹配 |
| `use_llm_matching` | bool | True | 是否使用LLM智能匹配 |
| `auto_insert_missing_titles` | bool | True | 是否自动插入缺失标题 |
| `insert_confidence_threshold` | float | 0.7 | 插入置信度阈值 |

### 图像处理参数

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `max_image_size_mb` | float | 1.0 | 图片最大尺寸(MB) |
| `image_quality_reduction` | int | 5 | 压缩质量递减百分比 |
| `extract_max_tokens` | int | 2048 | 提取任务最大token数 |
| `extract_temperature` | float | 0.0 | 提取任务温度参数 |

### 结构控制参数

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `max_title_levels` | int | 4 | 最大标题层级数 |
| `default_title_level` | int | 3 | 默认标题层级 |
| `auto_adjust_levels` | bool | True | 是否自动调整层级 |
| `preserve_original_structure` | bool | True | 是否保持原始结构 |

## 🎯 核心技术特性

### 1. 智能标题匹配算法
- **三层匹配策略**: 完全匹配 → 模糊匹配（RapidFuzz）→ 包含关系
- **中文文本标准化**: 自动处理中文字符和空白符
- **双LLM增强匹配**: DeepSeek V3用于标题选择，DeepSeek R1专门用于插入位置分析
- **专业化分工**: V3负责通用匹配，R1专注插入位置优化

### 2. 附录类内容顺序对齐
- **自动识别**: 智能识别"附录"、"关键绩效表"、"ESG绩效表"、"指标索引"、"意见反馈"等内容
- **顺序验证**: 基于人类撰写习惯的逻辑顺序验证
- **页码辅助**: 利用目录页码信息进行顺序校正
- **自动调整**: 在输出最终结果前自动重新排列附录类内容

### 3. 图像处理优化
- **自适应压缩**: 质量递减压缩策略，避免413错误
- **Base64编码优化**: 高效的图像编码处理
- **多模态Few-shot**: 基于示例图像的标题提取

### 4. 错误处理机制
- **分层错误处理**: API错误、文件错误、验证错误的独立处理
- **降级策略**: API失败时自动降级到规则匹配
- **异常恢复**: 完整的异常捕获和恢复机制

## 🔍 调试和监控

### 1. 日志系统

```python
# 配置详细日志
config = StructureEnhancementConfig()
config.log_level = "DEBUG"
config.log_to_file = True
config.log_file_path = "structure_enhancement_debug.log"
```

### 2. 性能监控

```python
# 获取处理统计
stats = processor.get_stats()
print(f"成功率: {stats['success_rate']:.2%}")
print(f"平均处理时间: {stats['avg_processing_time']:.2f}秒")
```

### 3. 结果验证

```python
# 验证输出质量
def validate_structure(output_md: str) -> List[str]:
    """验证输出结构的完整性和正确性"""
    errors = []
    
    # 检查标题层级
    if not has_valid_hierarchy(output_md):
        errors.append("标题层级结构不正确")
    
    # 检查内容完整性
    if not has_complete_content(output_md):
        errors.append("内容完整性检查失败")
    
    return errors
```

## 🚀 扩展开发指南

### 1. 添加新的处理器

```python
from .processors import BaseProcessor

class CustomProcessor(BaseProcessor):
    def __init__(self, config: StructureEnhancementConfig):
        super().__init__(config)
    
    def process(self, input_data: Any) -> Dict[str, Any]:
        # 实现自定义处理逻辑
        pass
```

### 2. 扩展API客户端

```python
from .api_clients import APIClientBase

class CustomAPIClient(APIClientBase):
    def call_api(self, messages: List[Dict], **kwargs) -> Dict[str, Any]:
        # 实现自定义API调用逻辑
        pass
```

### 3. 添加新的消融实验

```python
# 在config.py中扩展ABLATION_EXPERIMENTS
ABLATION_EXPERIMENTS = {
    "custom_experiment": {
        "custom_param": False,
        "experiment_name": "custom_experiment"
    }
}
```

## 📊 测试和验证

### 1. 单元测试

```bash
# 运行单元测试
python -m pytest tests/test_structure_enhancement.py -v
```

### 2. 集成测试

```bash
# 运行集成测试
python -m pytest tests/test_integration.py -v
```

### 3. 性能测试

```bash
# 运行性能测试
python tests/benchmark_performance.py
```

## 📚 参考资料

### 相关论文
- RapidFuzz: Fast string matching in Python
- Few-shot Learning for Information Extraction
- Hierarchical Document Structure Analysis

### API文档
- [DeepSeek API Documentation](https://platform.deepseek.com/api-docs/)
- [Qwen VL API Documentation](https://help.aliyun.com/zh/dashscope/)

### 依赖库
- `requests`: HTTP请求处理
- `rapidfuzz`: 快速字符串匹配
- `PIL`: 图像处理
- `tenacity`: 重试机制
- `dataclasses`: 配置管理

## 🤝 贡献指南

1. Fork本项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启Pull Request

## 📝 更新日志

### v1.0.0 (当前版本)
- ✅ 完成模块化架构设计
- ✅ 实现配置管理和消融实验支持
- ✅ 完成API客户端抽象层
- ✅ 实现工具函数库
- 🔄 核心处理器开发中
- 🔄 处理管道实现中

### 计划功能
- 📋 批量处理优化
- 📋 更多消融实验配置
- 📋 性能监控面板
- 📋 可视化调试工具

---

**ERLIC Team** - 让ESG报告结构化变得简单而强大 