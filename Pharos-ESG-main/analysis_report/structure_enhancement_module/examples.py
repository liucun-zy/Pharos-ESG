"""
结构增强模块使用示例

展示各种使用场景：
- 基础使用
- 模块化使用
- 批量处理
- 消融实验
"""

import os
import sys
from pathlib import Path

# 添加模块路径
sys.path.append(str(Path(__file__).parent.parent))

from structure_enhancement_module import (
    StructureEnhancementConfig,
    StructureEnhancementPipeline,
    BatchStructureEnhancementPipeline,
    TitleExtractor,
    PageGrouper,
    TitleAligner,
    AblationExperimentRunner,
    quick_structure_enhancement
)


def example_basic_usage():
    """示例1: 基础使用 - 快速处理单个文件"""
    print("=" * 50)
    print("示例1: 基础使用")
    print("=" * 50)
    
    # 使用快速接口
    result = quick_structure_enhancement(
        input_md_path="example_input.md",
        titles_json_path="example_titles.json",
        output_dir="output/basic_example"
    )
    
    print(f"处理结果: {result['success']}")
    if result['success']:
        print(f"输出目录: {result['output_dir']}")
        print(f"处理统计: {result['stats']['summary']}")


def example_modular_usage():
    """示例2: 模块化使用 - 独立使用各个处理器"""
    print("=" * 50)
    print("示例2: 模块化使用")
    print("=" * 50)
    
    # 创建配置
    config = StructureEnhancementConfig()
    config.title_similarity_threshold = 0.85
    config.use_llm_matching = True
    config.log_level = "DEBUG"
    
    # 独立使用标题提取器
    print("1. 标题提取")
    extractor = TitleExtractor(config)
    extraction_result = extractor.process(
        image_path="toc_page.jpg",
        output_json_path="extracted_titles.json"
    )
    print(f"标题提取结果: {extraction_result['success']}")
    
    # 独立使用页面分组器
    print("2. 页面分组")
    grouper = PageGrouper(config)
    grouping_result = grouper.process(
        input_md_path="input.md",
        output_md_path="grouped.md"
    )
    print(f"页面分组结果: {grouping_result['success']}")
    
    # 独立使用标题对齐器
    print("3. 标题对齐")
    aligner = TitleAligner(config)
    alignment_result = aligner.process(
        md_content=grouping_result["output_content"],
        titles_json_path="extracted_titles.json",
        output_md_path="aligned.md"
    )
    print(f"标题对齐结果: {alignment_result['success']}")


def example_pipeline_usage():
    """示例3: 管道使用 - 完整的处理流程"""
    print("=" * 50)
    print("示例3: 管道使用")
    print("=" * 50)
    
    # 创建自定义配置
    config = StructureEnhancementConfig(
        experiment_name="custom_pipeline",
        title_similarity_threshold=0.8,
        fuzzy_match_enabled=True,
        use_llm_matching=True,
        auto_insert_missing_titles=True,
        log_level="INFO"
    )
    
    # 创建处理管道
    pipeline = StructureEnhancementPipeline(config)
    
    # 运行完整流程
    result = pipeline.run(
        input_md_path="example_input.md",
        titles_json_path="example_titles.json",  # 或者提供 toc_image_path 来提取
        output_dir="output/pipeline_example"
    )
    
    print(f"管道处理结果: {result['success']}")
    if result['success']:
        print(f"实验名称: {result['experiment_name']}")
        print(f"各阶段结果:")
        for stage, stage_result in result['results'].items():
            print(f"  - {stage}: {stage_result['success']}")


def example_batch_processing():
    """示例4: 批量处理 - 处理多个文件"""
    print("=" * 50)
    print("示例4: 批量处理")
    print("=" * 50)
    
    # 创建配置
    config = StructureEnhancementConfig(
        experiment_name="batch_processing",
        title_similarity_threshold=0.8,
        use_llm_matching=True
    )
    
    # 批量处理文件列表
    input_files = [
        "report1.md",
        "report2.md", 
        "report3.md"
    ]
    
    # 创建批量处理管道
    batch_pipeline = BatchStructureEnhancementPipeline(config)
    
    # 运行批量处理
    batch_result = batch_pipeline.run_batch(
        input_files=input_files,
        output_base_dir="output/batch_processing",
        max_workers=2  # 并发处理数
    )
    
    print(f"批量处理结果: {batch_result['success']}")
    if 'batch_report' in batch_result:
        report = batch_result['batch_report']
        print(f"成功处理: {report['summary']['successful_files']}/{report['summary']['total_files']}")
        print(f"总体成功率: {report['summary']['success_rate']:.2%}")
        
        if batch_result['failed_files']:
            print(f"失败文件: {batch_result['failed_files']}")


