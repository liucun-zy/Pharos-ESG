# 图片链接格式说明

本项目为每个图片生成了**4种标准化URL格式**，以适应不同的使用场景和环境。这些格式经过精简优化，提供最佳的兼容性和易用性。

## 🔗 4种标准URL格式

### 1. Markdown格式（源引用）
- **字段名**: `*_markdown_url`
- **格式**: `![](相对路径)`
- **示例**: `![](3004XX.SZ-XXXXXX-2024年度环境、社会及公司治理(ESG)报告_temp_images/xxx.jpg)`
- **适用场景**: Markdown文档中的原始引用格式
- **优点**: 保持原始格式，便于追溯
- **用途**: 数据来源追踪，Markdown渲染

### 2. File协议（本机直接访问）
- **字段名**: `*_file_url`
- **格式**: `file:///绝对路径（URL编码）`
- **示例**: `file:///Users/liucun/Desktop/report_analysis/3004XX.SZ-%E5%AF%8C%E7%A5%A5%E8%8D%AF%E4%B8%9A-2024%E5%B9%B4%E5%BA%A6%E7%8E%AF%E5%A2%83%E3%80%81%E7%A4%BE%E4%BC%9A%E5%8F%8A%E5%85%AC%E5%8F%B8%E6%B2%BB%E7%90%86%28ESG%29%E6%8A%A5%E5%91%8A_temp_images/xxx.jpg`
- **适用场景**: 仅在当前计算机上可用
- **优点**: 直接点击即可打开，无需服务器
- **缺点**: 无法跨设备使用

### 3. 相对路径（编程处理）
- **字段名**: `*_relative_path`
- **格式**: `相对路径字符串（未编码）`
- **示例**: `3004XX.SZ-XXXX-2024年度环境、社会及公司治理(ESG)报告_temp_images/xxx.jpg`
- **适用场景**: 编程处理，路径拼接
- **优点**: 纯文本，易于处理和显示
- **用途**: 文件系统操作，路径计算

### 4. HTTP服务器（推荐跨平台方案）
- **字段名**: `*_http_url`
- **格式**: `http://localhost:8000/URL编码路径`
- **示例**: `http://localhost:8000/3004XX.SZ-%E5%AF%8C%E7%A5%A5%E8%8D%AF%E4%B8%9A-2024%E5%B9%B4%E5%BA%A6%E7%8E%AF%E5%A2%83%E3%80%81%E7%A4%BE%E4%BC%9A%E5%8F%8A%E5%85%AC%E5%8F%B8%E6%B2%BB%E7%90%86%28ESG%29%E6%8A%A5%E5%91%8A_temp_images/xxx.jpg`
- **适用场景**: 启动本地HTTP服务器后使用（推荐）
- **优点**: 跨平台兼容，浏览器友好，支持中文路径
- **使用方法**:
  1. 运行 `python start_local_server.py`
  2. 点击JSON中的HTTP链接
  3. 图片在浏览器中打开

## 🚀 快速开始

### 方案1: HTTP服务器（推荐）
```bash
# 1. 启动本地服务器
python start_local_server.py

# 2. 打开JSON文件，点击 *_http_url 链接
# 3. 图片将在浏览器中显示
```

### 方案2: 编程处理
```python
import json
import os

# 读取JSON数据
with open('xxx_grouped.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 使用相对路径
for page in data:
    if 'page_relative_path' in page:
        # 拼接完整路径
        full_path = os.path.join(os.getcwd(), page['page_relative_path'])
        print(f"页面图片路径: {full_path}")
    
    # 处理内容中的图片
    for content in page.get('content', []):
        if 'image_relative_path' in content:
            full_path = os.path.join(os.getcwd(), content['image_relative_path'])
            print(f"内容图片路径: {full_path}")
```

## 📋 JSON字段映射表

### 页面级字段（每个页面根对象）
| 字段名 | 格式类型 | 示例值 |
|--------|----------|---------|
| `page_markdown_url` | Markdown格式 | `![](3004XX.SZ-XXXX-2024年度环境、社会及公司治理(ESG)报告_pages/1.jpg)` |
| `page_file_url` | File协议 | `file:///Users/.../3004XX.SZ-%E5%AF%8C%E7%A5%A5%E8%8D%AF%E4%B8%9A-.../_pages/1.jpg` |
| `page_relative_path` | 相对路径 | `3004XX.SZ-XXXX-2024年度环境、社会及公司治理(ESG)报告/.../_pages/1.jpg` |
| `page_http_url` | HTTP服务器 | `http://localhost:8000/3004XX.SZ-%E5%AF%8C%E7%A5%A5%E8%8D%AF%E4%B8%9A-.../_pages/1.jpg` |

