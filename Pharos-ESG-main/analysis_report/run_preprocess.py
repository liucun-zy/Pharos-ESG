#!/usr/bin/env python3
"""
预处理模块运行脚本 - 批量处理版本

使用说明：
1. 修改下面的 BASE_PATH 为您的输入JSON文件根目录路径
2. 运行脚本：python run_preprocess.py
3. 脚本会自动查找所有JSON文件并逐个处理
4. 遇到任何错误时会立即停止，方便检查问题
"""

import os
import json
import sys
from pathlib import Path
from preprocess_module import quick_preprocess, PreprocessConfig

# ==================== 配置区域 ====================
# 请修改以下路径为您的实际路径

# 输入JSON文件根目录路径
BASE_PATH = r"/Users/liucun/Desktop/nengyuan"

# ==================== 高级配置（可选）====================
# 如果需要自定义配置，取消下面的注释并修改参数

config = PreprocessConfig()

# === 图片文件夹配置 ===
config.main_images_dir = None  # 设置为None，使用自动搜索模式
config.auto_search_images = True  # 启用自动搜索图片文件夹
config.image_folder_patterns = [
    "{base_name}_temp_images",  # 默认模式：文件名_temp_images
    # "{base_name}_images",       # 备选模式：文件名_images
    # "{base_name}",              # 直接文件名
    # "{base_name}_页面图片",      # 中文模式
    # "{base_name}_pages"         # 页面模式
]

# === OCR配置 ===
config.ocr_languages = "chi_sim+chi_tra+eng"  # OCR语言设置：简体中文+繁体中文+英文
config.confidence_threshold = 40.0    # OCR置信度阈值
config.min_text_length = 20           # 最小文本长度
config.log_level = "INFO"            # 日志级别

# 使用自定义配置
# config = None

# ==================== 主程序 ====================

def find_json_files(base_path):
    """
    在指定目录下递归查找所有JSON文件
    
    Args:
        base_path: 根目录路径
        
    Returns:
        JSON文件路径列表
    """
    json_files = []
    base_path = Path(base_path)
    
    if not base_path.exists():
        print(f"❌ 根目录不存在: {base_path}")
        print("程序立即停止，请检查路径配置")
        sys.exit(1)
    
    # 需要跳过的文件名模式
    skip_patterns = [
        'preprocess_batch_log.json',
        'preprocess_config.json', 
        'preprocess_report.json',
        'config.json',
        'log.json',
        'batch_log.json',
        '_log.json',
        '_config.json',
        '_report.json'
    ]
    
    # 递归查找所有JSON文件
    for json_file in base_path.rglob("*.json"):
        # 跳过临时文件和系统文件
        if json_file.name.startswith('.') or json_file.name.startswith('~'):
            continue
            
        # 跳过日志文件和配置文件
        should_skip = False
        for pattern in skip_patterns:
            if json_file.name == pattern or json_file.name.endswith(pattern):
                should_skip = True
                break
        
        if should_skip:
            print(f"⏭️  跳过非ESG报告文件: {json_file.name}")
            continue
            
        json_files.append(json_file)
    
    return json_files

def process_single_json(json_path, config):
    """
    处理单个JSON文件
    
    Args:
        json_path: JSON文件路径
        config: 预处理配置
        
    Returns:
        处理结果字典
    """
    json_path = Path(json_path)
    output_dir = json_path.parent  # 输出到同一目录
    
    print(f"\n🔧 处理文件: {json_path.name}")
    print(f"📁 输出目录: {output_dir}")
    
    # 检查输入文件是否存在
    if not json_path.exists():
        print(f"❌ 输入文件不存在: {json_path}")
        print("程序立即停止，请检查文件路径")
        sys.exit(1)
    
    # 检查文件是否可读
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ JSON文件格式错误: {e}")
        print("程序立即停止，请检查JSON文件格式")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 无法读取JSON文件: {e}")
        print("程序立即停止，请检查文件权限")
        sys.exit(1)
    
    # 检查输出目录权限
    try:
        test_file = output_dir / ".test_write_permission"
        test_file.touch()
        test_file.unlink()
    except Exception as e:
        print(f"❌ 输出目录无写入权限: {e}")
        print("程序立即停止，请检查目录权限")
        sys.exit(1)
    
    try:
        # 运行预处理
        result = quick_preprocess(
            input_json_path=str(json_path),
            output_dir=str(output_dir),
            config=config
        )
        
        # 详细检查处理结果
        if not result:
            print(f"❌ 预处理返回空结果")
            print("程序立即停止，请检查处理逻辑")
            sys.exit(1)
        
        # 检查处理结果中的错误
        if "processing_results" in result:
            for step_name, step_result in result["processing_results"].items():
                if isinstance(step_result, dict):
                    status = step_result.get("status", "unknown")
                    
                    if status == "failed":
                        error_msg = step_result.get('error', '未知错误')
                        print(f"❌ {step_name} 步骤失败: {error_msg}")
                        print("程序立即停止，请检查失败原因")
                        sys.exit(1)
                    elif status == "error":
                        error_msg = step_result.get('error', '未知错误')
                        print(f"❌ {step_name} 步骤出错: {error_msg}")
                        print("程序立即停止，请检查错误原因")
                        sys.exit(1)
                    elif "error" in step_result:
                        error_msg = step_result.get('error', '未知错误')
                        print(f"❌ {step_name} 步骤包含错误信息: {error_msg}")
                        print("程序立即停止，请检查错误原因")
                        sys.exit(1)
        
        # 检查是否有异常字段
        if "error" in result:
            print(f"❌ 处理结果包含错误: {result['error']}")
            print("程序立即停止，请检查错误原因")
            sys.exit(1)
        
        if "exception" in result:
            print(f"❌ 处理过程中发生异常: {result['exception']}")
            print("程序立即停止，请检查异常原因")
            sys.exit(1)
        
        # 显示单个文件的结果
        print(f"✅ {json_path.name} 处理完成！")
        
        if "processing_results" in result:
            for step_name, step_result in result["processing_results"].items():
                if isinstance(step_result, dict):
                    status = step_result.get("status", "unknown")
                    if status == "success":
                        print(f"   {step_name}: ✅ 成功")
                    elif status == "skipped":
                        print(f"   {step_name}: ⏭️ 跳过")
                    else:
                        print(f"   {step_name}: ❓ {status}")
        
        return {
            "file": json_path.name,
            "status": "success",
            "result": result
        }
        
    except FileNotFoundError as e:
        print(f"❌ 文件不存在错误: {e}")
        print("程序立即停止，请检查文件路径")
        sys.exit(1)
    except PermissionError as e:
        print(f"❌ 权限错误: {e}")
        print("程序立即停止，请检查文件权限")
        sys.exit(1)
    except ImportError as e:
        print(f"❌ 依赖包缺失: {e}")
        print("程序立即停止，请安装必要的依赖包")
        sys.exit(1)
    except Exception as e:
        print(f"❌ {json_path.name} 处理失败: {e}")
        print(f"❌ 错误类型: {type(e).__name__}")
        print("程序立即停止，请检查错误原因")
        sys.exit(1)

