#!/usr/bin/env python3
"""
DeepSeek R1 客户端使用示例

展示如何使用新的 DeepSeek R1 API 客户端进行标题插入位置分析
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import StructureEnhancementConfig
from api_clients import DeepSeekR1Client, create_api_client
from utils import setup_logging


def test_deepseek_r1_client():
    """测试 DeepSeek R1 客户端功能"""
    
    # 设置日志
    logger = setup_logging()
    
    # 创建配置
    config = StructureEnhancementConfig()
    
    # 获取 DeepSeek R1 API 配置
    r1_config = config.get_api_config("deepseek_r1")
    
    print("=== DeepSeek R1 客户端测试 ===")
    print(f"API URL: {r1_config['api_url']}")
    print(f"模型: {r1_config['model']}")
    print(f"API Key: {r1_config['api_key'][:10]}...")
    
    # 创建客户端
    r1_client = DeepSeekR1Client(r1_config, logger)
    
    # 测试文档内容
    test_content = """
# 环境保护与可持续发展

## 环境管理体系

公司建立了完善的环境管理体系，严格遵循ISO 14001标准。

### 环境政策

我们承诺在所有业务活动中最大程度地减少对环境的影响。

## 碳排放管理

### 碳排放现状

2024年公司总碳排放量为15,000吨CO2当量。

### 减排目标

计划到2030年实现碳中和目标。

## 资源管理

### 水资源管理

公司实施严格的水资源管理制度。

### 废物管理

建立了完善的废物分类和处理体系。

# 社会责任

## 员工权益保护

### 员工培训

公司每年投入大量资源进行员工培训。

### 职业健康安全

建立了完善的职业健康安全管理体系。
"""
    
    # 测试标题列表
    test_titles = [
        "能源管理",
        "绿色采购",
        "生物多样性保护",
        "供应链管理",
        "社区发展"
    ]
    
    print("\n=== 标题插入位置分析测试 ===")
    
    for title in test_titles:
        print(f"\n--- 分析标题: {title} ---")
        
        try:
            # 分析插入位置
            position = r1_client.find_insert_position(test_content, title)
            
            if position:
                lines = test_content.split('\n')
                print(f"✅ 建议插入位置: 第 {position} 行之前")
                if position <= len(lines):
                    print(f"   插入位置上下文:")
                    start_idx = max(0, position - 3)
                    end_idx = min(len(lines), position + 2)
                    for i in range(start_idx, end_idx):
                        marker = ">>> " if i == position - 1 else "    "
                        print(f"{marker}第{i+1}行: {lines[i]}")
                else:
                    print("   插入到文档末尾")
            else:
                print("❌ 不适合插入或分析失败")
                
        except Exception as e:
            print(f"❌ 分析失败: {e}")
    
    print("\n=== 上下文关系分析测试 ===")
    
    # 测试上下文分析功能
    test_title = "能源管理"
    print(f"\n--- 分析标题 '{test_title}' 的上下文关系 ---")
    
    try:
        analysis = r1_client.analyze_title_context(test_content, test_title)
        
        if "error" in analysis:
            print(f"❌ 分析失败: {analysis['error']}")
        else:
            print("✅ 上下文分析结果:")
            for key, value in analysis.items():
                print(f"   {key}: {value}")
                
    except Exception as e:
        print(f"❌ 上下文分析失败: {e}")


def test_api_client_factory():
    """测试 API 客户端工厂函数"""
    
    print("\n=== API 客户端工厂测试 ===")
    
    # 创建配置
    config = StructureEnhancementConfig()
    logger = setup_logging()
    
    # 测试创建不同类型的客户端
    api_types = ["deepseek", "deepseek_r1", "qwen"]
    
    for api_type in api_types:
        try:
            api_config = config.get_api_config(api_type)
            client = create_api_client(api_type, api_config, logger)
            print(f"✅ 成功创建 {api_type} 客户端: {type(client).__name__}")
        except Exception as e:
            print(f"❌ 创建 {api_type} 客户端失败: {e}")


def compare_deepseek_clients():
    """比较 DeepSeek V3 和 DeepSeek R1 客户端的差异"""
    
    print("\n=== DeepSeek V3 vs R1 客户端比较 ===")
    
    config = StructureEnhancementConfig()
    logger = setup_logging()
    
    # 创建两个客户端
    v3_config = config.get_api_config("deepseek")
    r1_config = config.get_api_config("deepseek_r1")
    
    from api_clients import DeepSeekClient
    v3_client = DeepSeekClient(v3_config, logger)
    r1_client = DeepSeekR1Client(r1_config, logger)
    
    print("DeepSeek V3 客户端:")
    print(f"  - 模型: {v3_client.model}")
    print(f"  - API URL: {v3_client.api_url}")
    print(f"  - 主要功能: 标题选择、通用插入位置分析")
    
    print("\nDeepSeek R1 客户端:")
    print(f"  - 模型: {r1_client.model}")
    print(f"  - API URL: {r1_client.api_url}")
    print(f"  - 主要功能: 专门的插入位置分析、上下文关系分析")
    
    print("\n功能对比:")
    print("  - V3: 支持标题选择 + 基础插入位置分析")
    print("  - R1: 专门优化的插入位置分析 + 详细上下文分析")
    print("  - 设计理念: V3通用性，R1专业性")


if __name__ == "__main__":
    print("🚀 DeepSeek R1 客户端功能测试")
    print("=" * 50)
    
    try:
        # 测试 DeepSeek R1 客户端
        test_deepseek_r1_client()
        
        # 测试 API 客户端工厂
        test_api_client_factory()
        
        # 比较两个 DeepSeek 客户端
        compare_deepseek_clients()
        
        print("\n✅ 所有测试完成！")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc() 