def example_ablation_experiments():
    """示例5: 消融实验 - 评估算法组件效果"""
    print("=" * 50)
    print("示例5: 消融实验")
    print("=" * 50)
    
    # 创建基础配置
    base_config = StructureEnhancementConfig(
        title_similarity_threshold=0.8,
        fuzzy_match_enabled=True,
        use_llm_matching=True,
        auto_insert_missing_titles=True
    )
    
    # 定义要运行的消融实验
    experiments = [
        "no_llm_matching",      # 禁用LLM匹配
        "no_fuzzy_match",       # 禁用模糊匹配
        "strict_matching",      # 严格匹配模式
        "high_similarity",      # 高相似度阈值
        "low_similarity"        # 低相似度阈值
    ]
    
    # 测试文件列表
    test_files = [
        "test_report1.md",
        "test_report2.md"
    ]
    
    # 创建消融实验运行器
    runner = AblationExperimentRunner(base_config, experiments)
    
    # 运行消融实验
    experiment_results = runner.run_experiments(
        input_files=test_files,
        output_base_dir="output/ablation_experiments"
    )
    
    print("消融实验完成!")
    print("实验结果:")
    
    for exp_name, result in experiment_results.items():
        if result.get('success') and 'batch_report' in result:
            success_rate = result['batch_report']['summary']['success_rate']
            print(f"  - {exp_name}: 成功率 {success_rate:.2%}")
        else:
            print(f"  - {exp_name}: 失败")


def example_custom_config():
    """示例6: 自定义配置 - 高级配置选项"""
    print("=" * 50)
    print("示例6: 自定义配置")
    print("=" * 50)
    
    # 创建高度自定义的配置
    config = StructureEnhancementConfig(
        # 基础配置
        experiment_name="custom_advanced",
        base_dir="/path/to/base",
        output_dir="/path/to/output",
        
        # 日志配置
        log_level="DEBUG",
        log_to_file=True,
        log_file_path="custom_debug.log",
        
        # API配置
        deepseek_api_key="your_deepseek_key",
        qwen_api_key="your_qwen_key",
        api_timeout=120,
        max_retries=5,
        
        # 标题匹配参数
        title_similarity_threshold=0.85,
        fuzzy_match_enabled=True,
        use_llm_matching=True,
        auto_insert_missing_titles=True,
        insert_confidence_threshold=0.75,
        
        # 图像处理参数
        max_image_size_mb=2.0,
        image_quality_reduction=10,
        extract_max_tokens=4096,
        extract_temperature=0.1,
        
        # 结构控制参数
        max_title_levels=5,
        default_title_level=2,
        auto_adjust_levels=True,
        preserve_original_structure=False
    )
    
    # 显示配置摘要
    print("自定义配置:")
    print(f"  实验名称: {config.experiment_name}")
    print(f"  相似度阈值: {config.title_similarity_threshold}")
    print(f"  启用LLM匹配: {config.use_llm_matching}")
    print(f"  最大标题层级: {config.max_title_levels}")
    print(f"  图片最大尺寸: {config.max_image_size_mb}MB")
    
    # 应用消融实验配置
    print("\n应用消融实验配置:")
    config.apply_ablation("strict_matching")
    print(f"  严格匹配模式 - 相似度阈值: {config.title_similarity_threshold}")
    
    config.apply_ablation("no_llm_matching")
    print(f"  禁用LLM匹配 - LLM匹配: {config.use_llm_matching}")


def example_error_handling():
    """示例7: 错误处理 - 展示错误处理机制"""
    print("=" * 50)
    print("示例7: 错误处理")
    print("=" * 50)
    
    config = StructureEnhancementConfig()
    pipeline = StructureEnhancementPipeline(config)
    
    # 尝试处理不存在的文件
    print("1. 处理不存在的文件:")
    result = pipeline.run(
        input_md_path="nonexistent_file.md",
        titles_json_path="nonexistent_titles.json",
        output_dir="output/error_test"
    )
    
    print(f"处理结果: {result['success']}")
    if not result['success']:
        print(f"错误信息: {result['error']}")
    
    # 展示降级策略
    print("\n2. API失败降级策略:")
    config_no_api = StructureEnhancementConfig()
    config_no_api.deepseek_api_key = "invalid_key"  # 无效API密钥
    config_no_api.use_llm_matching = True
    
    pipeline_no_api = StructureEnhancementPipeline(config_no_api)
    # 这里会触发API失败，然后降级到规则匹配
    print("配置了无效API密钥，将自动降级到规则匹配")


def main():
    """运行所有示例"""
    print("🚀 结构增强模块使用示例")
    print("=" * 60)
    
    examples = [
        ("基础使用", example_basic_usage),
        ("模块化使用", example_modular_usage),
        ("管道使用", example_pipeline_usage),
        ("批量处理", example_batch_processing),
        ("消融实验", example_ablation_experiments),
        ("自定义配置", example_custom_config),
        ("错误处理", example_error_handling)
    ]
    
    print("可用示例:")
    for i, (name, _) in enumerate(examples, 1):
        print(f"  {i}. {name}")
    
    print("\n选择要运行的示例 (1-7, 或 'all' 运行所有示例):")
    choice = input().strip().lower()
    
    if choice == 'all':
        for name, func in examples:
            print(f"\n运行示例: {name}")
            try:
                func()
            except Exception as e:
                print(f"示例运行失败: {e}")
    elif choice.isdigit() and 1 <= int(choice) <= len(examples):
        name, func = examples[int(choice) - 1]
        print(f"\n运行示例: {name}")
        try:
            func()
        except Exception as e:
            print(f"示例运行失败: {e}")
    else:
        print("无效选择")


if __name__ == "__main__":
    main() 