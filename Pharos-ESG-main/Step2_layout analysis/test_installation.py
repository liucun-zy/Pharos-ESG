#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF文档分析工具 - 安装验证脚本
用于验证所有依赖是否正确安装
"""

import sys
import importlib
from pathlib import Path

def test_import(module_name, package_name=None):
    """测试模块导入"""
    try:
        if package_name:
            importlib.import_module(package_name)
        else:
            importlib.import_module(module_name)
        return True, f"✓ {module_name} 已安装"
    except ImportError as e:
        return False, f"✗ {module_name} 未安装: {e}"
    except Exception as e:
        return False, f"✗ {module_name} 导入错误: {e}"

def main():
    print("=" * 60)
    print("PDF文档分析工具 - 依赖验证")
    print("=" * 60)
    print()
    
    # 检查Python版本
    print(f"Python版本: {sys.version}")
    print(f"Python路径: {sys.executable}")
    print()
    
    # 定义需要测试的依赖
    dependencies = [
        ("pathlib", "pathlib"),
        ("typing_extensions", "typing_extensions"),
        ("PIL", "Pillow"),
        ("cv2", "opencv-python"),
        ("numpy", "numpy"),
        ("fitz", "PyMuPDF"),
        ("pdf2image", "pdf2image"),
        ("pytesseract", "pytesseract"),
        ("easyocr", "easyocr"),
        ("pandas", "pandas"),
        ("tqdm", "tqdm"),
        ("requests", "requests"),
        ("magic_pdf", "magic_pdf"),
    ]
    
    # 测试所有依赖
    all_passed = True
    results = []
    
    for module_name, package_name in dependencies:
        success, message = test_import(module_name, package_name)
        results.append((success, message))
        if not success:
            all_passed = False
    
    # 显示结果
    print("依赖检查结果:")
    print("-" * 60)
    for success, message in results:
        print(message)
    print("-" * 60)
    
    # 测试项目文件
    print("\n项目文件检查:")
    print("-" * 60)
    
    project_files = [
        "create_jsonandimage.py",
        "test2.py",
        "requirements.txt",
        "README.md"
    ]
    
    for file_name in project_files:
        if Path(file_name).exists():
            print(f"✓ {file_name} 存在")
        else:
            print(f"✗ {file_name} 不存在")
            all_passed = False
    
    print("-" * 60)
    
    # 测试基本功能
    print("\n基本功能测试:")
    print("-" * 60)
    
    try:
        # 测试pathlib功能
        from pathlib import Path
        test_path = Path("test_file.txt")
        print("✓ pathlib 功能正常")
    except Exception as e:
        print(f"✗ pathlib 功能异常: {e}")
        all_passed = False
    
    try:
        # 测试JSON功能
        import json
        test_data = {"test": "data"}
        json_str = json.dumps(test_data)
        print("✓ JSON 功能正常")
    except Exception as e:
        print(f"✗ JSON 功能异常: {e}")
        all_passed = False
    
    print("-" * 60)
    
    # 总结
    print("\n验证总结:")
    print("=" * 60)
    if all_passed:
        print("🎉 所有依赖和文件检查通过！")
        print("✅ 可以开始使用PDF文档分析工具")
        print("\n使用方法:")
        print("  python create_jsonandimage.py")
        print("  或")
        print("  python -c \"from create_jsonandimage import process_pdf; process_pdf('your_file.pdf')\"")
    else:
        print("❌ 部分依赖或文件缺失")
        print("请运行安装脚本:")
        print("  Windows: install_dependencies.bat")
        print("  Linux/macOS: ./install_dependencies.sh")
        print("  或手动安装: pip install -r requirements.txt")
    
    print("=" * 60)
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 