"""
预处理模块使用示例

展示如何使用模块化的预处理系统进行：
1. 基础预处理
2. 自定义配置
3. 消融实验
4. 批量处理
"""

import os
from pathlib import Path

# 导入预处理模块
from preprocess_module import (
    PreprocessConfig, 
    PreprocessPipeline,
    BatchPreprocessPipeline,
    AblationExperimentRunner,
    ConfigManager,
    get_production_config,
    get_debug_config,
    quick_preprocess
)


def example_basic_usage():
    """示例1: 基础使用"""
    print("=== 示例1: 基础使用 ===")
    
    # 配置路径
    input_json = "/Users/liucun/Desktop/report_analysis/300497.SZ-富祥药业-2024年度环境、社会及公司治理(ESG)报告/300497.SZ-富祥药业-2024年度环境、社会及公司治理(ESG)报告.json"
    output_dir = "/Users/liucun/Desktop/report_analysis/output/basic_example"
    
    # 使用快速接口
    try:
        result = quick_preprocess(input_json, output_dir)
        print(f"处理完成: {result['summary']}")
    except Exception as e:
        print(f"处理失败: {e}")


def example_custom_config():
    """示例2: 自定义配置"""
    print("\n=== 示例2: 自定义配置 ===")
    
    # 创建自定义配置
    config = PreprocessConfig(
        json_to_md_enabled=True,
        image_link_conversion_enabled=True,
        text_detection_enabled=True,
        confidence_threshold=50.0,  # 提高置信度阈值
        min_text_length=5,          # 提高最小文本长度
        log_level="DEBUG",          # 详细日志
        experiment_name="high_precision"
    )
    
    # 配置路径
    input_json = "/Users/liucun/Desktop/report_analysis/300497.SZ-富祥药业-2024年度环境、社会及公司治理(ESG)报告/300497.SZ-富祥药业-2024年度环境、社会及公司治理(ESG)报告.json"
    output_dir = "/Users/liucun/Desktop/report_analysis/output/custom_config"
    
    # 运行处理
    pipeline = PreprocessPipeline(config)
    try:
        result = pipeline.run(input_json, output_dir)
        print(f"自定义配置处理完成")
        print(f"处理统计: {result['total_statistics']}")
    except Exception as e:
        print(f"处理失败: {e}")


def example_ablation_experiments():
    """示例3: 消融实验"""
    print("\n=== 示例3: 消融实验 ===")
    
    # 基础配置
    base_config = get_production_config(
        base_dir="/Users/liucun/Desktop/report_analysis",
        output_dir="/Users/liucun/Desktop/report_analysis/output/ablation"
    )
    
    # 定义要测试的消融配置
    experiment_configs = [
        "no_text_detection",
        "no_image_validation",
        "minimal_processing",
        "high_confidence",
        "low_confidence"
    ]
    
    # 运行消融实验
    input_json = "/Users/liucun/Desktop/report_analysis/300497.SZ-富祥药业-2024年度环境、社会及公司治理(ESG)报告/300497.SZ-富祥药业-2024年度环境、社会及公司治理(ESG)报告.json"
    output_dir = "/Users/liucun/Desktop/report_analysis/output/ablation_experiments"
    
    runner = AblationExperimentRunner(base_config, experiment_configs)
    try:
        results = runner.run_experiments(input_json, output_dir)
        print(f"消融实验完成: {results['successful_experiments']}/{results['total_experiments']} 成功")
    except Exception as e:
        print(f"消融实验失败: {e}")


def example_batch_processing():
    """示例4: 批量处理"""
    print("\n=== 示例4: 批量处理 ===")
    
    # 配置
    config = get_production_config(
        base_dir="/Users/liucun/Desktop/report_analysis",
        output_dir="/Users/liucun/Desktop/report_analysis/output/batch"
    )
    
    # 假设有多个JSON文件需要处理
    input_files = [
        "/Users/liucun/Desktop/report_analysis/300497.SZ-富祥药业-2024年度环境、社会及公司治理(ESG)报告/300497.SZ-富祥药业-2024年度环境、社会及公司治理(ESG)报告.json",
        # 可以添加更多文件...
    ]
    
    output_dir = "/Users/liucun/Desktop/report_analysis/output/batch_processing"
    
    # 运行批量处理
    batch_pipeline = BatchPreprocessPipeline(config)
    try:
        results = batch_pipeline.run_batch(input_files, output_dir)
        print(f"批量处理完成: {results['successful_files']}/{results['total_files']} 成功")
    except Exception as e:
        print(f"批量处理失败: {e}")


