#!/usr/bin/env python3
"""
通用元数据添加工具

为ESG报告处理过程中的JSON文件添加元数据信息，包括：
- 股票代码
- 公司名称  
- 报告年份
- 报告名称
- 报告类型

支持批量处理和不同的JSON结构格式。
"""

import json
import os
import re
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional

def extract_metadata_from_filename(file_path: str) -> Dict[str, Any]:
    """
    从文件路径中提取元数据信息
    
    Args:
        file_path: 文件路径，例如：
        "/path/300497.SZ-富祥药业-2024年度环境、社会及公司治理(ESG)报告_grouped.json"
    
    Returns:
        dict: 包含元数据的字典
    """
    # 获取文件名（不含路径和扩展名）
    filename = os.path.splitext(os.path.basename(file_path))[0]
    
    # 移除常见的后缀
    suffixes_to_remove = ['_grouped', '_vlm', '_clustered', '_aligned', '_processed', '_final']
    for suffix in suffixes_to_remove:
        if filename.endswith(suffix):
            filename = filename[:-len(suffix)]
            break
    
    # 定义正则表达式模式来解析文件名
    # 格式: 股票代码-公司名称-报告年份-报告类型
    pattern = r'^([^-]+)-([^-]+)-(\d{4})年度(.+)$'
    
    match = re.match(pattern, filename)
    
    if match:
        stock_code = match.group(1).strip()
        company_name = match.group(2).strip()
        report_year = int(match.group(3))
        report_type = match.group(4).strip()
        
        # 构建完整的报告名称
        report_name = f"{report_year}年度{report_type}"
        
        return {
            "stock_code": stock_code,
            "company_name": company_name,
            "report_year": report_year,
            "report_name": report_name,
            "report_type": report_type,
            "original_filename": os.path.basename(file_path),
            "processing_timestamp": None,  # 可以在处理时添加时间戳
            "file_size_bytes": None,  # 可以添加文件大小信息
            "data_source": "ESG_REPORT_PROCESSING"  # 数据来源标识
        }
    else:
        # 如果无法解析，返回默认值
        return {
            "stock_code": "UNKNOWN",
            "company_name": "未知公司",
            "report_year": None,
            "report_name": "未知报告",
            "report_type": "未知类型",
            "original_filename": os.path.basename(file_path),
            "processing_timestamp": None,
            "file_size_bytes": None,
            "data_source": "ESG_REPORT_PROCESSING"
        }

def add_file_info_to_metadata(metadata: Dict[str, Any], file_path: str) -> Dict[str, Any]:
    """
    为元数据添加文件相关信息
    
    Args:
        metadata: 基础元数据字典
        file_path: 文件路径
    
    Returns:
        dict: 增强后的元数据字典
    """
    import time
    
    try:
        file_stat = os.stat(file_path)
        metadata.update({
            "processing_timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            "file_size_bytes": file_stat.st_size,
            "file_modified_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(file_stat.st_mtime))
        })
    except OSError:
        pass
    
    return metadata

def add_metadata_to_json(input_path: str, output_path: str = None, 
                        structure_type: str = "auto", backup: bool = True) -> Dict[str, Any]:
    """
    为JSON文件添加元数据
    
    Args:
        input_path: 输入JSON文件路径
        output_path: 输出JSON文件路径（如果为None，则覆盖原文件）
        structure_type: JSON结构类型 ("auto", "pages", "blocks", "raw")
        backup: 是否创建备份文件
    
    Returns:
        dict: 处理结果信息
    """
    if output_path is None:
        output_path = input_path
    
    # 创建备份
    if backup and input_path == output_path:
        backup_path = f"{input_path}.backup"
        if os.path.exists(backup_path):
            # 如果备份已存在，添加时间戳
            import time
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            backup_path = f"{input_path}.backup.{timestamp}"
        
        import shutil
        shutil.copy2(input_path, backup_path)
        print(f"📁 创建备份文件: {backup_path}")
    
    # 读取原始JSON
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        return {"status": "error", "message": f"读取JSON文件失败: {e}"}
    
    # 提取元数据
    metadata = extract_metadata_from_filename(input_path)
    metadata = add_file_info_to_metadata(metadata, input_path)
    
    # 检查是否已经有元数据
    if isinstance(data, dict) and "metadata" in data:
        print("⚠️  文件已包含元数据，将进行更新")
        # 更新现有元数据，保留原有的其他字段
        existing_metadata = data["metadata"]
        if isinstance(existing_metadata, dict):
            existing_metadata.update(metadata)
            metadata = existing_metadata
    
    # 根据结构类型处理数据
    if structure_type == "auto":
        # 自动检测结构类型
        if isinstance(data, dict):
            if "pages" in data:
                structure_type = "pages"
            elif "metadata" in data:
                structure_type = "existing"
            elif all(key in data for key in ["h1", "h2", "data_type"]) if len(data) > 0 else False:
                structure_type = "blocks"
            else:
                structure_type = "raw"
        elif isinstance(data, list):
            structure_type = "blocks"
        else:
            structure_type = "raw"
    
    # 构建最终输出结构
    if structure_type == "pages":
        # 已经是pages结构，只更新metadata
        final_output = {
            "metadata": metadata,
            "pages": data.get("pages", data)
        }
    elif structure_type == "existing":
        # 已有metadata结构，更新metadata
        final_output = data.copy()
        final_output["metadata"] = metadata
    elif structure_type == "blocks":
        # 块结构数据，包装为标准格式
        final_output = {
            "metadata": metadata,
            "data": data
        }
    else:
        # 原始数据，直接包装
        final_output = {
            "metadata": metadata,
            "content": data
        }
    
    # 保存结果
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(final_output, f, ensure_ascii=False, indent=2)
        
        return {
            "status": "success",
            "input_path": input_path,
            "output_path": output_path,
            "structure_type": structure_type,
            "metadata": metadata,
            "backup_created": backup and input_path == output_path
        }
    except Exception as e:
        return {"status": "error", "message": f"保存JSON文件失败: {e}"}

