import requests
import base64
import logging
import json
import time
import os
import sys
from tenacity import retry, stop_after_attempt, wait_exponential
from PIL import Image
import io
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

API_KEY = ""
API_URL = "https://api.siliconflow.cn/v1/chat/completions"
MODEL_NAME = ""

def compress_image(image_path: str, max_size_mb: float = 1.0, quality_reduction: int = 5) -> bytes:
    """
    压缩图片到指定大小以下
    Args:
        image_path: 图片路径
        max_size_mb: 最大文件大小（MB）
        quality_reduction: 每次压缩的质量减少百分比
    Returns:
        bytes: 压缩后的图片数据
    """
    max_size_bytes = max_size_mb * 1024 * 1024
    
    # 打开图片
    with Image.open(image_path) as img:
        # 转换为RGB模式（如果是RGBA）
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        
        # 初始质量
        quality = 95
        output = io.BytesIO()
        
        # 压缩循环
        while True:
            output.seek(0)
            output.truncate()
            img.save(output, format='JPEG', quality=quality)
            size = output.tell()
            
            if size <= max_size_bytes or quality <= 5:
                break
                
            quality -= quality_reduction
        
        return output.getvalue()

def call_vlm_api_with_retry(messages, max_retries=4, quality_reduction=5, **kwargs):
    """
    带重试机制的VLM API调用，支持413错误时压缩图片
    Args:
        messages: API消息
        max_retries: 最大重试次数
        quality_reduction: 每次压缩的质量减少百分比
        **kwargs: 其他API参数
    """
    retry_count = 0
    last_error = None
    
    while retry_count < max_retries:
        try:
            headers = {
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": MODEL_NAME,
                "messages": messages,
                "max_tokens": 2048,
                "temperature": 0.0,
                "top_p": 1.0,
                "n": 1
            }
            # 只允许动态改动已存在的key
            for k, v in kwargs.items():
                if k in payload:
                    payload[k] = v

            response = requests.post(API_URL, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            last_error = e
            if e.response.status_code == 413:  # Request Entity Too Large
                retry_count += 1
                if retry_count >= max_retries:
                    logging.error(f"图片压缩{max_retries}次后仍然太大，放弃处理")
                    raise last_error
                    
                logging.warning(f"图片太大，正在进行第{retry_count}次压缩尝试（质量减少{quality_reduction}%）")
                
                # 遍历所有消息内容，找到需要压缩的图片
                for message in messages:
                    if "content" in message and isinstance(message["content"], list):
                        for content_item in message["content"]:
                            if isinstance(content_item, dict) and content_item.get("type") == "image_url":
                                image_url = content_item["image_url"]["url"]
                                if image_url.startswith("data:image/jpeg;base64,"):
                                    try:
                                        # 从base64中提取图片数据
                                        img_data = base64.b64decode(image_url.split(",")[1])
                                        # 保存为临时文件
                                        temp_path = "temp_image.jpg"
                                        with open(temp_path, "wb") as f:
                                            f.write(img_data)
                                        try:
                                            # 压缩图片，每次减少quality_reduction的质量
                                            compressed_image = compress_image(temp_path, quality_reduction=quality_reduction)
                                            # 更新messages中的图片
                                            content_item["image_url"]["url"] = f"data:image/jpeg;base64,{base64.b64encode(compressed_image).decode('utf-8')}"
                                        finally:
                                            # 清理临时文件
                                            if os.path.exists(temp_path):
                                                os.remove(temp_path)
                                    except Exception as e:
                                        logging.error(f"压缩图片时出错: {str(e)}")
                                        raise
                
                # 继续重试
                continue
            else:
                # 其他HTTP错误直接抛出
                raise
                
        except Exception as e:
            # 其他异常直接抛出
            raise
    
    # 如果所有重试都失败
    raise last_error

def extract_titles_from_image(image_path: str) -> str:
    """
    从图片文件中提取标题结构，保存为JSON文件
    Args:
        image_path: 图片文件路径
    Returns:
        str: 保存的JSON文件路径
    """
    try:
        # 确保输入路径是绝对路径
        image_path = os.path.abspath(image_path)
        
        # 确保图片路径存在
        if not os.path.exists(image_path):
            raise Exception(f"图片文件不存在: {image_path}")
        
        # 读取原始图片并转base64
        with open(image_path, "rb") as img_file:
            img_b64 = base64.b64encode(img_file.read()).decode("utf-8")
            
        # --- 读取示例图片的 Base64 编码 ---
        # 获取当前脚本所在目录
        script_dir = os.path.dirname(os.path.abspath(__file__))
        example1_base64_path = os.path.join(script_dir, "sample2base64.txt")
        example2_base64_path = os.path.join(script_dir, "sample1base64.txt")
        
        example1_base64 = ""
        example2_base64 = ""
        
        if os.path.exists(example1_base64_path):
            with open(example1_base64_path, 'r') as f:
                example1_base64 = f.read().strip()
        else:
            logging.warning(f"示例图片 Base64 文件不存在: {example1_base64_path}")
            
        if os.path.exists(example2_base64_path):
            with open(example2_base64_path, 'r') as f:
                example2_base64 = f.read().strip()
        else:
            logging.warning(f"示例图片 Base64 文件不存在: {example2_base64_path}")
        
        # --- 构造多模态 messages ---
        # 将提示词分割成多个文本块，并在中间插入图片
        prompt_text_part1 = """
你是一位文档目录抽取助手，请从最后一张图片中识别目录标题并按层级输出。

**禁止** 在最终答案中出现任何推理过程、解释、注释、Markdown 标题符号 (#) 或 "阶段一 / 阶段二" 等文字；**只输出最终的标题结构列表**。
⚠️ 在生成最终答案之前，**必须依序执行并完成下面 7 大规则的推理与判断**并输出你对每一条规则判断的推理思路（每一条规则的推理思路输出要在100-200字之间）；其次输出是否找到篇标签X，若未找到则输出最终结果，若找到，则说明可替换的Y和Z，并说明替换理由，完成以上输出后再输出最终结果。

───────────────────
识别与筛选规则
───────────────────
1. **候选提取**  
   - 首先完整提取图片中所有可能的目录标题，忽略页码、行号、空心点、虚线、CONTENTS/目录,上篇，下篇等说明性词。


2. **篇标签智能处理**

    步骤 1　识别候选篇标签  
     - 长度 ≤ 3 且**必须**以 "篇 / 章 / 部" 结尾的行才视为候选标签 X（词干 X′ = 去后缀）。
     【示例】候选标题提取中初步归为一级标题的行文本 **完全等于** "治理篇" / "社会篇" / "环境篇" 时，视为篇标签 X  
    - ⚠️无关词："上篇""下篇"，只要出现"上篇""下篇"，则与其同行的标题直接删除掉，禁止出现在最终输出中
    步骤 2　在视觉邻域内寻找替代标题 Y  
        - 视觉邻域 =  
            • 与 X 同列向下连续 10 行；或  
            • 同一水平行向右 40% 页面宽度内出现的行。  
         - Y 必须满足：  
            • 视觉上为一级标题，不考虑字体相对小的标题  
            • 文本长度 ≥ 3；  
            • **模糊匹配条件（满足任一即可）**  
                 ① X′ 与 Y 至少共享 2 个汉字； （不要求连续）；  
                 ② 中文 Jaccard 相似度 ≥ 0.5；  
                 ③ 编辑距离 ÷ max(len) ≤ 0.5。  

    步骤 3　替换  
        - 若找到符合条件的 Y：**删除 X**，仅保留 Y 作为一级标题  
        （或按需合并为 "X′ + 空格 + Y"，全页一致）。 
        - 若未找到符合条件的 Y：  
            • 在 X 下 3 行内找长度 ≥ 6 的最近行 Z，合并为 "X′ + 空格 + Z"  
            • 合并后 **删除 X 与 Z 原行**。  
        - 合并 / 替换失败则**整行舍弃 X**，不得将其作为一级标题输出。

    步骤 4　去重  
        - 若多个 X 指向同一 Y，只保留第一次出现。

    **输出约束**（  
        - 最终输出中**不得**出现任何长度 ≤ 4 且以 "篇/章/部" 结尾的行，违者视为错误输出。
        - 篇标签只能处理的步骤均要在**存在候选篇标签**时才触发

3. **层级判定优先级**

    A. 独立编号对齐 → 同级一级（不得嵌套）

    B. 无编号并列：依次按【字体大小/粗细 → 颜色 → 位置缩进】判级

    C. 字体相同，颜色不同时，在同一视觉区块内，如果每个标题间距离相同，颜色数量为一的是更高级标题，颜色数量多的均为更低级标题

    D. 颜色字体相似时，观察同一视觉区块内相邻行垂直间距 ΔY。若 ΔY 近似均匀，视为同级；若某行 ΔY 显著大于其下方行 ΔY，则该行视为新父级标题，其下方直到下一个大间距行之前，所有行默认降一级归属该父级。

4.**图块结构判定规则**
    - 若页面中出现 01 / 02 / 03 等阿拉伯数字角标，后跟"××篇"类短标签，再后跟一行长标题，三个组成视觉模块：
        → 将这三行合并为一个完整的一级标题，格式为：
            "××篇 + 空格 + 长标题"
            例如："环境篇 育绿色之苗"
    - 若该模块下存在 4–8 行短句（字体更小、颜色一致），与图块主标题颜色相同或相近：
        → 这些行全部视为该一级标题下的二级标题。
    - 所有图块结构必须优先于左侧纯文字区域判断，不得重复。

5. **同题断行合并**  
   - 若同一逻辑标题被排版断为多行（如 "合规治理" 换行 "护航发展"），在输出时请合并为一句，用空格连接。

6. **二级 / 三级标题识别**（在同一一级标题可见区域内）  
   6.1 字体或颜色 **显著更醒目**（通常更粗/更深色）的行视为 **二级标题**。  
   6.2 紧跟其后的若干行，若字体/颜色 **明显更淡** 或字号更小，且与上一行颜色相同，则全部归属于该二级标题，视为其 **三级标题**。  
   6.3 当再次出现醒目的行时，开始新的二级标题分组。

7. **附录类内容顺序对齐**  
   7.1 识别附录类标题：包含"附录"、"关键绩效表"、"ESG绩效表"、"指标索引"、"ESG指标索引"、"意见反馈"、"读者反馈"等词汇的标题。  
   7.2 顺序验证：这些内容通常属于文章的最后部分，应按照以下人类撰写习惯排序：  
       • 附录 → 关键绩效表/ESG绩效表 → 指标索引/ESG指标索引 → 意见反馈/读者反馈  
   7.3 页码辅助判断：如果目录中包含页码信息，利用页码数字大小来验证和调整附录类内容的排列顺序。  
   7.4 顺序调整：在输出最终结果前，确保附录类内容符合上述顺序逻辑，必要时进行重新排列。

───────────────────
输出格式
───────────────────
### 完成规则推理与判断
请逐条严格执行以下7项规则，输出你对每一条规则判断的推理思路（每一条规则的推理思路输出要在100-200字之间）
### 是否找到X，Y，Z及理由
输出是否找到篇标签X，若未找到则输出最终结果，若找到，则说明可替换的Y和Z，并说明替换理由，
### 最终输出结果
输出格式（用 <INDENT> 表示 4 个空格）
一级标题
<INDENT>二级标题
<INDENT><INDENT>三级标题（若有）
<INDENT>二级标题

要求：实际输出时请把每个 <INDENT> 替换成 4 个 ASCII 空格，且不要保留 "<INDENT>" 字样。

- 一级标题行 **无缩进**；  
- 一级→二级、二级→三级 均缩进 **4 个空格**；  
- 每个标题独占一行；  
- 允许没有二级标题的一级标题；  
- 结果中 **不得出现页码、编号、符号或解释性文字**。

───────────────────
图片示例
───────────────────
"""
        
        prompt_text_part2 = """
规则 C 应用于此示例，遇到与此图片格式相同的按此期望输出格式划分方式进行划分：
期望输出格式:
附录
    ESG绩效表
    ESG指标索引
    意见反馈

"""
        prompt_text_part3 = """
规则 D 应用于此示例，遇到与此图片格式相同的按此期望输出格式划分方式进行划分输出：
观察"关于本报告"到"董事长致辞"、"董事长致辞"到"走进国机重装"的垂直间距。如果这些间距相似，则它们为同级。
观察"助力 SDGs 行动进展"到"责任专题"的垂直间距。如果这个间距显著大于其上行间的间距，则"责任专题"是新的父级标题。
以此类推，根据垂直间距判断层级。
期望输出格式:
关于本报告
董事长致辞
走进国机重装

责任与成长
    关键绩效
    荣誉与认可
    助力 SDGs 行动进展

责任专题
    以创新驱动发展装备制造业新质生产力
    加快构建人才发展雁阵，共赴"大国重器"之约

责任管理
    可持续发展理念与治理
    重要性议题管理
    利益相关方沟通

展望
指标索引
关键绩效表
读者意见反馈

───────────────────
补充说明
───────────────────
- "不要遗漏任何标题" 指去冗余后，仍需保留每个 **独立章节** 的唯一标题；删除与其语义等价、信息量更低的重复条目不算遗漏。
- 在判定层级与去重时，优先比较 **字体大小/粗细、颜色**，再比较视觉距离。
"""

        # 构造多模态 messages，包含文本和图片
        content_list = [
            # 提示词第一部分文本
            {
                "type": "text",
                "text": prompt_text_part1
            }
        ]
        
        # 只有在示例图片存在时才添加
        if example2_base64:
            content_list.extend([
                # 示例图片 1
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{example2_base64}",
                        "detail": "high"
                    }
                },
                # 提示词第二部分文本
                {
                    "type": "text",
                    "text": prompt_text_part2
                }
            ])
        
        if example1_base64:
            content_list.extend([
                # 示例图片 2
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{example1_base64}",
                        "detail": "high"
                    }
                },
                # 提示词第三部分文本
                {
                    "type": "text",
                    "text": prompt_text_part3
                }
            ])
        
        # 添加主要图片（要分析的图片）
        content_list.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{img_b64}",
                "detail": "high"
            }
        })
        
        messages = [{
            "role": "user",
            "content": content_list
        }]
        
        # 调用API（带重试机制）
        result = call_vlm_api_with_retry(messages=messages)
        time.sleep(2)  # 防止频繁请求

        # 解析API返回内容
        content = result["choices"][0]["message"]["content"]
        
        # 解析章节标题为结构化列表
        titles_list = parse_titles_from_text(content)

        # 保存为JSON文件（保存在图片所在的目录）
        output_path = os.path.join(os.path.dirname(image_path), "titles.json")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(titles_list, f, ensure_ascii=False, indent=2)
        print(f"\n=== 标题提取完成 ===")
        print(f"结果已保存到: {output_path}")

        return output_path

    except Exception as e:
        logging.error(f"提取标题时出错: {str(e)}")
        return None

