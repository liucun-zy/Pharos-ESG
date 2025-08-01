# 跨平台HTTP链接使用说明

## 问题描述
当将包含中文路径的JSON文件从macOS复制到Windows等其他平台时，HTTP链接可能因为URL编码差异导致404错误。

## 解决方案

### 第一步：将文件复制到目标电脑
1. 将整个项目文件夹复制到目标电脑
2. 确保包含以下文件：
   - `xxx_vlm.json` (VLM处理后的JSON文件)
   - `xxx_temp_images` (图片文件夹)
   - `xxx_pages` (页面文件夹，如果有的话)
   - 跨平台工具脚本

### 第二步：修复URL编码
在目标电脑上运行URL修复脚本：

```bash
# 方法1：使用默认路径（需要修改脚本中的路径）
python fix_cross_platform_urls.py

# 方法2：指定路径参数
python fix_cross_platform_urls.py "路径\到\vlm.json" "项目根目录路径"
```

### 第三步：启动HTTP服务器
运行生成的平台专用服务器：

```bash
python start_server_local.py
```

### 第四步：测试链接
在JSON文件中点击 `*_http_url` 链接，应该能够正常显示图片。

## 故障排除

### 如果仍然出现404错误：

1. **运行调试脚本**：
   ```bash
   python debug_server.py
   ```

2. **检查常见问题**：
   - 项目根目录路径是否正确
   - 图片文件是否存在
   - 文件名编码是否一致
   - HTTP服务器是否正常启动

3. **手动验证**：
   - 检查HTTP服务器输出的调试信息
   - 确认请求的文件路径与实际文件路径匹配

### 如果问题持续存在：

可以考虑以下替代方案：
- 使用 `*_file_url` 字段（本地file://协议）
- 将项目移动到纯英文路径下
- 手动重命名图片文件夹为英文名称

## 文件说明

- `fix_cross_platform_urls.py`: URL修复脚本
- `debug_server.py`: 调试工具
- `start_server_local.py`: 自动生成的平台专用HTTP服务器
- `start_local_server.py`: 原始HTTP服务器（通用版本）

## 技术原理

问题的根本原因是不同操作系统对中文字符的URL编码处理方式略有差异。修复脚本通过：
1. 解码现有URL
2. 验证文件是否存在
3. 重新编码URL以适配当前平台

这确保了HTTP链接在不同平台上的一致性和可用性。 