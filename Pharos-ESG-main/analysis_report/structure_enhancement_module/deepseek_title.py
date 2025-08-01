import requests
import time
import logging
import json
import re

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 场景一：用于 align_titles 阶段的 LLM 标题选择
SYSTEM_PROMPT_SELECT_TITLE = (
    "你是一个结构化文档标题对齐专家，你的任务是从给定的候选标题列表中，选择最符合目标文本上下文的标题。\n"
    "要求：\n"
    "1. 只能从以下候选里选择一个\n"
    "2. 不要生成新的标题\n"
    "3. 输出格式：选择：<你选的标题>"
)

# 场景二：用于智能插入的 LLM 分析
SYSTEM_PROMPT_INSERT_POSITION = (
    "你是一个结构化文档分析专家，专门判断标题在非结构化文本中应插入的位置。你的任务是根据目标标题与文档内容的语义、结构、主题关系，判断其最自然、合理的插入位置。\n"
    "判断时需要考虑：\n"
    "1. 语义连贯性：插入后与上下文是否自然衔接\n"
    "2. 结构合理性：是否适合作为新的主题的开始\n"
    "3. 内容相关性：与周围内容的主题是否相关\n"
    "你需要准确判断应将标题插入到哪一行文本之前，或指出当前范围内不适合插入"
)

def deepseek_api(content, api_key, system_prompt=None, max_retries=3, retry_delay=5, use_r1=True):
    """
    调用DeepSeek AI API（支持V3和R1两种模型）
    Args:
        content (str): 要发送的内容
        api_key (str): API密钥
        system_prompt (str): 系统提示词，支持不同场景
        max_retries (int): 最大重试次数
        retry_delay (int): 重试间隔（秒）
        use_r1 (bool): 是否使用DeepSeek R1模型
    Returns:
        str: API响应的文本内容
    """
    # 根据模型选择API配置
    if use_r1:
        API_URL = "https://deepseek-r1-0528.ibswufe.com:21112/v1/chat/completions"
        model_name = "deepseek-r1-0528"
        max_tokens = 1024  # R1模型使用更大的token限制
    else:
        API_URL = "https://api.siliconflow.cn/v1/chat/completions"
        model_name = "Pro/deepseek-ai/DeepSeek-V3"
        max_tokens = 512

    # 默认场景二的提示词
    if system_prompt is None:
        system_prompt = SYSTEM_PROMPT_INSERT_POSITION

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    data = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content}
        ],
        "max_tokens": max_tokens,
        "temperature": 0.1,
    }

    for attempt in range(max_retries):
        try:
            response = requests.post(API_URL, headers=headers, json=data)
            if response.status_code == 200:
                response_data = response.json()
                message = response_data["choices"][0]["message"]
                
                # DeepSeek R1模型的响应格式特殊处理
                if use_r1 and message.get("content") is None and "reasoning_content" in message:
                    # R1模型的内容在reasoning_content字段中
                    return message["reasoning_content"]
                else:
                    # 普通模型的内容在content字段中
                    return message.get("content")
            elif response.status_code == 429:
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (attempt + 1)
                    logging.warning(f"达到速率限制，等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                    continue
                else:
                    logging.error("达到最大重试次数，仍然失败")
                    return None
            else:
                logging.error(f"请求失败，状态码：{response.status_code}, 错误信息：{response.text}")
                return None
        except Exception as e:
            logging.error(f"请求出错: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
            return None
    return None

def parse_api_response(response):
    """解析API返回的结果"""
    try:
        # 清理响应文本
        response = response.strip()
        if response.startswith('```json'):
            response = response[7:]
        if response.endswith('```'):
            response = response[:-3]
        response = response.strip()
        
        # 替换单引号为双引号
        response = response.replace("'", '"')
        
        # 修复可能的格式问题
        response = re.sub(r'(\w+):', r'"\1":', response)  # 给属性名添加双引号
        response = re.sub(r',\s*}', '}', response)  # 移除对象末尾多余的逗号
        response = re.sub(r',\s*]', ']', response)  # 移除数组末尾多余的逗号
        
        # 尝试解析JSON
        return json.loads(response)
    except json.JSONDecodeError as e:
        logging.error(f"JSON解析错误: {str(e)}")
        logging.error(f"清理后的响应: {response}")
        return []
    except Exception as e:
        logging.error(f"解析API响应时出错: {str(e)}")
        logging.error(f"原始响应: {response}")
        return []