### 图片块字段（content中data_type包含image的块）
| 字段名 | 格式类型 | 示例值 |
|--------|----------|---------|
| `image_markdown_url` | Markdown格式 | `![](3004XX.SZ-XXXX-2024年度环境、社会及公司治理(ESG)报告_temp_images/xxx.jpg)` |
| `image_file_url` | File协议 | `file:///Users/.../3004XX.SZ-%E5%AF%8C%E7%A5%A5%E8%8D%AF%E4%B8%9A-.../_temp_images/xxx.jpg` |
| `image_relative_path` | 相对路径 | `3004XX.SZ-XXXX-2024年度环境、社会及公司治理(ESG)报告_temp_images/xxx.jpg` |
| `image_http_url` | HTTP服务器 | `http://localhost:8000/3004XX.SZ-%E5%AF%8C%E7%A5%A5%E8%8D%AF%E4%B8%9A-.../_temp_images/xxx.jpg` |

### 表格块字段（content中data_type为table的块）
| 字段名 | 格式类型 | 示例值 |
|--------|----------|---------|
| `table_markdown_url` | Markdown格式 | `![](3004XX.SZ-XXXX-2024年度环境、社会及公司治理(ESG)报告_temp_images/xxx.jpg)` |
| `table_file_url` | File协议 | `file:///Users/.../3004XX.SZ-%E5%AF%8C%E7%A5%A5%E8%8D%AF%E4%B8%9A-.../_temp_images/xxx.jpg` |
| `table_relative_path` | 相对路径 | `3004XX.SZ-XXXX-2024年度环境、社会及公司治理(ESG)报告_temp_images/xxx.jpg` |
| `table_http_url` | HTTP服务器 | `http://localhost:8000/3004XX.SZ-%E5%AF%8C%E7%A5%A5%E8%8D%AF%E4%B8%9A-.../_temp_images/xxx.jpg` |

### 实际JSON数据示例
```json
{
  "page_idx": 1,
  "page_markdown_url": "![](3004XX.SZ-XXXX-2024年度环境、社会及公司治理(ESG)报告_pages/1.jpg)",
  "page_file_url": "file:///Users/liucun/Desktop/report_analysis/3004XX.SZ-%E5%AF%8C%E7%A5%A5%E8%8D%AF%E4%B8%9A-2024%E5%B9%B4%E5%BA%A6%E7%8E%AF%E5%A2%83%E3%80%81%E7%A4%BE%E4%BC%9A%E5%8F%8A%E5%85%AC%E5%8F%B8%E6%B2%BB%E7%90%86%28ESG%29%E6%8A%A5%E5%91%8A/3004XX.SZ-%E5%AF%8C%E7%A5%A5%E8%8D%AF%E4%B8%9A-2024%E5%B9%B4%E5%BA%A6%E7%8E%AF%E5%A2%83%E3%80%81%E7%A4%BE%E4%BC%9A%E5%8F%8A%E5%85%AC%E5%8F%B8%E6%B2%BB%E7%90%86%28ESG%29%E6%8A%A5%E5%91%8A_pages/1.jpg",
  "page_relative_path": "3004XX.SZ-XXXX-2024年度环境、社会及公司治理(ESG)报告/3004XX.SZ-XXXX-2024年度环境、社会及公司治理(ESG)报告_pages/1.jpg",
  "page_http_url": "http://localhost:8000/3004XX.SZ-%E5%AF%8C%E7%A5%A5%E8%8D%AF%E4%B8%9A-2024%E5%B9%B4%E5%BA%A6%E7%8E%AF%E5%A2%83%E3%80%81%E7%A4%BE%E4%BC%9A%E5%8F%8A%E5%85%AC%E5%8F%B8%E6%B2%BB%E7%90%86%28ESG%29%E6%8A%A5%E5%91%8A/3004XX.SZ-%E5%AF%8C%E7%A5%A5%E8%8D%AF%E4%B8%9A-2024%E5%B9%B4%E5%BA%A6%E7%8E%AF%E5%A2%83%E3%80%81%E7%A4%BE%E4%BC%9A%E5%8F%8A%E5%85%AC%E5%8F%B8%E6%B2%BB%E7%90%86%28ESG%29%E6%8A%A5%E5%91%8A_pages/1.jpg",
  "content": [
    {
      "data_type": "image<image[7][混合图]>",
      "data": "VLM分析的图像描述内容...",
      "image_markdown_url": "![](3004XX.SZ-XXXX-2024年度环境、社会及公司治理(ESG)报告_temp_images/xxx.jpg)",
      "image_file_url": "file:///Users/.../xxx.jpg",
      "image_relative_path": "3004XX.SZ-XXXX-2024年度环境、社会及公司治理(ESG)报告_temp_images/xxx.jpg",
      "image_http_url": "http://localhost:8000/3004XX.SZ-%E5%AF%8C%E7%A5%A5%E8%8D%AF%E4%B8%9A-.../xxx.jpg"
    }
  ]
}
```

