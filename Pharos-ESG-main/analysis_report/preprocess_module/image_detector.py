import os
import pytesseract
from pathlib import Path
import re
from PIL import Image
import numpy as np

class ImageDetector:
    def __init__(self):
        # 设置 Tesseract 路径（macOS Homebrew 安装路径）
        pytesseract.pytesseract.tesseract_cmd = '/opt/homebrew/bin/tesseract'
    
    def detect_text(self, image_path):
        """
        检测图片中的文字
        Args:
            image_path: 图片路径
        Returns:
            str: 检测到的文字
        """
        try:
            # 打开图片
            img = Image.open(image_path)
            # 使用 pytesseract 识别文字
            text = pytesseract.image_to_string(img, lang='chi_sim+eng')
            return text
        except Exception as e:
            print(f"❌ 文字检测失败: {str(e)}")
            return ""

def process_markdown_file(md_file_path, detector, output_images_dir):
    """
    处理Markdown文件中的图片链接
    :param md_file_path: Markdown文件路径
    :param detector: TextDetector实例
    :param output_images_dir: 输出图片目录
    :return: 删除的图片链接数量
    """
    # 读取Markdown文件内容
    with open(md_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 匹配Markdown中的图片链接，支持两种格式：
    # 1. ![](path/to/image.jpg)
    # 2. ![alt text](path/to/image.jpg)
    # 修改正则表达式以正确处理包含括号的路径
    image_pattern = r'!\[.*?\]\((.+)\)'
    matches = re.finditer(image_pattern, content)
    
    # 存储需要删除的图片链接
    links_to_remove = []
    images_deleted = 0
    
    print(f"\n开始处理Markdown文件中的图片链接...")
    print(f"文件路径: {md_file_path}")
    
    # 检查每个图片链接
    for match in matches:
        image_path = match.group(1)  # 获取图片路径
        # 从URL中提取文件名
        image_filename = os.path.basename(image_path)
        # 构建完整的图片路径
        full_image_path = Path(output_images_dir) / image_filename
        
        print(f"\n处理图片链接: {match.group(0)}")
        print(f"图片文件: {full_image_path}")
        
        if full_image_path.exists():
            has_text = detector.detect_text(full_image_path)
            print(f"文字检测结果: {'有文字' if has_text else '无文字'}")
            
            if not has_text:
                # 只删除md文件中的图片链接，不删除图片文件
                    links_to_remove.append(match.group(0))
                    images_deleted += 1
                    print(f"✓ 已删除Markdown中的无文字图片链接: {match.group(0)}")
            else:
                print(f"✗ 图片文件不存在: {full_image_path}")
    
    # 从Markdown文件中删除对应的图片链接
    original_content = content
    for link in links_to_remove:
        content = content.replace(link, '')
    
    # 保存更新后的Markdown文件
    with open(md_file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"\nMarkdown文件处理完成:")
    print(f"- 原始内容长度: {len(original_content)} 字符")
    print(f"- 更新后内容长度: {len(content)} 字符")
    print(f"- 删除的图片链接数: {len(links_to_remove)}")
    
    return images_deleted

def get_report_directories(base_path):
    """
    获取所有报告目录及其对应的图片目录
    :param base_path: 基础路径
    :return: 包含报告目录和图片目录的列表
    """
    report_dirs = []
    base_path = Path(base_path)
    
    # 获取两个子文件夹
    subdirs = list(base_path.iterdir())
    if len(subdirs) != 2:
        print(f"错误：在基础路径下未找到两个子文件夹")
        return report_dirs
    
    # 正确识别md_files和image_files文件夹
    md_base_dir = None
    img_base_dir = None
    for subdir in subdirs:
        if subdir.name == "md_files":
            md_base_dir = subdir
        elif subdir.name == "image_files":
            img_base_dir = subdir
    
    if not md_base_dir or not img_base_dir:
        print(f"错误：未找到md_files或image_files文件夹")
        return report_dirs
        
    print(f"MD文件目录: {md_base_dir}")
    print(f"图片目录: {img_base_dir}")
    
    # 遍历md文件目录下的所有子文件夹
    for report_dir in md_base_dir.iterdir():
        if report_dir.is_dir():
            # 从文件夹名称中提取报告名
            # 支持两种格式：
            # 1. 日期_股票代码_公司名_报告名
            # 2. 股票代码_公司名_报告名
            parts = report_dir.name.split('_')
            if len(parts) >= 3:  # 至少需要股票代码、公司名和报告名三部分
                # 如果第一部分是日期格式（8位数字），则从第二部分开始取
                if len(parts[0]) == 8 and parts[0].isdigit():
                    report_name = '_'.join(parts[1:])
                else:
                    report_name = report_dir.name
                
                # 查找对应的md文件
                md_file = next(report_dir.glob("*_without_toc.md"), None)
                if md_file:
                    # 构建对应的图片目录路径
                    img_dir = img_base_dir / f"{report_name}_without_toc"
                    if img_dir.exists():
                        report_dirs.append({
                            'report_dir': report_dir.name,
                            'md_file': md_file,
                            'img_dir': img_dir
                        })
                        print(f"找到报告: {report_dir.name}")
                    else:
                        print(f"警告：未找到对应的图片目录: {img_dir}")
                else:
                    print(f"警告：在 {report_dir} 中未找到md文件")
            else:
                print(f"警告：报告目录名称格式不正确: {report_dir.name}")
    
    return report_dirs

def process_directory(directory_info):
    """
    处理单个报告目录
    :param directory_info: 包含报告目录信息的字典
    """
    md_file_path = directory_info['md_file']
    output_images_dir = directory_info['img_dir']
    report_dir = directory_info['report_dir']
    
    print(f"\n处理报告: {report_dir}")
    print(f"Markdown文件路径: {md_file_path}")
    print(f"输出图片目录路径: {output_images_dir}")
    
    # 检查markdown文件是否存在
    if not md_file_path.exists():
        print(f"错误：Markdown文件不存在: {md_file_path}")
        return
    
    # 检查输出图片目录是否存在
    if not output_images_dir.exists():
        print(f"错误：输出图片目录不存在: {output_images_dir}")
        return
    
    # 初始化检测器
    detector = ImageDetector()
    
    # 处理Markdown文件
    print(f"\n处理Markdown文件: {md_file_path}")
    images_deleted = process_markdown_file(str(md_file_path), detector, str(output_images_dir))
    
    # 打印统计信息
    print("\n统计信息:")
    print(f"删除的无文字图片数: {images_deleted}")
    print(f"\n处理完成！原文件夹中只保留了有文字的图片。")

def deleteUrlImage(base_path):
    """
    处理指定基础路径下的所有报告
    :param base_path: 基础路径
    """
    print("\n开始检测图片中的文字...\n")
    report_dirs = get_report_directories(base_path)
    
    if not report_dirs:
        print(f"在路径 {base_path} 下未找到任何报告目录")
        return
        
    print(f"找到 {len(report_dirs)} 个报告目录")
    
    for directory_info in report_dirs:
        process_directory(directory_info)
    
    print("\n所有报告处理完成！")

if __name__ == "__main__":
    # 只处理一个硬编码的Markdown文件和图片目录
    md_file_path = "/Users/liucun/Desktop/report_analysis/300497.SZ-富祥药业-2024年度环境、社会及公司治理(ESG)报告/output.md"
    output_images_dir = "/Users/liucun/Desktop/report_analysis/300497.SZ-富祥药业-2024年度环境、社会及公司治理(ESG)报告_temp_images"
    detector = ImageDetector()
    process_markdown_file(md_file_path, detector, output_images_dir)