def batch_add_metadata(input_dir: str, pattern: str = "*.json", 
                      output_dir: str = None, backup: bool = True) -> List[Dict[str, Any]]:
    """
    批量为JSON文件添加元数据
    
    Args:
        input_dir: 输入目录
        pattern: 文件匹配模式
        output_dir: 输出目录（如果为None，则原地更新）
        backup: 是否创建备份
    
    Returns:
        list: 处理结果列表
    """
    input_path = Path(input_dir)
    results = []
    
    # 查找匹配的文件
    json_files = list(input_path.glob(pattern))
    
    if not json_files:
        print(f"❌ 在目录 {input_dir} 中未找到匹配 {pattern} 的文件")
        return results
    
    print(f"🔍 找到 {len(json_files)} 个JSON文件")
    
    for json_file in json_files:
        print(f"\n📄 处理文件: {json_file.name}")
        
        # 确定输出路径
        if output_dir:
            output_path = Path(output_dir) / json_file.name
            os.makedirs(output_dir, exist_ok=True)
        else:
            output_path = json_file
        
        # 添加元数据
        result = add_metadata_to_json(str(json_file), str(output_path), backup=backup)
        result["file_name"] = json_file.name
        results.append(result)
        
        if result["status"] == "success":
            print(f"✅ 成功处理: {json_file.name}")
        else:
            print(f"❌ 处理失败: {json_file.name} - {result.get('message', 'Unknown error')}")
    
    return results

def main():
    """命令行主函数"""
    parser = argparse.ArgumentParser(description="为ESG报告JSON文件添加元数据")
    parser.add_argument("input", help="输入JSON文件或目录路径")
    parser.add_argument("-o", "--output", help="输出文件或目录路径（可选）")
    parser.add_argument("-t", "--type", choices=["auto", "pages", "blocks", "raw"], 
                       default="auto", help="JSON结构类型")
    parser.add_argument("-p", "--pattern", default="*.json", help="批量处理时的文件匹配模式")
    parser.add_argument("--no-backup", action="store_true", help="不创建备份文件")
    parser.add_argument("-v", "--verbose", action="store_true", help="详细输出")
    
    args = parser.parse_args()
    
    input_path = Path(args.input)
    backup = not args.no_backup
    
    if input_path.is_file():
        # 处理单个文件
        print(f"🚀 处理单个文件: {input_path}")
        result = add_metadata_to_json(str(input_path), args.output, args.type, backup)
        
        if result["status"] == "success":
            print("✅ 处理成功!")
            if args.verbose:
                print("\n📊 提取的元数据:")
                for key, value in result["metadata"].items():
                    print(f"   {key}: {value}")
        else:
            print(f"❌ 处理失败: {result.get('message', 'Unknown error')}")
    
    elif input_path.is_dir():
        # 批量处理目录
        print(f"🚀 批量处理目录: {input_path}")
        results = batch_add_metadata(str(input_path), args.pattern, args.output, backup)
        
        # 统计结果
        success_count = sum(1 for r in results if r["status"] == "success")
        total_count = len(results)
        
        print(f"\n📊 批量处理完成:")
        print(f"   总文件数: {total_count}")
        print(f"   成功处理: {success_count}")
        print(f"   失败处理: {total_count - success_count}")
        
        if args.verbose and results:
            print("\n📋 详细结果:")
            for result in results:
                status_icon = "✅" if result["status"] == "success" else "❌"
                print(f"   {status_icon} {result['file_name']}")
    
    else:
        print(f"❌ 路径不存在: {input_path}")

if __name__ == "__main__":
    # 如果直接运行，执行命令行接口
    main()

# 使用示例:
"""
# 1. 为单个文件添加元数据
python add_metadata.py report.json

# 2. 为单个文件添加元数据并保存到新文件
python add_metadata.py report.json -o report_with_metadata.json

# 3. 批量处理目录中的所有JSON文件
python add_metadata.py /path/to/reports/

# 4. 批量处理特定模式的文件
python add_metadata.py /path/to/reports/ -p "*_grouped.json"

# 5. 处理时不创建备份
python add_metadata.py report.json --no-backup

# 6. 详细输出模式
python add_metadata.py report.json -v
""" 