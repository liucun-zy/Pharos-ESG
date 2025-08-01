#!/usr/bin/env python3
"""
子文件夹配置测试脚本

用于验证子文件夹处理配置是否正确，
以及检查目录结构和文件分布。
"""

import os
import sys
from pathlib import Path
from typing import Dict, List

# 添加模块路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from batch_config import INPUT_CONFIG, validate_config, check_system_requirements
    from run_batch_preprocess import discover_subfolder_json_files
except ImportError as e:
    print(f"❌ 导入错误: {e}")
    print("请确保在正确的目录中运行此脚本")
    sys.exit(1)

def check_directory_structure(base_dir: str):
    """检查目录结构"""
    print(f"🔍 检查目录结构: {base_dir}")
    
    if not os.path.exists(base_dir):
        print(f"❌ 目录不存在: {base_dir}")
        return False
    
    base_path = Path(base_dir)
    subdirs = []
    
    for item in base_path.iterdir():
        if item.is_dir():
            subdirs.append(item)
    
    if not subdirs:
        print(f"⚠️ 在 {base_dir} 中未找到任何子文件夹")
        return False
    
    print(f"📁 找到 {len(subdirs)} 个子文件夹:")
    for subdir in subdirs:
        print(f"   - {subdir.name}")
    
    return True

def check_json_files_distribution(base_dir: str, exclude_patterns: List[str]):
    """检查JSON文件分布"""
    print(f"\n🔍 检查JSON文件分布...")
    
    subfolder_files = discover_subfolder_json_files(base_dir, exclude_patterns)
    
    if not subfolder_files:
        print("❌ 未找到任何包含JSON文件的子文件夹")
        return False
    
    print(f"\n📊 JSON文件分布统计:")
    total_files = 0
    
    for folder_path, json_files in subfolder_files.items():
        folder_name = Path(folder_path).name
        file_count = len(json_files)
        total_files += file_count
        
        print(f"   📁 {folder_name}: {file_count} 个JSON文件")
        for json_file in json_files:
            print(f"      - {Path(json_file).name}")
    
    print(f"\n📈 总计: {total_files} 个JSON文件在 {len(subfolder_files)} 个文件夹中")
    return True

def test_output_directory_generation():
    """测试输出目录生成"""
    print(f"\n🔍 测试输出目录生成...")
    
    # 模拟几个输入文件
    test_files = [
        "/Users/liucun/Desktop/yuancailiao/folder1/report.json",
        "/Users/liucun/Desktop/yuancailiao/folder2/data.json"
    ]
    
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from run_batch_preprocess import get_output_directory
    
    for test_file in test_files:
        output_dir = get_output_directory(test_file, "/dummy/base")
        print(f"   {Path(test_file).name} -> {output_dir}")

def check_permissions(base_dir: str):
    """检查目录权限"""
    print(f"\n🔍 检查目录权限...")
    
    base_path = Path(base_dir)
    
    # 检查读取权限
    if not os.access(base_path, os.R_OK):
        print(f"❌ 基础目录无读取权限: {base_dir}")
        return False
    
    # 检查子目录的写入权限
    permission_issues = []
    
    for item in base_path.iterdir():
        if item.is_dir() and not item.name.endswith('_temp_pages'):
            if not os.access(item, os.W_OK):
                permission_issues.append(str(item))
    
    if permission_issues:
        print(f"⚠️ 以下子目录无写入权限:")
        for issue in permission_issues:
            print(f"   - {issue}")
        return False
    
    print(f"✅ 所有相关目录权限正常")
    return True

def main():
    """主函数"""
    print("🚀 子文件夹配置测试")
    print("=" * 50)
    
    # 获取配置
    subfolder_config = INPUT_CONFIG.get("subfolder_processing", {})
    
    if not subfolder_config.get("enabled", False):
        print("❌ 子文件夹处理功能未启用")
        print("请在 batch_config.py 中启用 subfolder_processing")
        return
    
    base_directory = subfolder_config.get("base_directory")
    exclude_patterns = subfolder_config.get("exclude_folder_patterns", [])
    
    print(f"📋 配置信息:")
    print(f"   基础目录: {base_directory}")
    print(f"   排除模式: {exclude_patterns}")
    print(f"   输出到源文件夹: {subfolder_config.get('output_in_source', False)}")
    
    # 运行测试
    tests_passed = 0
    total_tests = 5
    
    print(f"\n" + "=" * 50)
    print("开始测试...")
    
    # 测试1: 检查目录结构
    if check_directory_structure(base_directory):
        tests_passed += 1
        print("✅ 测试1: 目录结构检查通过")
    else:
        print("❌ 测试1: 目录结构检查失败")
    
    # 测试2: 检查JSON文件分布
    if check_json_files_distribution(base_directory, exclude_patterns):
        tests_passed += 1
        print("✅ 测试2: JSON文件分布检查通过")
    else:
        print("❌ 测试2: JSON文件分布检查失败")
    
    # 测试3: 检查权限
    if check_permissions(base_directory):
        tests_passed += 1
        print("✅ 测试3: 权限检查通过")
    else:
        print("❌ 测试3: 权限检查失败")
    
    # 测试4: 配置验证
    errors = validate_config()
    if not errors:
        tests_passed += 1
        print("✅ 测试4: 配置验证通过")
    else:
        print("❌ 测试4: 配置验证失败")
        for error in errors:
            print(f"   - {error}")
    
    # 测试5: 系统要求检查
    issues = check_system_requirements()
    if not issues:
        tests_passed += 1
        print("✅ 测试5: 系统要求检查通过")
    else:
        print("❌ 测试5: 系统要求检查失败")
        for issue in issues:
            print(f"   - {issue}")
    
    # 额外测试：输出目录生成
    try:
        test_output_directory_generation()
        print("✅ 额外测试: 输出目录生成测试通过")
    except Exception as e:
        print(f"❌ 额外测试: 输出目录生成测试失败: {e}")
    
    # 总结
    print(f"\n" + "=" * 50)
    print(f"📊 测试结果: {tests_passed}/{total_tests} 通过")
    
    if tests_passed == total_tests:
        print("🎉 所有测试通过！可以开始批量处理了")
        print("\n运行命令:")
        print("   python run_batch_preprocess.py")
    else:
        print("⚠️ 部分测试失败，请检查配置和环境")
        print("\n建议:")
        print("1. 检查目录路径是否正确")
        print("2. 确保目录包含JSON文件")
        print("3. 检查文件和目录权限")
        print("4. 安装必要的依赖")
    
    print("\n" + "=" * 50)

if __name__ == "__main__":
    main() 