def main():
    """主函数"""
    print("🚀 开始批量ESG报告预处理...")
    print(f"📁 根目录: {BASE_PATH}")
    print(f"📁 主图片文件夹: {config.main_images_dir}")
    print("⚠️  注意：遇到任何错误将立即停止程序")
    print("=" * 80)
    
    # 检查根目录是否存在
    if not os.path.exists(BASE_PATH):
        print(f"❌ 错误：根目录不存在: {BASE_PATH}")
        print("请修改 BASE_PATH 为正确的目录路径")
        print("程序立即停止")
        sys.exit(1)
    
    # 检查主图片文件夹是否存在
    if config.main_images_dir and not os.path.exists(config.main_images_dir):
        print(f"❌ 错误：主图片文件夹不存在: {config.main_images_dir}")
        print("请检查 main_images_dir 配置")
        print("程序立即停止")
        sys.exit(1)
    
    # 验证配置
    config_errors = config.validate()
    if config_errors:
        print("❌ 配置验证失败:")
        for error in config_errors:
            print(f"   - {error}")
        print("程序立即停止，请修复配置问题")
        sys.exit(1)
    
    print("✅ 配置验证通过")
    if config.main_images_dir:
        print(f"✅ 主图片文件夹存在: {config.main_images_dir}")
    
    # 查找所有JSON文件
    json_files = find_json_files(BASE_PATH)
    
    if not json_files:
        print("❌ 未找到任何JSON文件")
        print("请检查目录路径和文件扩展名")
        print("程序立即停止")
        sys.exit(1)
    
    print(f"📄 找到 {len(json_files)} 个JSON文件")
    print("=" * 80)
    
    # 统计处理结果
    total_files = len(json_files)
    successful_files = 0
    processing_results = []
    
    # 逐个处理JSON文件
    for i, json_file in enumerate(json_files, 1):
        print(f"\n📋 处理进度: {i}/{total_files}")
        print(f"📄 文件: {json_file.name}")
        
        # 处理单个文件
        result = process_single_json(json_file, config)
        processing_results.append(result)
        successful_files += 1
    
    # 显示最终统计结果
    print("\n" + "=" * 80)
    print("📊 批量处理完成！")
    print(f"📄 总文件数: {total_files}")
    print(f"✅ 成功处理: {successful_files}")
    print(f"📈 成功率: {successful_files/total_files*100:.1f}%")
    
    print(f"\n📁 所有输出文件已保存到各自的子文件夹中")
    
    # 保存处理日志
    log_file = Path(BASE_PATH) / "preprocess_batch_log.json"
    try:
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump({
                "batch_info": {
                    "base_path": BASE_PATH,
                    "main_images_dir": config.main_images_dir,
                    "total_files": total_files,
                    "successful_files": successful_files,
                    "failed_files": 0,
                    "success_rate": successful_files/total_files*100
                },
                "processing_results": processing_results
            }, f, ensure_ascii=False, indent=2)
        print(f"📝 处理日志已保存到: {log_file}")
    except Exception as e:
        print(f"⚠️  保存日志失败: {e}")
        print("程序立即停止，请检查文件权限")
        sys.exit(1)

if __name__ == "__main__":
    main() 