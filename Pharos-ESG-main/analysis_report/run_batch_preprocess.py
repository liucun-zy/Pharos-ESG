#!/usr/bin/env python3
"""
批量预处理模块运行脚本

支持：
1. 批量处理多个JSON文件
2. 目录扫描自动发现文件
3. 并行处理（可选）
4. 详细的处理报告
5. 错误恢复和重试机制

使用说明：
1. 修改下面的配置参数
2. 运行脚本：python run_batch_preprocess.py
"""

import os
import sys
import glob
import time
from pathlib import Path
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

# 添加preprocess_module到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from preprocess_module import BatchPreprocessPipeline, PreprocessConfig

# 导入配置
from batch_config import (
    INPUT_CONFIG, 
    PERFORMANCE_CONFIG, 
    ERROR_HANDLING_CONFIG,
    create_preprocess_config,
    get_config_for_environment,
    check_system_requirements,
    validate_config
)

# ==================== 配置区域 ====================

# 从配置文件中读取设置
INPUT_FILES = INPUT_CONFIG["specific_files"]
INPUT_DIRECTORY = INPUT_CONFIG["directory_scan"]["directory"] if INPUT_CONFIG["directory_scan"]["enabled"] else None
PATTERN = INPUT_CONFIG["directory_scan"]["pattern"]
OUTPUT_BASE_DIR = INPUT_CONFIG["output_base_dir"]
SUBFOLDER_PROCESSING = INPUT_CONFIG.get("subfolder_processing", {}).get("enabled", False)

# 性能配置
ENABLE_PARALLEL = PERFORMANCE_CONFIG["parallel_processing"]["enabled"]
MAX_WORKERS = PERFORMANCE_CONFIG["parallel_processing"]["max_workers"]

# 错误处理配置
CONTINUE_ON_ERROR = ERROR_HANDLING_CONFIG["continue_on_error"]
MAX_RETRIES = ERROR_HANDLING_CONFIG["max_retries"]

# 处理配置（可以选择环境：development, testing, production）
ENVIRONMENT = "production"  # 修改这里选择不同的配置模式
config = get_config_for_environment(ENVIRONMENT)

# ==================== 主程序 ====================

def discover_json_files(directory: str, pattern: str = "**/*.json") -> List[str]:
    """
    自动发现目录中的JSON文件
    
    Args:
        directory: 搜索目录
        pattern: 文件匹配模式
        
    Returns:
        JSON文件路径列表
    """
    if not directory or not os.path.exists(directory):
        return []
    
    search_path = Path(directory)
    json_files = []
    
    try:
        # 使用glob模式搜索文件
        for file_path in search_path.glob(pattern):
            if file_path.is_file() and file_path.suffix.lower() == '.json':
                json_files.append(str(file_path))
        
        print(f"📁 在目录 {directory} 中发现 {len(json_files)} 个JSON文件")
        
    except Exception as e:
        print(f"❌ 搜索目录时出错: {e}")
    
    return json_files

def discover_subfolder_json_files(base_directory: str, exclude_patterns: List[str] = None) -> Dict[str, List[str]]:
    """
    扫描子文件夹中的JSON文件
    
    Args:
        base_directory: 基础目录
        exclude_patterns: 排除的文件夹模式
        
    Returns:
        字典，键为子文件夹路径，值为该文件夹中的JSON文件列表
    """
    if not base_directory or not os.path.exists(base_directory):
        return {}
    
    if exclude_patterns is None:
        exclude_patterns = []
    
    base_path = Path(base_directory)
    subfolder_files = {}
    
    try:
        # 遍历所有子文件夹
        for subfolder in base_path.iterdir():
            if not subfolder.is_dir():
                continue
                
            # 检查是否匹配排除模式
            exclude_folder = False
            for exclude_pattern in exclude_patterns:
                if subfolder.name.endswith(exclude_pattern.lstrip('*')):
                    exclude_folder = True
                    break
            
            if exclude_folder:
                print(f"⏭️ 跳过文件夹: {subfolder.name}")
                continue
            
            # 搜索该文件夹中的JSON文件
            json_files = []
            for json_file in subfolder.glob("*.json"):
                if json_file.is_file():
                    json_files.append(str(json_file))
            
            if json_files:
                subfolder_files[str(subfolder)] = json_files
                print(f"📁 文件夹 {subfolder.name} 中发现 {len(json_files)} 个JSON文件")
            else:
                print(f"⚠️ 文件夹 {subfolder.name} 中未发现JSON文件")
        
        total_files = sum(len(files) for files in subfolder_files.values())
        print(f"📊 总共发现 {len(subfolder_files)} 个有效文件夹，包含 {total_files} 个JSON文件")
        
    except Exception as e:
        print(f"❌ 扫描子文件夹时出错: {e}")
    
    return subfolder_files

