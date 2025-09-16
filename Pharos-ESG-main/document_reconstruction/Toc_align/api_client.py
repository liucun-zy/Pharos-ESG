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

def deepseek_api(content, api_key, system_prompt=None, max_retries=5, retry_delay=10, timeout=120):
    """
    调用DeepSeek AI API
    Args:
        content (str): 要发送的内容
        api_key (str): API密钥
        system_prompt (str): 系统提示词，支持不同场景
        max_retries (int): 最大重试次数
        retry_delay (int): 重试间隔（秒）
        timeout (int): 请求超时时间（秒）
    Returns:
        str: API响应的文本内容
    """
    # API配置 - 尝试不同的路径格式
    # 首先尝试标准路径
    API_URL = "https://qwen3-coder-480b-a35b-instruct.ibswufe.com:21112/v1/chat/completions"
    model_name = "qwen3-coder-480b-a35b-instruct"
    max_tokens = 1024

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
            logging.info(f"尝试第 {attempt + 1} 次API调用...")
            logging.info(f"API URL: {API_URL}")
            logging.info(f"Model: {model_name}")
            response = requests.post(API_URL, headers=headers, json=data, timeout=timeout)
            
            if response.status_code == 200:
                response_data = response.json()
                message = response_data["choices"][0]["message"]
                return message.get("content")
                    
            elif response.status_code == 429:
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)  # 指数退避
                    logging.warning(f"达到速率限制，等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                    continue
                else:
                    logging.error("达到最大重试次数，仍然失败")
                    return None
                    
            elif response.status_code == 504:
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)  # 指数退避
                    logging.warning(f"网关超时 (504)，等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                    continue
                else:
                    logging.error("达到最大重试次数，网关超时仍然失败")
                    return None
                    
            else:
                logging.error(f"请求失败，状态码：{response.status_code}, 错误信息：{response.text}")
                # 如果是404错误，尝试不同的路径
                if response.status_code == 404 and attempt == 0:
                    logging.info("尝试备用API路径...")
                    # 尝试备用路径1：不使用chat/completions
                    backup_url1 = "https://qwen3-coder-480b-a35b-instruct.ibswufe.com:21112/v1"
                    try:
                        logging.info(f"尝试备用路径1: {backup_url1}")
                        response = requests.post(backup_url1, headers=headers, json=data, timeout=timeout)
                        if response.status_code == 200:
                            response_data = response.json()
                            message = response_data["choices"][0]["message"]
                            return message.get("content")
                    except Exception as e:
                        logging.error(f"备用路径1也失败: {str(e)}")
                    
                    # 尝试备用路径2：使用chat/completions但不带v1
                    backup_url2 = "https://qwen3-coder-480b-a35b-instruct.ibswufe.com:21112/chat/completions"
                    try:
                        logging.info(f"尝试备用路径2: {backup_url2}")
                        response = requests.post(backup_url2, headers=headers, json=data, timeout=timeout)
                        if response.status_code == 200:
                            response_data = response.json()
                            message = response_data["choices"][0]["message"]
                            return message.get("content")
                    except Exception as e:
                        logging.error(f"备用路径2也失败: {str(e)}")
                
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)
                    logging.info(f"等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                    continue
                return None
                
        except requests.exceptions.Timeout:
            logging.warning(f"请求超时 (尝试 {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                wait_time = retry_delay * (2 ** attempt)
                logging.info(f"等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
                continue
            else:
                logging.error("达到最大重试次数，请求超时")
                return None
                
        except requests.exceptions.ConnectionError:
            logging.warning(f"连接错误 (尝试 {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                wait_time = retry_delay * (2 ** attempt)
                logging.info(f"等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
                continue
            else:
                logging.error("达到最大重试次数，连接错误")
                return None
                
        except Exception as e:
            logging.error(f"请求出错: {str(e)}")
            if attempt < max_retries - 1:
                wait_time = retry_delay * (2 ** attempt)
                logging.info(f"等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
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

def test_api_connection(api_key: str) -> bool:
    """
    测试API连接是否正常
    Args:
        api_key: API密钥
    Returns:
        bool: 连接是否成功
    """
    API_URL = "https://qwen3-coder-480b-a35b-instruct.ibswufe.com:21112/v1/chat/completions"
    model_name = "qwen3-coder-480b-a35b-instruct"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": model_name,
        "messages": [
            {"role": "user", "content": "Hello"}
        ],
        "max_tokens": 10,
        "temperature": 0.1,
    }
    
    try:
        logging.info("测试API连接...")
        logging.info(f"测试URL: {API_URL}")
        logging.info(f"测试模型: {model_name}")
        response = requests.post(API_URL, headers=headers, json=data, timeout=30)
        logging.info(f"测试响应状态码: {response.status_code}")
        logging.info(f"测试响应内容: {response.text[:200]}")
        return response.status_code == 200
    except Exception as e:
        logging.error(f"API连接测试失败: {str(e)}")
        return False