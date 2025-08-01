#!/usr/bin/env python3
"""
DeepSeek R1 集成示例

展示如何在实际的标题对齐流程中使用 DeepSeek R1 客户端进行插入位置分析
"""

import sys
import os
sys.path.append('.')

from config import StructureEnhancementConfig
from api_clients import DeepSeekClient, DeepSeekR1Client, create_api_client
from utils import setup_logging


def enhanced_title_alignment_example():
    """增强的标题对齐示例，使用 DeepSeek V3 + R1 双模型"""
    
    logger = setup_logging()
    config = StructureEnhancementConfig()
    
    # 创建两个客户端
    v3_client = DeepSeekClient(config.get_api_config("deepseek"), logger)
    r1_client = DeepSeekR1Client(config.get_api_config("deepseek_r1"), logger)
    
    print("=== 增强的标题对齐流程示例 ===")
    print("DeepSeek V3: 负责标题选择和通用匹配")
    print("DeepSeek R1: 专门负责插入位置分析")
    print()
    
    # 模拟文档内容
    document_content = """
# 环境、社会与公司治理(ESG)报告

## 环境保护

### 碳排放管理
公司严格控制碳排放，制定了详细的减排计划。

### 水资源管理
建立了完善的水资源管理体系，提高用水效率。

## 社会责任

### 员工权益
保障员工合法权益，提供良好的工作环境。

### 社区发展
积极参与社区建设，承担社会责任。

## 公司治理

### 董事会治理
建立了独立、高效的董事会治理结构。

### 风险管理
完善的风险识别、评估和控制体系。
"""
    
    # 待匹配的标题列表
    unmatched_titles = [
        "能源管理",
        "绿色供应链",
        "生物多样性保护",
        "供应商管理",
        "投资者关系"
    ]
    
    print("=== 双模型协作流程 ===")
    
    for title in unmatched_titles:
        print(f"\n--- 处理标题: {title} ---")
        
        # 步骤1: 使用 DeepSeek V3 进行候选匹配（如果有候选的话）
        # 这里简化为直接使用 R1 进行插入位置分析
        
        # 步骤2: 使用 DeepSeek R1 进行专业的插入位置分析
        try:
            print("🔍 DeepSeek R1 分析插入位置...")
            position = r1_client.find_insert_position(
                document_content, 
                title,
                max_content_length=3000  # 限制内容长度
            )
            
            if position:
                lines = document_content.split('\n')
                print(f"✅ R1 建议插入位置: 第 {position} 行之前")
                
                # 显示插入位置上下文
                if position <= len(lines):
                    print("   上下文:")
                    start_idx = max(0, position - 2)
                    end_idx = min(len(lines), position + 2)
                    for i in range(start_idx, end_idx):
                        marker = ">>> " if i == position - 1 else "    "
                        line_content = lines[i] if i < len(lines) else "(文档末尾)"
                        print(f"{marker}第{i+1}行: {line_content}")
                
                # 步骤3: 使用 R1 进行详细的上下文分析
                print("\n🧠 DeepSeek R1 上下文分析...")
                analysis = r1_client.analyze_title_context(
                    document_content[:2000],  # 限制分析内容长度
                    title
                )
                
                if "error" not in analysis:
                    print("✅ 上下文分析结果:")
                    if isinstance(analysis, dict):
                        for key, value in analysis.items():
                            print(f"   {key}: {value}")
                    else:
                        print(f"   分析结果: {analysis}")
                else:
                    print(f"❌ 上下文分析失败: {analysis.get('error', '未知错误')}")
                    
            else:
                print("❌ R1 判断该标题不适合插入到当前文档中")
                
        except Exception as e:
            print(f"❌ 处理失败: {e}")
    
    print("\n=== 模型对比总结 ===")
    print("DeepSeek V3 优势:")
    print("  - 通用性强，适合多种匹配场景")
    print("  - 支持标题选择功能")
    print("  - 基础插入位置分析")
    
    print("\nDeepSeek R1 优势:")
    print("  - 专门优化的插入位置分析")
    print("  - 更详细的上下文关系分析")
    print("  - 更准确的位置判断")
    print("  - 支持复杂的语义理解")