def get_output_directory(input_file: str, base_dir: str) -> str:
    """
    为输入文件生成输出目录
    
    Args:
        input_file: 输入文件路径
        base_dir: 输出基础目录
        
    Returns:
        输出目录路径
    """
    input_path = Path(input_file)
    
    # 如果启用子文件夹处理，输出到源文件所在的文件夹
    if SUBFOLDER_PROCESSING and INPUT_CONFIG.get("subfolder_processing", {}).get("output_in_source", False):
        # 输出到源文件所在的文件夹
        return str(input_path.parent)
    else:
        # 传统模式：创建基于文件名的输出目录
        file_name = input_path.stem
        output_dir = Path(base_dir) / f"{file_name}_processed"
        return str(output_dir)

def process_single_file(input_file: str, output_dir: str, config: PreprocessConfig, 
                       retry_count: int = 0) -> Dict[str, Any]:
    """
    处理单个文件
    
    Args:
        input_file: 输入文件路径
        output_dir: 输出目录
        config: 配置对象
        retry_count: 当前重试次数
        
    Returns:
        处理结果字典
    """
    try:
        print(f"📄 处理文件: {Path(input_file).name}")
        
        # 创建处理管道
        pipeline = BatchPreprocessPipeline(config)
        
        # 处理文件
        result = pipeline.run_batch([input_file], output_dir)
        
        print(f"✅ 完成文件: {Path(input_file).name}")
        return {
            "status": "success",
            "input_file": input_file,
            "output_dir": output_dir,
            "result": result,
            "retry_count": retry_count
        }
        
    except Exception as e:
        error_msg = f"❌ 处理文件失败: {Path(input_file).name} - {str(e)}"
        print(error_msg)
        
        # 重试逻辑
        if retry_count < MAX_RETRIES:
            print(f"🔄 重试处理 ({retry_count + 1}/{MAX_RETRIES}): {Path(input_file).name}")
            time.sleep(2)  # 等待2秒后重试
            return process_single_file(input_file, output_dir, config, retry_count + 1)
        
        return {
            "status": "failed",
            "input_file": input_file,
            "output_dir": output_dir,
            "error": str(e),
            "retry_count": retry_count
        }

def process_files_parallel(input_files: List[str], base_output_dir: str, 
                          config: PreprocessConfig) -> List[Dict[str, Any]]:
    """
    并行处理多个文件
    
    Args:
        input_files: 输入文件列表
        base_output_dir: 输出基础目录
        config: 配置对象
        
    Returns:
        处理结果列表
    """
    results = []
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # 提交任务
        future_to_file = {}
        for input_file in input_files:
            output_dir = get_output_directory(input_file, base_output_dir)
            future = executor.submit(process_single_file, input_file, output_dir, config)
            future_to_file[future] = input_file
        
        # 收集结果
        for future in as_completed(future_to_file):
            input_file = future_to_file[future]
            try:
                result = future.result()
                results.append(result)
                
                if not CONTINUE_ON_ERROR and result["status"] == "failed":
                    print(f"🛑 遇到错误，停止处理")
                    break
                    
            except Exception as e:
                print(f"❌ 处理任务时出现意外错误: {e}")
                results.append({
                    "status": "failed",
                    "input_file": input_file,
                    "error": str(e)
                })
    
    return results

def process_files_sequential(input_files: List[str], base_output_dir: str, 
                           config: PreprocessConfig) -> List[Dict[str, Any]]:
    """
    顺序处理多个文件
    
    Args:
        input_files: 输入文件列表
        base_output_dir: 输出基础目录
        config: 配置对象
        
    Returns:
        处理结果列表
    """
    results = []
    
    for i, input_file in enumerate(input_files, 1):
        print(f"\n📊 进度: {i}/{len(input_files)}")
        
        output_dir = get_output_directory(input_file, base_output_dir)
        result = process_single_file(input_file, output_dir, config)
        results.append(result)
        
        if not CONTINUE_ON_ERROR and result["status"] == "failed":
            print(f"🛑 遇到错误，停止处理")
            break
    
    return results

