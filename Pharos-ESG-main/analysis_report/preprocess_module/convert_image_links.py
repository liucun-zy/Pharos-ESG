import re
import os
from pathlib import Path

def convert_image_links(md_file_path, images_dir):
    """
    将单独一行的图片路径转换为标准的Markdown图片语法
    :param md_file_path: Markdown文件路径
    :param images_dir: 图片目录路径
    """
    # 读取Markdown文件内容
    with open(md_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 按行分割内容
    lines = content.split('\n')
    new_lines = []
    
    # 图片文件扩展名
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
    
    print(f"开始处理Markdown文件: {md_file_path}")
    print(f"图片目录: {images_dir}")
    
    converted_count = 0
    
    for line in lines:
        line = line.strip()
        
        # 检查是否为图片路径（包含_temp_images/且以图片扩展名结尾）
        if '_temp_images/' in line and any(line.lower().endswith(ext) for ext in image_extensions):
            # 提取文件名
            filename = os.path.basename(line)
            # 构建完整的图片路径
            full_image_path = Path(images_dir) / filename
            
            # 检查图片文件是否存在
            if full_image_path.exists():
                # 转换为标准Markdown图片语法
                new_line = f"![]({line})"
                new_lines.append(new_line)
                converted_count += 1
                print(f"✓ 转换: {line} -> ![]({line})")
            else:
                # 图片文件不存在，保持原样
                new_lines.append(line)
                print(f"⚠ 图片文件不存在: {full_image_path}")
        else:
            # 不是图片路径，保持原样
            new_lines.append(line)
    
    # 写回文件
    with open(md_file_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(new_lines))
    
    print(f"\n转换完成!")
    print(f"- 转换的图片链接数: {converted_count}")
    print(f"- 文件已保存: {md_file_path}")

if __name__ == "__main__":
    # 硬编码路径
    md_file_path = "/Users/liucun/Desktop/report_analysis/300497.SZ-富祥药业-2024年度环境、社会及公司治理(ESG)报告/output.md"
    images_dir = "/Users/liucun/Desktop/report_analysis/300497.SZ-富祥药业-2024年度环境、社会及公司治理(ESG)报告_temp_images"
    
    convert_image_links(md_file_path, images_dir) 