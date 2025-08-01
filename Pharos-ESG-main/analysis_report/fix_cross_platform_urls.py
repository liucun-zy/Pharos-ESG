#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
跨平台URL修复脚本
用于修复不同操作系统间的中文字符编码问题
"""

import json
import os
import sys
from urllib.parse import quote, unquote
from pathlib import Path

def fix_urls_for_platform(json_path, project_root, output_path=None):
    """
    修复JSON文件中的HTTP URL，使其在当前平台上可用
    
    Args:
        json_path: VLM JSON文件路径
        project_root: 项目根目录路径
        output_path: 输出文件路径（可选，默认覆盖原文件）
    """
    print("🔧 开始修复跨平台URL问题...")
    print(f"JSON文件: {json_path}")
    print(f"项目根目录: {project_root}")
    print("=" * 80)
    
    # 检查文件和目录是否存在
    if not os.path.exists(json_path):
        print(f"❌ JSON文件不存在: {json_path}")
        return False
        
    if not os.path.exists(project_root):
        print(f"❌ 项目根目录不存在: {project_root}")
        return False
    
    # 读取JSON文件
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"✅ 成功读取JSON文件，包含 {len(data)} 个块")
    except Exception as e:
        print(f"❌ 读取JSON文件失败: {e}")
        return False
    
    # 统计修复情况
    fixed_count = 0
    total_urls = 0
    
    def fix_http_url(original_url, url_type, block_index):
        """修复单个HTTP URL"""
        nonlocal fixed_count, total_urls
        total_urls += 1
        
        if not original_url or not original_url.startswith('http://localhost:8000/'):
            return original_url
        
        # 提取路径部分
        url_path = original_url[len('http://localhost:8000/'):]
        
        try:
            # 先解码，再重新编码以确保一致性
            decoded_path = unquote(url_path)
            
            # 检查解码后的文件是否存在
            full_path = os.path.join(project_root, decoded_path)
            full_path = os.path.normpath(full_path)
            
            if os.path.exists(full_path):
                # 文件存在，重新编码URL
                new_encoded_path = quote(decoded_path, safe='/')
                new_url = f"http://localhost:8000/{new_encoded_path}"
                
                if new_url != original_url:
                    print(f"🔧 修复 {url_type} URL (块 {block_index}):")
                    print(f"   原始: {original_url}")
                    print(f"   修复: {new_url}")
                    fixed_count += 1
                
                return new_url
            else:
                print(f"⚠️  文件不存在: {full_path}")
                return original_url
                
        except Exception as e:
            print(f"❌ 处理URL时出错: {e}")
            return original_url
    
    # 处理每个块
    for i, block in enumerate(data):
        # 修复图片HTTP URLs
        if 'image_http_urls' in block and block['image_http_urls']:
            for j in range(len(block['image_http_urls'])):
                block['image_http_urls'][j] = fix_http_url(
                    block['image_http_urls'][j], 
                    f"image[{j}]", 
                    i
                )
        
        # 修复单个图片HTTP URL
        if 'image_http_url' in block and block['image_http_url']:
            block['image_http_url'] = fix_http_url(
                block['image_http_url'], 
                "image", 
                i
            )
        
        # 修复表格HTTP URLs
        if 'table_http_urls' in block and block['table_http_urls']:
            for j in range(len(block['table_http_urls'])):
                block['table_http_urls'][j] = fix_http_url(
                    block['table_http_urls'][j], 
                    f"table[{j}]", 
                    i
                )
        
        # 修复单个表格HTTP URL
        if 'table_http_url' in block and block['table_http_url']:
            block['table_http_url'] = fix_http_url(
                block['table_http_url'], 
                "table", 
                i
            )
        
        # 修复页面HTTP URL
        if 'page_http_url' in block and block['page_http_url']:
            block['page_http_url'] = fix_http_url(
                block['page_http_url'], 
                "page", 
                i
            )
    
    # 保存修复后的文件
    output_file = output_path or json_path
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"✅ 修复完成，已保存到: {output_file}")
        print(f"📊 统计: 修复了 {fixed_count}/{total_urls} 个URL")
        return True
    except Exception as e:
        print(f"❌ 保存文件失败: {e}")
        return False

def create_platform_server_script(project_root):
    """创建适合当前平台的服务器启动脚本"""
    server_script = f'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
跨平台HTTP服务器启动脚本
自动生成，适用于当前平台
"""

import http.server
import socketserver
import os
import sys
from pathlib import Path
from urllib.parse import unquote

# 当前平台的项目根目录
PROJECT_ROOT = r"{project_root}"
PORT = 8000

class CrossPlatformHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=PROJECT_ROOT, **kwargs)
    
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        super().end_headers()
    
    def do_GET(self):
        """增强的GET方法，支持跨平台路径处理"""
        decoded_path = unquote(self.path)
        print(f"📥 请求: {{self.path}}")
        print(f"🔓 解码: {{decoded_path}}")
        
        if decoded_path.startswith('/'):
            file_path = os.path.join(PROJECT_ROOT, decoded_path[1:])
        else:
            file_path = os.path.join(PROJECT_ROOT, decoded_path)
        
        file_path = os.path.normpath(file_path)
        print(f"📁 文件: {{file_path}}")
        print(f"✓ 存在: {{os.path.exists(file_path)}}")
        
        super().do_GET()

def start_server():
    try:
        os.chdir(PROJECT_ROOT)
        print(f"✅ HTTP服务器已启动")
        print(f"🌐 地址: http://localhost:{{PORT}}")
        print(f"📁 根目录: {{PROJECT_ROOT}}")
        print(f"⏹️  按 Ctrl+C 停止")
        print("=" * 60)
        
        with socketserver.TCPServer(("", PORT), CrossPlatformHTTPRequestHandler) as httpd:
            httpd.serve_forever()
            
    except KeyboardInterrupt:
        print("\\n🛑 服务器已停止")
    except Exception as e:
        print(f"❌ 启动失败: {{e}}")

if __name__ == "__main__":
    start_server()
'''
    
    script_path = os.path.join(project_root, "start_server_local.py")
    try:
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(server_script)
        print(f"✅ 已创建平台专用服务器脚本: {script_path}")
        return script_path
    except Exception as e:
        print(f"❌ 创建服务器脚本失败: {e}")
        return None

if __name__ == "__main__":
    # 默认配置（在目标电脑上需要修改这些路径）
    if len(sys.argv) >= 3:
        json_path = sys.argv[1]
        project_root = sys.argv[2]
    else:
        # Windows示例路径
        json_path = r"/Users/liucun/Desktop/yiyao_fuxaing/300497.SZ-富祥药业-2024年度环境、社会及公司治理(ESG)报告/300497.SZ-富祥药业-2024年度环境、社会及公司治理(ESG)报告_grouped.json"
        project_root = r"/Users/liucun/Desktop/yiyao_fuxaing"
        
        print("🔧 使用默认路径，如需修改请运行：")
        print(f"python {__file__} <json_path> <project_root>")
        print()
    
    # 执行修复
    success = fix_urls_for_platform(json_path, project_root)
    
    if success:
        # 创建平台专用的服务器脚本
        create_platform_server_script(project_root)
        
        print("\\n💡 下一步操作：")
        print("1. 运行生成的 start_server_local.py")
        print("2. 在浏览器中测试HTTP链接")
        print("3. 如果仍有问题，请运行 debug_server.py 进行诊断")
    else:
        print("\\n❌ 修复失败，请检查路径设置") 