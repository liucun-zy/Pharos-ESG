#!/usr/bin/env python3
"""
结构增强模块批量处理脚本 - 基于原始align_title.py逻辑

功能说明：
- 自动扫描基础路径下的子文件夹
- 查找 *_preprocessed.md 文件和同文件夹下的JPG图片
- 批量执行结构增强处理（标题提取 → 页面分组 → 标题对齐）
- 所有输出保存在原始子文件夹中
- ⚠️ 任何API调用失败都会立即终止程序

使用说明：
1. 修改下面的配置参数（主要是BASE_PATH和API Keys）
2. 运行脚本：python quick_structure_enhancement.py
3. 注意：VLM或DeepSeek API调用失败时程序会立即终止
"""

import os
import json
import glob
import sys
import tempfile
from pathlib import Path
from typing import List, Dict, Tuple
from structure_enhancement_module import TitleExtractor, StructureEnhancementConfig

# ==================== 配置区域 ====================
# 请修改以下路径为您的实际路径

# 基础路径
BASE_PATH = "/Users/liucun/Desktop/nengyuan"

# API配置
DEEPSEEK_R1_API_KEY = "xUFrf8g3N6dx5Jg252hDjiskZ"  # DeepSeek R1 API Key for LLM
QWEN_API_KEY = "sk-mhjyfsmkzrnxftbiqqohibxaqxoanulwmjctvtysnqknuwoq"     # Qwen API Key for VLM

# ==================== 文件发现函数 ====================

def discover_processing_folders(base_path: str) -> List[Dict[str, str]]:
    """
    发现需要处理的文件夹和对应的文件
    
    Args:
        base_path: 基础路径
        
    Returns:
        处理文件夹信息列表
    """
    folders_to_process = []
    base_path_obj = Path(base_path)
    
    print(f"🔍 扫描基础目录: {base_path}")
    
    # 遍历所有子文件夹
    for subfolder in base_path_obj.iterdir():
        if not subfolder.is_dir():
            continue
            
        # 排除 _temp_pages 结尾的文件夹
        if subfolder.name.endswith('_temp_pages'):
            print(f"⏭️ 跳过: {subfolder.name}")
            continue
        
        # 查找预处理后的Markdown文件
        md_files = list(subfolder.glob("*_preprocessed.md"))
        if not md_files:
            print(f"⚠️ 未找到预处理文件: {subfolder.name}")
            continue
        
        # 查找同一子文件夹下的JPG文件
        jpg_files = list(subfolder.glob("*.jpg")) + list(subfolder.glob("*.JPG"))
        
        if not jpg_files:
            print(f"⚠️ 未找到JPG文件: {subfolder.name}")
            continue
        
        # 优先选择可能的目录图片
        toc_image_candidates = [
            "page_2.jpg", "page_1.jpg", "toc.jpg", "contents.jpg", "目录.jpg",
            "page_2.JPG", "page_1.JPG", "toc.JPG", "contents.JPG", "目录.JPG"
        ]
        
        toc_image_path = None
        # 首先尝试优先候选者
        for candidate in toc_image_candidates:
            candidate_path = subfolder / candidate
            if candidate_path.exists():
                toc_image_path = str(candidate_path)
                break
        
        # 如果没有找到优先候选者，使用第一个JPG文件
        if not toc_image_path:
            toc_image_path = str(jpg_files[0])
            print(f"📸 使用第一个JPG文件: {jpg_files[0].name}")
        else:
            print(f"📸 使用优先JPG文件: {Path(toc_image_path).name}")
        
        folder_info = {
            "folder_name": subfolder.name,
            "folder_path": str(subfolder),
            "md_file": str(md_files[0]),  # 使用第一个找到的预处理文件
            "toc_image": toc_image_path,
            "output_dir": str(subfolder)
        }
        
        folders_to_process.append(folder_info) 
        print(f"✅ 发现: {subfolder.name}")
        print(f"   📄 MD文件: {Path(md_files[0]).name}")
        print(f"   📸 图片文件: {Path(toc_image_path).name}")
        if len(jpg_files) > 1: 
            print(f"   📊 总计JPG文件: {len(jpg_files)}个")
    
    print(f"\n📊 总共发现 {len(folders_to_process)} 个待处理文件夹")
    return folders_to_process