def parse_titles_from_text(content: str):
    """
    解析LLM输出的章节标题文本，返回结构化的列表
    从"### 最终输出结果"之后开始解析
    返回格式：
    [
        {
            "title": "一级标题"
        },
        {
            "title": "一级标题",
            "subtitles": [
                {
                    "title": "二级标题",
                    "subtitles": ["三级标题1", "三级标题2"]
                }
            ]
        }
    ]
    """
    print("\n=== LLM输出结果 ===")
    print(content)
    print("="*30)
    
    # 找到"### 最终输出结果"的位置
    start_marker = "### 最终输出结果"
    start_index = content.find(start_marker)
    
    if start_index == -1:
        logging.error("未找到'### 最终输出结果'标记")
        return []
    
    # 获取标记后的内容
    content = content[start_index + len(start_marker):].strip()
    
    lines = content.splitlines()
    result = []
    current_h1 = None
    current_h2 = None
    
    for line in lines:
        line = line.strip('\r\n')
        if not line.strip():
            continue
            
        # 判断是否为一级标题（无缩进且不以特殊符号开头）
        if not line.startswith('    ') and not line.startswith('-') and not line.startswith('·') and not line.startswith('•'):
            # 如果已经有标题在处理中，保存它
            if current_h1:
                result.append(current_h1)
            # 开始新的一级标题
            current_h1 = {"title": line.strip()}
            current_h2 = None
        # 判断是否为二级标题（缩进4个空格）
        elif line.startswith('    ') and not line.startswith('        '):
            if current_h1:
                # 如果一级标题还没有subtitles字段，创建它
                if "subtitles" not in current_h1:
                    current_h1["subtitles"] = []
                # 开始新的二级标题
                current_h2 = {"title": line.lstrip('    ').strip()}
                current_h1["subtitles"].append(current_h2)
        # 判断是否为三级标题（缩进8个空格）
        elif line.startswith('        '):
            if current_h2:
                # 如果二级标题还没有subtitles字段，创建它
                if "subtitles" not in current_h2:
                    current_h2["subtitles"] = []
                # 添加三级标题
                current_h2["subtitles"].append(line.lstrip('        ').strip())
    
    # 保存最后一个标题
    if current_h1:
        result.append(current_h1)
    
    return result

if __name__ == "__main__":
    # 检查命令行参数
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
    else:
        # 默认处理指定图片路径
        image_path = "/Users/liucun/Desktop/report_analysis/analysis_report/page_2.jpg"
        print(f"使用默认图片路径: {image_path}")
    
    # 检查图片文件是否存在
    if not os.path.exists(image_path):
        print(f"错误: 图片文件不存在: {image_path}")
        print("使用方法: python extract_title.py [图片路径]")
        sys.exit(1)
    
    result = extract_titles_from_image(image_path)
    if result:
        print(f"处理成功，结果保存在: {result}")
    else:
        print("处理失败")
        sys.exit(1)
        
        