## 📋 数据分享最佳实践

### 给别人分享数据时：

1. **打包完整项目**
   - JSON文件
   - 所有图片文件夹
   - `start_local_server.py` 脚本

2. **提供使用说明**
   ```
   1. 解压到任意目录
   2. 运行: python start_local_server.py
   3. 点击JSON中的HTTP链接查看图片
   ```

3. **保持目录结构**
   ```
   项目根目录/
   ├── xxx_grouped.json
   ├── start_local_server.py
   ├── 3004XX.SZ-XXXX-2024年度环境、社会及公司治理(ESG)报告_temp_images/
   ├── 3004XX.SZ-XXXX-2024年度环境、社会及公司治理(ESG)报告_pages/
   └── ...
   ```

## 🔧 技术细节

### HTTP服务器特性
- 端口: 8000
- 支持CORS跨域访问
- 自动处理中文路径
- 支持所有常见图片格式

### URL编码处理
- 空格自动转换为 `%20`
- 中文字符自动URL编码
- 特殊字符安全处理

### 兼容性
- ✅ Windows/Mac/Linux
- ✅ 所有现代浏览器
- ✅ 移动设备浏览器
- ✅ 各种图片查看器

## ❓ 常见问题

**Q: HTTP链接点击无效？**
A: 确保本地HTTP服务器正在运行（`python start_local_server.py`）

**Q: 如何在其他端口运行服务器？**
A: 修改 `start_local_server.py` 中的 `PORT = 8000` 为其他端口

**Q: 可以远程访问图片吗？**
A: 可以，将服务器绑定到 `0.0.0.0` 并开放防火墙端口

**Q: 自定义协议如何使用？**
A: 需要注册协议处理程序，或开发支持该协议的应用程序

## 🔧 URL编码技术细节

### 中文路径处理
- **中文字符**: 自动转换为URL编码（如：XXXX → %E5%AF%8C%E7%A5%A5%E8%8D%AF%E4%B8%9A）
- **特殊符号**: 括号、空格等自动编码（如：(ESG) → %28ESG%29）
- **兼容性**: 确保Windows/Mac/Linux系统间的路径兼容

### 格式对比
| 原始路径 | 相对路径格式 | URL编码格式 |
|----------|-------------|-------------|
| `XXXX-2024年度环境` | `XXXX-2024年度环境` | `%E5%AF%8C%E7%A5%A5%E8%8D%AF%E4%B8%9A-2024%E5%B9%B4%E5%BA%A6%E7%8E%AF%E5%A2%83` |
| `(ESG)报告` | `(ESG)报告` | `%28ESG%29%E6%8A%A5%E5%91%8A` |
| `社会及公司治理` | `社会及公司治理` | `%E7%A4%BE%E4%BC%9A%E5%8F%8A%E5%85%AC%E5%8F%B8%E6%B2%BB%E7%90%86` |

### 适用场景建议
- **本地查看**: 使用 `*_file_url` 直接点击打开
- **分享传输**: 使用 `*_http_url` 配合HTTP服务器
- **编程处理**: 使用 `*_relative_path` 进行路径操作
- **源文档追溯**: 使用 `*_markdown_url` 查看原始引用

## 📝 更新日志

- v1.0: 支持基础的 `file://` 协议
- v2.0: 添加HTTP本地服务器支持
- v2.1: 添加自定义协议和可移植路径
- v2.2: 优化URL编码和跨平台兼容性
- **v3.0: 标准化4种URL格式，移除冗余字段**
  - 精简为4种核心格式：markdown_url, file_url, relative_path, http_url
  - 移除 custom_url 和 portable_path 字段
  - 统一命名规范：页面级、图片级、表格级字段
  - 改进中文路径的URL编码处理 