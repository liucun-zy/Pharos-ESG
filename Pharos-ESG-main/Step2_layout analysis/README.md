# PDF文档分析工具

这是一个基于magic_pdf库的PDF文档分析工具，能够自动处理PDF文件并生成JSON格式的结构化数据和图片输出。

## 功能特性

- **智能PDF解析**: 自动识别PDF类型（OCR或文本模式）
- **结构化输出**: 生成JSON格式的内容列表
- **图片提取**: 自动提取PDF中的图片并保存
- **批量处理**: 支持批量处理多个PDF文件
- **错误处理**: 完善的错误处理和日志记录

## 系统要求

- Python 3.7+
- 操作系统: Windows, macOS, Linux
- 内存: 建议4GB以上
- 存储空间: 根据PDF文件大小而定

## 安装指南

### 1. 克隆或下载项目

```bash
git clone <repository-url>
cd Step2_mineru
```

### 2. 安装依赖

#### 方法一: 使用安装脚本（推荐）

```bash
# Windows
install_dependencies.bat

# macOS/Linux
chmod +x install_dependencies.sh
./install_dependencies.sh
```

#### 方法二: 手动安装

```bash
pip install -r requirements.txt
```

### 3. 验证安装

```bash
python -c "import magic_pdf; print('安装成功!')"
```

## 使用方法

### 单个PDF文件处理

```python
from create_jsonandimage import process_pdf

# 处理单个PDF文件
result = process_pdf("path/to/your/file.pdf")
print(f"JSON文件: {result['output_files']['json']}")
print(f"图片目录: {result['output_files']['images_dir']}")
```

### 批量处理PDF文件

```python
from create_jsonandimage import process_all_pdfs

# 处理指定目录下的所有PDF文件
process_all_pdfs("path/to/pdf/directory")
```

### 命令行使用

```bash
# 处理所有PDF文件（使用默认目录）
python create_jsonandimage.py

# 处理指定目录下的PDF文件
python -c "from create_jsonandimage import process_all_pdfs; process_all_pdfs('your/path')"
```

## 输出说明

### JSON文件结构

生成的JSON文件包含以下结构：

```json
[
  {
    "type": "text|image|table",
    "content": "...",
    "position": {...},
    "metadata": {...}
  }
]
```

### 文件组织

- **JSON文件**: 保存在PDF文件同目录下，文件名与PDF相同
- **图片文件**: 保存在指定的输出目录中，按PDF文件名组织

## 配置说明

### 默认路径配置

- **输入目录**: `E:\ESGdata\success` (Windows) 或 `/path/to/input`
- **输出目录**: `E:\ESGdata\md_jpg` (Windows) 或 `/path/to/output`

### 自定义路径

修改代码中的路径变量：

```python
# 在create_jsonandimage.py中修改
def process_all_pdfs(base_dir="your/input/path"):
    # ...

def process_pdf(pdf_file_path, output_base_dir="your/output/path"):
    # ...
```

## 故障排除

### 常见问题

1. **ImportError: No module named 'magic_pdf'**
   - 解决方案: 确保正确安装了magic_pdf库
   - 检查: `pip list | grep magic_pdf`

2. **内存不足错误**
   - 解决方案: 增加系统内存或处理较小的PDF文件
   - 建议: 分批处理大文件

3. **路径错误**
   - 解决方案: 检查文件路径是否正确
   - 确保路径使用正确的分隔符

### 日志和调试

程序会输出详细的处理日志，包括：
- 处理进度
- 成功/失败统计
- 错误详情

## 性能优化

- 使用SSD存储以提高I/O性能
- 增加系统内存以处理大型PDF文件
- 考虑使用多进程处理（需要代码修改）

## 许可证

请查看项目的LICENSE文件了解详细信息。

## 贡献

欢迎提交Issue和Pull Request来改进这个项目。

## 联系方式

如有问题或建议，请通过以下方式联系：
- 提交GitHub Issue
- 发送邮件至项目维护者

---

**注意**: 请确保您有合法的权限来处理相关的PDF文件。 