def process_single_folder(folder_info: Dict[str, str]) -> None:
    """
    处理单个文件夹
    
    Args:
        folder_info: 文件夹信息字典
        
    Note:
        失败时会立即终止程序，不返回失败状态
    """
    folder_name = folder_info["folder_name"]
    md_file = folder_info["md_file"]
    toc_image = folder_info["toc_image"]
    output_dir = folder_info["output_dir"]
    
    print(f"\n{'='*60}")
    print(f"🔄 处理文件夹: {folder_name}")
    print(f"{'='*60}")
    
    try:
        # 步骤1：从目录图片提取标题
        print("\n📸 步骤1：从目录图片提取标题...")
        
        # 创建标题文件路径
        titles_file = os.path.join(output_dir, "titles.json")
        
        # 创建配置
        config = StructureEnhancementConfig()
        config.qwen_api_key = QWEN_API_KEY
        config.deepseek_r1_api_key = DEEPSEEK_R1_API_KEY
        
        extractor = TitleExtractor(config)
        titles_result = extractor.process(toc_image, titles_file)
        
        if not titles_result['success']:
            print(f"❌ 标题提取失败: {titles_result.get('error', 'Unknown error')}")
            print(f"🚨 API调用失败，立即终止程序")
            print(f"📁 失败的文件夹: {folder_name}")
            sys.exit(1)
        
        print(f"✅ 标题提取成功，共提取 {len(titles_result.get('titles_data', []))} 个标题")
        print(f"📄 titles.json文件已生成: {titles_file}")
        
        # 显示提取的标题预览
        if titles_result.get('titles_data'):
            print("📋 提取的标题预览:")
            for i, title_item in enumerate(titles_result['titles_data'][:5], 1):  # 显示前5个标题
                title_text = title_item.get('title', '未知标题')
                level = title_item.get('level', 0)
                print(f"   {i}. {title_text} (层级: {level})")
            if len(titles_result['titles_data']) > 5:
                print(f"   ... 还有 {len(titles_result['titles_data']) - 5} 个标题")
        
        # 验证文件是否真的生成了
        if os.path.exists(titles_file):
            file_size = os.path.getsize(titles_file)
            print(f"📊 titles.json文件大小: {file_size} 字节")
        else:
            print("⚠️ titles.json文件生成失败")
        
        # 步骤2：页面分组处理
        print("\n📄 步骤2：页面分组处理...")
        from structure_enhancement_module.group_by_page_idx import group_by_page_idx
        
        grouped_md_path = os.path.join(output_dir, "grouped.md")
        group_by_page_idx(md_file, grouped_md_path)
        print(f"✅ 页面分组完成")
        
        # 步骤3：读取分组后的文件内容
        print("\n📖 步骤3：读取分组后的文件内容...")
        with open(grouped_md_path, 'r', encoding='utf-8') as f:
            content = f.read()
        print(f"✅ 成功读取，内容长度: {len(content)} 字符")
        
        # 步骤4：标题对齐
        print("\n🔄 步骤4：执行标题对齐...")
        output_md_path = os.path.join(output_dir, "aligned_output.md")
        
        # 如果对齐失败，函数内部会终止程序
        align_titles_with_original_logic(content, titles_file, output_md_path)
        
        print(f"✅ {folder_name} 处理完成！")
            
    except Exception as e:
        print(f"❌ {folder_name} 处理失败: {e}")
        import traceback
        print(f"错误详情:\n{traceback.format_exc()}")
        print(f"🚨 处理异常，可能是API调用失败，立即终止程序")
        print(f"📁 失败的文件夹: {folder_name}")
        sys.exit(1)

# ==================== 导入原始align_title逻辑 ====================

def align_titles_with_original_logic(content: str, titles_json_path: str, output_md_path: str) -> None:
    """使用原始align_title.py的完整逻辑进行标题对齐（使用DeepSeek R1架构）
    
    Note:
        失败时会立即终止程序，不返回失败状态
    """
    
    # 导入原始函数 - 确保使用所有核心功能
    from structure_enhancement_module.align_title import (
        align_titles, 
        process_unmatched_titles,
        process_json_titles,
        extract_chinese,
        normalize_title,
        is_title_match,
        get_title_level
    )
    
    print("=" * 60)
    print("开始标题对齐处理（使用DeepSeek R1架构）...")
    print("=" * 60)
    
    # 显示关键配置信息
    print(f"📄 输入内容长度: {len(content)} 字符")
    print(f"📁 标题JSON文件: {titles_json_path}")
    print(f"📁 输出文件: {output_md_path}")
    print(f"🔑 DeepSeek R1 API Key: {DEEPSEEK_R1_API_KEY[:20]}...")
    
    print("\n" + "-" * 40)
    print("阶段1: 标准匹配和模糊匹配")
    print("-" * 40)
    
    # 执行标题对齐 - 这包含了标准匹配、模糊匹配等所有核心逻辑
    success, unmatched_titles = align_titles(content, titles_json_path, output_md_path)
    
    if success:
        print("\n" + "=" * 60)
        print(f"✅ 标题对齐阶段完成")
        print(f"📊 未匹配标题数: {len(unmatched_titles)}")
        print("=" * 60)
        
        # 显示未匹配标题的详细信息
        if unmatched_titles:
            print("\n📋 未匹配标题列表:")
            for i, (json_title, json_level, json_index, parent, prev_title, next_title) in enumerate(unmatched_titles, 1):
                print(f"  {i}. '{json_title}' (层级: {json_level})")
                print(f"     前标题: '{prev_title}' | 后标题: '{next_title}'")
        
        # 处理未匹配的标题
        if unmatched_titles:
            print("\n" + "-" * 40)
            print("阶段2: 处理未匹配标题（DeepSeek R1专业插入）")
            print("-" * 40)
            
            # 加载标题JSON
            with open(titles_json_path, 'r', encoding='utf-8') as f:
                titles_json = json.load(f)
            
            print(f"🔄 开始处理 {len(unmatched_titles)} 个未匹配标题...")
            print(f"🤖 使用DeepSeek R1进行专业位置分析和插入...")
            
            # 处理未匹配标题 - 这包含了搜索范围、LLM输入格式等所有逻辑
            unmatched_success = process_unmatched_titles(
                output_md_path, 
                unmatched_titles, 
                titles_json, 
                DEEPSEEK_R1_API_KEY
            )
            
            print("\n" + "=" * 60)
            if unmatched_success:
                print("✅ 未匹配标题处理完成")
            else:
                print("⚠️  未匹配标题处理部分失败")
                print("🚨 DeepSeek API调用失败，立即终止程序")
                sys.exit(1)
            print("=" * 60)
        else:
            print("\n🎉 所有标题都已成功匹配，无需处理未匹配标题")
    else:
        print("\n" + "=" * 60)
        print("❌ 标题对齐失败")
        print("=" * 60)
        print("🚨 DeepSeek API调用失败，立即终止程序")
        sys.exit(1)