def fallback_strategy_example():
    """降级策略示例：R1 失败时使用 V3 作为备选"""
    
    logger = setup_logging()
    config = StructureEnhancementConfig()
    
    print("\n=== 降级策略示例 ===")
    print("主要使用 DeepSeek R1，失败时降级到 DeepSeek V3")
    
    # 创建两个客户端
    v3_client = DeepSeekClient(config.get_api_config("deepseek"), logger)
    r1_client = DeepSeekR1Client(config.get_api_config("deepseek_r1"), logger)
    
    test_content = "这是一个测试文档内容..."
    test_title = "测试标题"
    
    def find_insert_position_with_fallback(content, title):
        """带降级策略的插入位置分析"""
        
        # 首先尝试使用 DeepSeek R1
        try:
            print("🚀 尝试使用 DeepSeek R1...")
            position = r1_client.find_insert_position(content, title)
            if position:
                print(f"✅ R1 成功: 位置 {position}")
                return position, "deepseek_r1"
        except Exception as e:
            print(f"⚠️ R1 失败: {e}")
        
        # 降级到 DeepSeek V3
        try:
            print("🔄 降级到 DeepSeek V3...")
            position = v3_client.find_insert_position(content, title)
            if position:
                print(f"✅ V3 成功: 位置 {position}")
                return position, "deepseek_v3"
        except Exception as e:
            print(f"❌ V3 也失败: {e}")
        
        print("❌ 所有方法都失败")
        return None, "failed"
    
    # 测试降级策略
    position, method = find_insert_position_with_fallback(test_content, test_title)
    print(f"\n最终结果: 位置={position}, 方法={method}")


def configuration_example():
    """配置示例：如何在配置中启用/禁用不同的模型"""
    
    print("\n=== 配置示例 ===")
    
    # 创建配置并展示 API 设置
    config = StructureEnhancementConfig()
    
    print("当前 API 配置:")
    for api_type in ["deepseek", "deepseek_r1", "qwen"]:
        api_config = config.get_api_config(api_type)
        print(f"\n{api_type.upper()} 配置:")
        for key, value in api_config.items():
            if "key" in key:
                print(f"  {key}: {str(value)[:10]}...")
            else:
                print(f"  {key}: {value}")
    
    # 展示如何在消融实验中禁用某些功能
    print("\n=== 消融实验配置 ===")
    
    # 创建一个禁用 LLM 匹配的配置
    no_llm_config = config.copy()
    no_llm_config.apply_ablation("no_llm_matching")
    
    print("禁用 LLM 匹配后:")
    print(f"  use_llm_matching: {no_llm_config.use_llm_matching}")
    print(f"  experiment_name: {no_llm_config.experiment_name}")
    
    # 可以基于配置决定是否使用 R1
    if no_llm_config.use_llm_matching:
        print("✅ 可以使用 DeepSeek R1")
    else:
        print("❌ 跳过 DeepSeek R1，使用传统方法")


if __name__ == "__main__":
    print("🚀 DeepSeek R1 集成示例")
    print("=" * 50)
    
    try:
        # 增强的标题对齐示例
        enhanced_title_alignment_example()
        
        # 降级策略示例
        fallback_strategy_example()
        
        # 配置示例
        configuration_example()
        
        print("\n✅ 所有示例完成！")
        print("\n💡 使用建议:")
        print("1. 优先使用 DeepSeek R1 进行插入位置分析")
        print("2. 保留 DeepSeek V3 作为备选方案")
        print("3. 根据实际需求调整配置参数")
        print("4. 在消融实验中测试不同组合的效果")
        
    except Exception as e:
        print(f"\n❌ 示例运行失败: {e}")
        import traceback
        traceback.print_exc() 