def example_config_management():
    """示例5: 配置管理"""
    print("\n=== 示例5: 配置管理 ===")
    
    # 创建配置管理器
    config_dir = "/Users/liucun/Desktop/report_analysis/configs"
    manager = ConfigManager(config_dir)
    
    # 创建并保存不同的配置
    production_config = get_production_config(
        base_dir="/Users/liucun/Desktop/report_analysis",
        output_dir="/Users/liucun/Desktop/report_analysis/output"
    )
    manager.save_config(production_config, "production")
    
    debug_config = get_debug_config(
        base_dir="/Users/liucun/Desktop/report_analysis",
        output_dir="/Users/liucun/Desktop/report_analysis/output"
    )
    manager.save_config(debug_config, "debug")
    
    # 创建消融实验配置
    ablation_configs = manager.create_ablation_configs()
    print(f"创建了 {len(ablation_configs)} 个消融实验配置")
    
    # 列出所有配置
    all_configs = manager.list_configs()
    print(f"可用配置: {all_configs}")
    
    # 加载并使用配置
    loaded_config = manager.load_config("production")
    print(f"加载配置: {loaded_config.experiment_name}")


def example_single_step_processing():
    """示例6: 单步骤处理（调试用）"""
    print("\n=== 示例6: 单步骤处理 ===")
    
    config = get_debug_config(
        base_dir="/Users/liucun/Desktop/report_analysis",
        output_dir="/Users/liucun/Desktop/report_analysis/output/debug"
    )
    
    pipeline = PreprocessPipeline(config)
    
    # 只运行JSON转Markdown步骤
    try:
        result = pipeline.run_single_step(
            'json_to_md',
            input_json_path="/Users/liucun/Desktop/report_analysis/300497.SZ-富祥药业-2024年度环境、社会及公司治理(ESG)报告/300497.SZ-富祥药业-2024年度环境、社会及公司治理(ESG)报告.json",
            output_md_path="/Users/liucun/Desktop/report_analysis/output/debug/test.md"
        )
        print(f"单步骤处理完成: {result['status']}")
    except Exception as e:
        print(f"单步骤处理失败: {e}")


def example_error_handling():
    """示例7: 错误处理和恢复"""
    print("\n=== 示例7: 错误处理 ===")
    
    # 创建一个可能失败的配置（错误的Tesseract路径）
    config = PreprocessConfig(
        tesseract_path="/invalid/path/to/tesseract",  # 错误路径
        text_detection_enabled=True,
        log_level="DEBUG"
    )
    
    # 验证配置
    errors = config.validate()
    if errors:
        print(f"配置验证失败: {errors}")
        
        # 修复配置
        config.tesseract_path = "/opt/homebrew/bin/tesseract"
        print("已修复配置")
    
    # 现在可以正常运行
    pipeline = PreprocessPipeline(config)
    print("管道初始化成功")


if __name__ == "__main__":
    print("预处理模块使用示例")
    print("=" * 50)
    
    # 运行所有示例
    example_basic_usage()
    example_custom_config()
    example_config_management()
    example_single_step_processing()
    example_error_handling()
    
    # 注意：以下示例需要较长时间，可以单独运行
    # example_ablation_experiments()
    # example_batch_processing()
    
    print("\n" + "=" * 50)
    print("所有示例完成！")
    print("\n使用提示:")
    print("1. 修改路径以匹配您的实际文件位置")
    print("2. 根据需要调整配置参数")
    print("3. 查看生成的报告文件了解详细结果")
    print("4. 使用配置管理器保存和重用配置")
    print("5. 利用消融实验功能优化处理参数") 