# ==================== 主程序 ====================

def main():
    """主函数 - 批量处理多个文件夹"""
    print("🚀 开始ESG报告结构增强批量处理（使用DeepSeek R1专业架构）...")
    print(f"📁 基础路径: {BASE_PATH}")
    
    # 检查基础路径是否存在
    if not os.path.exists(BASE_PATH):
        print(f"❌ 错误：基础路径不存在: {BASE_PATH}")
        return
    
    try:
        # 步骤1：发现需要处理的文件夹
        print("\n🔍 步骤1：扫描并发现处理目标...")
        folders_to_process = discover_processing_folders(BASE_PATH)
        
        if not folders_to_process:
            print("❌ 未找到任何需要处理的文件夹")
            print("\n🔧 请确认:")
            print("1. 基础路径中包含子文件夹")
            print("2. 子文件夹中包含 *_preprocessed.md 文件")
            print("3. 子文件夹中包含JPG图片文件 (*.jpg 或 *.JPG)")
            return
        
        # 步骤2：批量处理
        print(f"\n🔄 步骤2：开始批量处理 {len(folders_to_process)} 个文件夹...")
        print("⚠️ 注意：任何API调用失败都会立即终止程序")
        
        successful_count = 0
        
        for i, folder_info in enumerate(folders_to_process, 1):
            print(f"\n📊 进度: {i}/{len(folders_to_process)}")
            
            # 如果process_single_folder失败，程序会在函数内部终止
            process_single_folder(folder_info)
            successful_count += 1
        
        # 步骤3：显示处理完成的文件路径
        print(f"\n{'='*60}")
        print("📊 批量处理完成统计")
        print(f"{'='*60}")
        print(f"✅ 成功处理: {successful_count} 个文件夹")
        
        print(f"\n📄 处理完成的文件:")
        for folder_info in folders_to_process:
            folder_name = folder_info["folder_name"]
            output_file = os.path.join(folder_info["output_dir"], "aligned_output.md")
            
            if os.path.exists(output_file):
                # 显示文件信息
                try:
                    with open(output_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # 统计标题数量
                    import re
                    heading_re = re.compile(r'^(#+)\s*(.+?)\s*$', re.MULTILINE)
                    titles = heading_re.findall(content)
                    
                    print(f"   📁 {folder_name}")
                    print(f"      📄 文件: {output_file}")
                    print(f"      📊 长度: {len(content)} 字符")
                    print(f"      📋 标题数: {len(titles)}")
                except Exception as e:
                    print(f"   📁 {folder_name}: {output_file} (读取统计失败)")
        
        print(f"\n🎉 所有文件夹处理完成！")
        
    except Exception as e:
        print(f"❌ 批量处理失败: {e}")
        import traceback
        print(f"错误详情:\n{traceback.format_exc()}")
        
        print("\n🔧 可能的解决方案:")
        print("1. 检查基础路径是否正确")
        print("2. 检查API配置是否正确")
        print("3. 检查预处理文件(*_preprocessed.md)是否存在")
        print("4. 检查JPG图片文件是否存在")
        print("5. 检查网络连接是否正常")
        print("6. 检查输出目录是否有写入权限")
        
        print(f"\n🚨 程序遇到异常，立即终止")
        sys.exit(1)

if __name__ == "__main__":
    main() 