def generate_summary_report(results: List[Dict[str, Any]], output_dir: str):
    """
    生成批量处理总结报告
    
    Args:
        results: 处理结果列表
        output_dir: 输出目录
    """
    # 统计信息
    total_files = len(results)
    successful_files = sum(1 for r in results if r["status"] == "success")
    failed_files = total_files - successful_files
    
    # 生成报告
    report = {
        "batch_processing_summary": {
            "total_files": total_files,
            "successful_files": successful_files,
            "failed_files": failed_files,
            "success_rate": f"{successful_files/total_files*100:.1f}%" if total_files > 0 else "0%"
        },
        "file_results": results,
        "processing_config": config.to_dict(),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # 保存报告
    report_path = Path(output_dir) / "batch_processing_report.json"
    os.makedirs(output_dir, exist_ok=True)
    
    import json
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n📋 处理报告已保存: {report_path}")
    return report

def main():
    """主函数"""
    print("🚀 开始批量ESG报告预处理...")
    
    # 系统检查
    print("🔍 检查系统要求...")
    issues = check_system_requirements()
    if issues:
        print("⚠️ 系统检查发现以下问题:")
        for issue in issues:
            print(f"   - {issue}")
        
        # 询问是否继续
        response = input("是否继续执行？(y/N): ").lower()
        if response not in ['y', 'yes']:
            print("🛑 用户选择退出")
            return
    
    # 配置验证
    print("\n🔍 验证配置...")
    errors = validate_config()
    if errors:
        print("❌ 配置验证失败:")
        for error in errors:
            print(f"   - {error}")
        print("请修改 batch_config.py 文件中的配置")
        return
    
    print(f"✅ 配置验证通过 (环境: {ENVIRONMENT})")
    
    # 收集输入文件
    input_files = []
    
    # 方式1: 从指定的文件列表
    if INPUT_FILES:
        for file_path in INPUT_FILES:
            if os.path.exists(file_path):
                input_files.append(file_path)
            else:
                print(f"⚠️ 文件不存在: {file_path}")
    
    # 方式2: 子文件夹处理模式
    if SUBFOLDER_PROCESSING:
        subfolder_config = INPUT_CONFIG.get("subfolder_processing", {})
        base_directory = subfolder_config.get("base_directory", INPUT_DIRECTORY)
        exclude_patterns = subfolder_config.get("exclude_folder_patterns", [])
        
        print(f"🔍 使用子文件夹处理模式，扫描目录: {base_directory}")
        subfolder_files = discover_subfolder_json_files(base_directory, exclude_patterns)
        
        # 收集所有文件
        for folder_path, json_files in subfolder_files.items():
            input_files.extend(json_files)
    
    # 方式3: 从目录扫描 (传统模式)
    elif INPUT_DIRECTORY:
        discovered_files = discover_json_files(INPUT_DIRECTORY, PATTERN)
        input_files.extend(discovered_files)
    
    # 去重
    input_files = list(set(input_files))
    
    if not input_files:
        print("❌ 未找到任何需要处理的JSON文件")
        print("请检查：")
        print("1. INPUT_FILES 列表中的文件路径是否正确")
        print("2. INPUT_DIRECTORY 是否设置正确")
        print("3. 目录中是否包含.json文件")
        return
    
    print(f"📁 找到 {len(input_files)} 个文件需要处理")
    
    # 确保输出目录存在
    os.makedirs(OUTPUT_BASE_DIR, exist_ok=True)
    
    # 开始处理
    start_time = time.time()
    
    try:
        if ENABLE_PARALLEL and len(input_files) > 1:
            print(f"🔄 使用并行处理模式 (工作线程: {MAX_WORKERS})")
            results = process_files_parallel(input_files, OUTPUT_BASE_DIR, config)
        else:
            print("🔄 使用顺序处理模式")
            results = process_files_sequential(input_files, OUTPUT_BASE_DIR, config)
        
        # 处理完成
        end_time = time.time()
        processing_time = end_time - start_time
        
        print(f"\n✅ 批量处理完成！")
        print(f"⏱️ 总处理时间: {processing_time:.2f} 秒")
        
        # 生成总结报告
        if SUBFOLDER_PROCESSING:
            # 子文件夹处理模式：将报告保存在基础目录中
            base_directory = INPUT_CONFIG.get("subfolder_processing", {}).get("base_directory", INPUT_DIRECTORY)
            report = generate_summary_report(results, base_directory)
        else:
            # 传统模式：保存在输出基础目录
            report = generate_summary_report(results, OUTPUT_BASE_DIR)
        
        # 显示总结
        summary = report["batch_processing_summary"]
        print(f"\n📊 处理统计:")
        print(f"   总文件数: {summary['total_files']}")
        print(f"   成功文件数: {summary['successful_files']}")
        print(f"   失败文件数: {summary['failed_files']}")
        print(f"   成功率: {summary['success_rate']}")
        
        # 显示失败的文件
        failed_files = [r for r in results if r["status"] == "failed"]
        if failed_files:
            print(f"\n❌ 失败的文件:")
            for failed in failed_files:
                print(f"   - {Path(failed['input_file']).name}: {failed.get('error', 'Unknown error')}")
        
        # 显示输出位置
        if SUBFOLDER_PROCESSING:
            print(f"\n📁 输出位置: 各文件的源文件夹中")
            print(f"   每个子文件夹都包含相应的处理结果")
        else:
            print(f"\n📁 输出目录: {OUTPUT_BASE_DIR}")
        
    except KeyboardInterrupt:
        print(f"\n⏹️ 用户中断处理")
    except Exception as e:
        print(f"❌ 批量处理出现异常: {e}")

if __name__ == "__main__":
    main() 