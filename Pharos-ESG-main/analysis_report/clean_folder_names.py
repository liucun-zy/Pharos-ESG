#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件夹名称清理脚本
删除文件夹名中除了"-""_""."之外的所有符号
"""

import os
import sys
import re
from pathlib import Path

def clean_folder_name(folder_name):
    """
    清理文件夹名称，删除除了"-""_""."之外的所有符号
    
    Args:
        folder_name: 原始文件夹名称
        
    Returns:
        清理后的文件夹名称
    """
    # 保留字母、数字、中文字符、"-"、"_"、"."，删除其他所有符号
    cleaned_name = re.sub(r'[^\w\-\.\u4e00-\u9fff]', '', folder_name)
    return cleaned_name

def clean_folder_names_in_directory(root_path):
    """
    清理指定目录下所有文件夹的名称
    
    Args:
        root_path: 根目录路径
    """
    print("🧹 开始清理文件夹名称...")
    print(f"根目录: {root_path}")
    print("=" * 80)
    
    # 检查根目录是否存在
    if not os.path.exists(root_path):
        print(f"❌ 根目录不存在: {root_path}")
        return False
    
    if not os.path.isdir(root_path):
        print(f"❌ 指定路径不是目录: {root_path}")
        return False
    
    # 统计处理情况
    processed_count = 0
    skipped_count = 0
    error_count = 0
    no_change_count = 0
    
    try:
        # 遍历根目录下的所有项目
        for item in os.listdir(root_path):
            item_path = os.path.join(root_path, item)
            
            # 只处理文件夹
            if not os.path.isdir(item_path):
                print(f"⏭️  跳过文件: {item}")
                skipped_count += 1
                continue
            
            # 清理文件夹名称
            cleaned_name = clean_folder_name(item)
            
            # 检查是否需要重命名
            if cleaned_name == item:
                print(f"⏭️  无需修改: {item}")
                no_change_count += 1
                continue
            
            # 检查新名称是否已存在
            new_path = os.path.join(root_path, cleaned_name)
            if os.path.exists(new_path):
                print(f"⚠️  目标名称已存在，跳过: {item} -> {cleaned_name}")
                skipped_count += 1
                continue
            
            try:
                # 重命名文件夹
                os.rename(item_path, new_path)
                print(f"✅ 清理成功: {item} -> {cleaned_name}")
                processed_count += 1
            except Exception as e:
                print(f"❌ 重命名失败: {item} -> {cleaned_name}, 错误: {e}")
                error_count += 1
                
    except Exception as e:
        print(f"❌ 遍历目录时出错: {e}")
        return False
    
    # 输出统计结果
    print("=" * 80)
    print("📊 清理完成！")
    print(f"✅ 成功清理: {processed_count} 个文件夹")
    print(f"⏭️  无需修改: {no_change_count} 个文件夹")
    print(f"⏭️  跳过处理: {skipped_count} 个项目")
    print(f"❌ 处理失败: {error_count} 个项目")
    
    return True

def preview_changes(root_path):
    """
    预览将要进行的更改，不实际执行重命名
    
    Args:
        root_path: 根目录路径
    """
    print("👀 预览文件夹名称清理效果...")
    print(f"根目录: {root_path}")
    print("=" * 80)
    
    if not os.path.exists(root_path) or not os.path.isdir(root_path):
        print(f"❌ 根目录不存在或不是目录: {root_path}")
        return False
    
    changes_found = False
    
    try:
        for item in os.listdir(root_path):
            item_path = os.path.join(root_path, item)
            
            if not os.path.isdir(item_path):
                continue
            
            cleaned_name = clean_folder_name(item)
            
            if cleaned_name != item:
                print(f"📝 {item}")
                print(f"    -> {cleaned_name}")
                print()
                changes_found = True
        
        if not changes_found:
            print("✅ 没有需要清理的文件夹名称")
        else:
            print("💡 以上是预览效果，运行脚本时会实际执行重命名")
            
    except Exception as e:
        print(f"❌ 预览时出错: {e}")
        return False
    
    return True

def main():
    """主函数"""
    if len(sys.argv) >= 2:
        if sys.argv[1] == "--preview":
            root_path = sys.argv[2] if len(sys.argv) >= 3 else r"/Users/liucun/Desktop/nengyuan"
            preview_changes(root_path)
            return
        else:
            root_path = sys.argv[1]
    else:
        # 默认路径
        root_path = r"/Users/liucun/Desktop/nengyuan"
        print("🔧 使用默认路径，如需修改请运行：")
        print(f"python {__file__} <root_path>")
        print(f"python {__file__} --preview [root_path]  # 预览效果")
        print()
    
    # 执行清理
    success = clean_folder_names_in_directory(root_path)
    
    if success:
        print("\n💡 文件夹名称清理完成！")
    else:
        print("\n❌ 清理失败，请检查路径设置")

if __name__ == "__main__":
    main() 