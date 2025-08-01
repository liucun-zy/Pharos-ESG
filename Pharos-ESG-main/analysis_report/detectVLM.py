import base64
import requests
import json
import os
from typing import List, Dict, Tuple, Set
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock, Timer
from queue import Queue
import time
from requests.exceptions import RequestException, Timeout
import functools
import threading
import hashlib
import pickle
from pathlib import Path
import argparse
import glob
from urllib.parse import quote

# 添加线程安全的打印锁
print_lock = Lock()
def safe_print(*args, **kwargs):
    """线程安全的打印函数"""
    with print_lock:
        print(*args, **kwargs)

# 定义允许的图片类型
ALLOWED_TYPES = {
    '表格图', '流程图', '统计图', '关系图', '纯文本图', '混合型', '组合型'
}

# 添加缓存配置
CACHE_DIR = "cache"
CACHE_EXPIRE_TIME = 24 * 60 * 60  # 缓存过期时间（秒）
CACHE_LOCK = Lock()  # 缓存锁

def get_cache_key(prompt: str, images_base64: List[Dict]) -> str:
    """生成缓存键"""
    # 将提示词和图片信息组合
    content = prompt + json.dumps(images_base64, sort_keys=True)
    # 使用MD5生成唯一键
    return hashlib.md5(content.encode()).hexdigest()

def get_cache_path(cache_key: str) -> Path:
    """获取缓存文件路径"""
    return Path(CACHE_DIR) / f"{cache_key}.pkl"

def load_from_cache(cache_key: str) -> Dict:
    """从缓存加载数据"""
    cache_path = get_cache_path(cache_key)
    if not cache_path.exists():
        return None
    
    try:
        with CACHE_LOCK:
            with open(cache_path, 'rb') as f: 
                cache_data = pickle.load(f)
                
        # 检查缓存是否过期
        if time.time() - cache_data['timestamp'] > CACHE_EXPIRE_TIME:
            return None
            
        return cache_data['result']
    except Exception as e:
        safe_print(f"读取缓存失败: {e}")
        return None

def save_to_cache(cache_key: str, result: Dict):
    """保存数据到缓存"""
    cache_path = get_cache_path(cache_key)
    cache_data = {
        'timestamp': time.time(),
        'result': result
    }
    
    try:
        # 确保缓存目录存在
        os.makedirs(CACHE_DIR, exist_ok=True)
        
        with CACHE_LOCK:
            with open(cache_path, 'wb') as f:
                pickle.dump(cache_data, f)
    except Exception as e:
        safe_print(f"保存缓存失败: {e}")

# 定义提示词模板
prompt_template = """你是一个专业的ESG报告图像理解助手，将协助用户识别并分析一个 JSON 结构化内容块中所包含的图片信息。每个输入的 JSON 块属于文档中的一个逻辑段落。
一、json块类型：
1.普通块：
结构如下：
{
  "h1": "一级标题",
  "h2": null 或 "二级标题",
  "h3": null,或 "三级标题",
  "h4": null,或 "四级标题",
  "data": "图片![](xxx.jpg)",
  "data_type":"image" 
}
2.聚类块（cluster）：
{
  "data_indices": [index1, index2, index3, ...],
  "data": ["text内容", "图片![](xxx.jpg)", "表格内容", "text内容", "图片![](xxx.jpg)",  ...], # 多个data项，按顺序排列，包括 text, image, table 
  "data_type": "cluster["text1", "image2", "table3", "text4", "image5",  ...]",
  "h1": "...",
  "h2": "...",
  "h3": "...",
  "h4": "..."
}
❗<注意>：若为聚类块，请将其作为一个完整的段落处理，每张图片都应结合上下文的文字分析。

二、图像类型分类说明（必须从以下七种中选择其一）：
    1.表格图：以表格形式呈现结构化数据（含边框/表头/单元格）。
    2.流程图：展现流程、阶段、路径或操作步骤（常含箭头、节点）。
    3.统计图：条形图、折线图、饼图、柱状图等基于数值分布的图。
    4.关系图：展示元素之间的连接、归属或层级（如组织架构图）。
    5.纯文本图：整张图主要是文字块，没有图形结构、颜色编码等信息。
    6.混合图：一张图中包含多类视觉元素，如图表+图标+照片+界面等。
    7.组合图：两张及以上图片形成信息闭环，必须联合理解。
❗特别说明：混合图vs组合图判定标准：
    混合图：指一张图内部混杂多种信息结构（如文字+表格+照片+界面），其多样性体现在"单图内"。
    组合图：指两张及以上图片在逻辑上必须联合理解，分别承担解释/示意/数据等职责，缺一不可。
    典型组合图例子：
        图1为编号图例，图2为编号分布图；
        图1为活动说明，图2为活动现场；，ll
        图1为分组说明，图2为分组占比图。
    组合图的判定必须在分析图片前完成，一旦识别为组合图，请将两张图混合为一个输出，输出位置按照两张图合并后的具体语义去插入到上下文中。
❗如图片位于聚类块中，请结合其上下文文本（data 列表中的其他文本项）进行分析。禁止孤立处理图片内容，所有描述必须基于可见要素与上下文关系展开，避免主观判断与未证实的推断。

三、输出格式与风格要求
1.所有输出必须为完整自然语言段落，风格正式、客观，符合撰写报告风格语言规范。
2.除统计图和混合图外，禁止使用"该图展示了"、"图片中可以看到"、"如下图所示"等描述性句式。
3.统计图可以简要说明图表类型，例如"这是柱状图，展示了……"。
4.混合图可以进行结构性描述，例如"图像左侧为……，右侧为……"。
5.除上述两类外，所有图像内容应以嵌入式语言呈现，即直接写入上下文中，不得显式指出图像来源或图像存在。
6.图像分析必须结合上下文内容，避免孤立描述。可参考以下表达方式：
    -"……也体现在具体的课程安排中。"
    -"……相关数据反映了员工参与的广泛程度。"
    -"……不同主题覆盖了合规、数据、写作等多个方向。"
7.输出中禁止使用以下内容：
    -Markdown 标记（如 **、#、``` 等）
    -特殊字符（如 ★、※ 等）
    -转义符（如 \n、\t 等）
8.不得加入主观推测或修饰性语言，不得揣测图中人物、组织的意图、态度或情绪。所有分析必须基于图像中可辨认的内容以及上下文信息。

四、输出格式： 
     ```
     <图片类型> <自然语言表述图片内容>
     ```  
 ⚠️ 注意：图片类型必须且只能是以下七种之一：表格图、流程图、统计图、关系图、纯文本图、混合图、组合图

请分析以下数据：
"""

def encode_image_to_base64(image_path):
    """将本地图片转换为base64编码"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def extract_image_path(image_url: str, base_path: str) -> str:
    """从Markdown图片URL中提取图片路径，只保留文件名，拼接到base_path下"""
    safe_print(f"\n开始处理图片URL: {image_url}")
    safe_print(f"基础路径: {base_path}")
    match = re.search(r'!\[\]\((.*?\.(?:jpg|png|jpeg|bmp|gif|webp))\)', image_url, re.IGNORECASE)
    if match:
        relative_path = match.group(1)
        safe_print(f"1. 从Markdown中提取的相对路径: {relative_path}")
        # 只保留文件名
        filename = os.path.basename(relative_path)
        safe_print(f"2. 提取的文件名: {filename}")
        # 拼接到base_path下
        full_path = os.path.join(base_path, filename)
        full_path = full_path.replace('\\', '/')
        safe_print(f"3. 最终图片路径: {full_path}")
        return full_path
    safe_print("未找到有效的图片URL")
    return ""

def extract_relative_path_from_markdown(image_url: str) -> str:
    """从Markdown图片URL中提取完整的相对路径"""
    match = re.search(r'!\[\]\((.*?\.(?:jpg|png|jpeg|bmp|gif|webp))\)', image_url, re.IGNORECASE)
    if match:
        return match.group(1)
    return ""

def query_qwen_vl_with_template(api_config, images_base64, prompt_template, api_key=None):
    """使用提示词模板调用Qwen-VL模型，支持多图片处理和缓存"""
    # 生成缓存键
    cache_key = get_cache_key(prompt_template, images_base64)
    
    # 尝试从缓存加载
    cached_result = load_from_cache(cache_key)
    if cached_result:
        safe_print("使用缓存结果")
        return cached_result
    
    headers = {
        "Authorization": f"Bearer {api_key or api_config['api_key']}",
        "Content-Type": "application/json"
    }
    
    # 构建多模态请求体，使用系统消息设置提示词模板
    payload = {
        "model": api_config["model"],
        "messages": [
            {
                "role": "system",
                "content": prompt_template  # 将模板作为系统指令
            },
            {
                "role": "user",
                "content": images_base64  # 直接传入图片列表
            }
        ],
        "max_tokens": 4096
    }
    
    try:
        safe_print("正在识别当前图片")
        response = requests.post(api_config["api_url"], headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        
        # 保存到缓存
        save_to_cache(cache_key, result)
        return result
    
    except requests.exceptions.RequestException as e:
        safe_print(f"API请求失败: {e}")
        return None

def contains_image(data: List) -> bool:
    """检查data列表中是否包含图片"""
    if not isinstance(data, list):
        return False
    return any(isinstance(item, str) and ('.jpg' in item.lower() or '.png' in item.lower()) for item in data)

def find_blocks_with_images(blocks: List[Dict]) -> List[Dict]:
    """找出所有包含图片的块，或者包含table_path的普通table块"""
    blocks_with_images = []
    for block in blocks:
        if isinstance(block, dict) and 'data' in block:
            # 获取数据类型列表
            data_types = block.get('data_type', '').replace('cluster[', '').replace(']', '').split(',') if 'data_type' in block else ['text'] * len(block['data'])
            # 确保每个类型后面都有]
            data_types = [f"{type_str}]" if not type_str.endswith(']') else type_str for type_str in data_types]
            # 检查是否包含图片类型，或者是包含table_path的普通table块
            has_images = any(data_type.startswith('image') for data_type in data_types)
            is_table_with_path = (block.get('data_type') == 'table' and 'table_path' in block and block['table_path'])
            if has_images or is_table_with_path:
                blocks_with_images.append(block)
    return blocks_with_images

def clean_image_type(image_type: str) -> str:
    """清理图片类型，只保留正确的类型"""
    # 定义允许的图片类型
    allowed_types = {'表格图', '流程图', '统计图', '关系图', '纯文本图', '混合图', '组合图'}
    
    # 移除多余字符
    cleaned_type = image_type.replace('```', '').replace('\n', '').strip()
    
    # 检查是否是允许的类型
    for type_name in allowed_types:
        if type_name in cleaned_type:
            return type_name
    
    return '纯文本图'  # 默认返回纯文本图

def merge_combined_images(image_types: List[str]) -> List[str]:
    """合并连续的组合图类型"""
    result = []
    i = 0
    while i < len(image_types):
        if '[组合图]' in image_types[i]:
            # 收集连续的组合图
            combined_indices = []
            while i < len(image_types) and '[组合图]' in image_types[i]:
                # 提取图片索引
                match = re.search(r'image\[(.*?)\]\[组合图\]', image_types[i])
                if match:
                    indices = match.group(1).split(',')
                    combined_indices.extend(indices)
                i += 1
            # 添加合并后的组合图
            if combined_indices:
                result.append(f"image[{','.join(combined_indices)}][组合图]")
        else:
            result.append(image_types[i])
            i += 1
    return result

# 配置参数
API_CONFIG = {
    "api_key": "",
    "api_url": "https://api.siliconflow.cn/v1/chat/completions",
    "model": "",
}

# 配置多个API key
API_KEYS = [
    "",
    ""
]

# 添加超时设置
API_TIMEOUT = 30  # API调用超时时间（秒）
PROCESS_TIMEOUT = 60  # 单个块处理超时时间（秒）
MAX_RETRIES = 3  # 最大重试次数
RETRY_DELAY = 5  # 重试间隔（秒）

def timeout_handler(timeout_seconds):
    """超时处理装饰器"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            result = []
            error = []
            
            def target():
                try:
                    result.append(func(*args, **kwargs))
                except Exception as e:
                    error.append(e)
            
            thread = threading.Thread(target=target)
            thread.daemon = True
            thread.start()
            thread.join(timeout_seconds)
            
            if thread.is_alive():
                raise TimeoutError(f"函数执行超时（{timeout_seconds}秒）")
            if error:
                raise error[0]
            return result[0]
        return 

    
    return decorator

@timeout_handler(PROCESS_TIMEOUT)
def process_block_with_api_key(block: Dict, api_key: str, block_index: int, total_blocks: int, image_dir: str) -> Dict:
    """使用指定的API key处理一个块"""
    start_time = time.time()
    block_id = f"块 {block_index + 1}/{total_blocks}"
    safe_print(f"\n{block_id} 开始处理 - {time.strftime('%H:%M:%S')}")
    
    try:
        if 'data' not in block:
            safe_print(f"{block_id} 跳过: 无数据")
            return block

        # 获取数据类型列表和数据列表
        data_types = []
        is_normal_block = False
        if 'data_type' in block:
            if block['data_type'].startswith('cluster'):
                # 处理聚类块
                type_str = block['data_type'].replace('cluster[', '').replace(']', '')
                data_types = [t.strip() for t in type_str.split(',')]
            else:
                # 处理普通块
                data_types = [block['data_type']]
                is_normal_block = True
        else:
            # 如果没有data_type，默认为text
            data_types = ['text'] * len(block['data'])

        # 修正：普通块data为字符串时转为单元素列表
        if is_normal_block and isinstance(block['data'], str):
            data_list = [block['data']]
        else:
            data_list = block['data']

        data_indices = block.get('data_indices', list(range(len(data_list))))
        safe_print(f"[DEBUG] data_indices: {data_indices} (type: {type(data_indices)})")
        if data_indices and isinstance(data_indices[0], list):
            reading_orders = [idx[1] for idx in data_indices]
        else:
            reading_orders = data_indices
        safe_print(f"[DEBUG] reading_orders: {reading_orders} (type: {type(reading_orders)})")
        
        safe_print(f"\n{block_id} 初始数据:")
        safe_print(f"data_types: {data_types}")
        safe_print(f"data_indices: {data_indices}")
        
        # 处理所有数据，保持原始顺序
        processed_data = []
        image_types = []  # 存储图片类型信息（如<混合图>）
        current_images = []
        current_image_paths = []
        current_image_indices = []
        current_image_positions = []
        image_paths = []  # 存储图片路径信息
        
        # 按照原始顺序处理所有数据
        for i, (data, data_type) in enumerate(zip(data_list, data_types)):
            reading_order = reading_orders[i] if i < len(reading_orders) else i
            safe_print(f"[DEBUG] i: {i}, data: {data}, data_type: {data_type}, reading_order: {reading_order}")
            
            if not data_type.startswith('image'):
                processed_data.append(data)
                image_types.append(None)
                image_paths.append(None)
                safe_print(f"添加非图片数据: {data_type}")
                safe_print(f"当前image_types列表: {image_types}")
            else:
                current_images.append(data)
                image_path = extract_image_path(data, image_dir)
                if not image_path or not os.path.exists(image_path):
                    safe_print(f"警告: 图片路径不存在: {image_path}")
                    processed_data.append(data)
                    image_types.append(None)
                    image_paths.append(None)
                    continue
                current_image_paths.append(image_path)
                current_image_indices.append(i)
                current_image_positions.append(i)
                image_paths.append(data)  # 保存原始图片链接
                safe_print(f"[DEBUG] current_image_indices: {current_image_indices}")
                safe_print(f"[DEBUG] current_image_positions: {current_image_positions}")
                
                if i < len(data_list) - 1:
                    continue
                    
            if current_images:
                safe_print(f"[DEBUG] current_images: {current_images}")
                safe_print(f"[DEBUG] current_image_indices: {current_image_indices}")
                safe_print(f"[DEBUG] current_image_positions: {current_image_positions}")
                # 获取当前图片之前的所有文本作为上下文
                context_texts = []
                # 获取标题信息
                for key in ['h1', 'h2', 'h3', 'h4']:
                    if key in block and block[key]:
                        context_texts.append(f"{key.upper()}: {block[key]}")
                
                # 获取所有相关文本（包括图片之间的文本）
                all_texts = []
                start_idx = 0
                end_idx = len(data_list)
                
                # 如果是连续图片，获取整个图片组的上下文
                if len(current_image_indices) > 1:
                    start_idx = max(0, current_image_indices[0] - 1)  # 获取第一张图片前的文本
                    end_idx = min(len(data_list), current_image_indices[-1] + 2)  # 获取最后一张图片后的文本
                else:
                    # 单张图片的情况
                    start_idx = max(0, current_image_indices[0] - 1)
                    end_idx = min(len(data_list), current_image_indices[0] + 2)
                
                # 收集指定范围内的所有文本
                for i in range(start_idx, end_idx):
                    if i not in current_image_indices:  # 跳过当前图片
                        data = data_list[i]
                        data_type = data_types[i]
                        data_index = data_indices[i]
                        safe_print(f"[DEBUG] all_texts收集: i={i}, data_index={data_index} (type: {type(data_index)})")
                        if data_type in ['text', 'table']:
                            prefix = "前文" if i < current_image_indices[0] else "后文"
                            # 修正：data_index为list时取最后一个元素
                            if isinstance(data_index, list):
                                idx_val = data_index[-1]
                            else:
                                idx_val = data_index
                            all_texts.append((i, f"{prefix} {idx_val + 1} ({data_type}): {data}"))
                
                # 按原始顺序排序并添加到context_texts
                all_texts.sort(key=lambda x: x[0])
                context_texts.extend([text for _, text in all_texts])
                
                # 限制上下文长度（保留靠近图片的上下文）
                MAX_CONTEXT_LENGTH = 2000  # 设置最大上下文长度
                if len(context_texts) > MAX_CONTEXT_LENGTH:
                    # 保留标题和靠近图片的上下文
                    title_texts = [text for text in context_texts if text.startswith(('H1:', 'H2:', 'H3:', 'H4:'))]
                    other_texts = [text for text in context_texts if not text.startswith(('H1:', 'H2:', 'H3:', 'H4:'))]
                    
                    # 计算需要保留的文本数量
                    remaining_length = MAX_CONTEXT_LENGTH - len(title_texts)
                    half_length = remaining_length // 2
                    
                    # 保留前一半和后一半的文本
                    context_texts = title_texts + other_texts[:half_length] + other_texts[-half_length:]
                
                # 构建完整的提示词（使用线程安全的prompt_template）
                context_str = "\n".join(context_texts)
                thread_safe_prompt = prompt_template  # 创建线程本地副本
                full_prompt = f"{thread_safe_prompt}\n\n上下文信息：\n{context_str}\n\n当前图片：\n" + "\n".join(current_images)
                
                # 打印上下文信息用于调试
                safe_print(f"\n当前块的上下文信息:")
                safe_print(f"标题信息: {[text for text in context_texts if text.startswith(('H1:', 'H2:', 'H3:', 'H4:'))]}")
                safe_print(f"前文数量: {len([text for text in context_texts if text.startswith('前文')])}")
                safe_print(f"后文数量: {len([text for text in context_texts if text.startswith('后文')])}")
                safe_print(f"当前图片数量: {len(current_images)}")
                safe_print(f"上下文总长度: {len(context_str)}")
                safe_print(f"完整提示词长度: {len(full_prompt)}")
                
                # 调用VLM处理图片
                safe_print(f"\n正在调用VLM处理图片: {', '.join(current_image_paths)}")
                all_images_base64 = []
                for img_path in current_image_paths:
                    image_base64 = encode_image_to_base64(img_path)
                    all_images_base64.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}"
                        }
                    })
                
                # 添加重试机制
                for retry in range(MAX_RETRIES):
                    try:
                        result = query_qwen_vl_with_template(API_CONFIG, all_images_base64, full_prompt, api_key)
                        if result:
                            safe_print(f"VLM返回结果: {result['choices'][0]['message']['content'][:100]}...")
                            content = result['choices'][0]['message']['content']
                            
                            # 处理VLM返回的结果
                            # 检查是否是组合图
                            is_combined = "组合图" in content[:content.find('\n')] if '\n' in content else "组合图" in content
                            if is_combined:
                                safe_print(f"[DEBUG] 组合图 current_image_indices: {current_image_indices}")
                                safe_print(f"[DEBUG] 组合图 data_indices: {data_indices}")
                                combined_indices = []
                                for idx in current_image_indices:
                                    safe_print(f"[DEBUG] 组合图 idx: {idx}, data_indices[idx]: {data_indices[idx]} (type: {type(data_indices[idx])})")
                                    # 修正：data_indices[idx]为list时取最后一个元素
                                    if isinstance(data_indices[idx], list):
                                        combined_indices.append(str(data_indices[idx][-1]))
                                    else:
                                        combined_indices.append(str(data_indices[idx]))
                                image_types.append(f"image[{','.join(combined_indices)}][组合图]")
                                safe_print(f"[DEBUG] 添加组合图类型: image[{','.join(combined_indices)}][组合图]")
                            else:
                                # 如果不是组合图，分别处理每个图片
                                # 提取图片类型（第一个空格前的内容）
                                image_type = content.split(' ')[0] if ' ' in content else ''
                                # 清理图片类型
                                cleaned_type = clean_image_type(image_type)
                                # 提取实际内容（第一个空格后的内容）
                                actual_content = content[content.find(' ')+1:].strip() if ' ' in content else content
                                
                                # 为每个图片单独添加类型
                                for idx in current_image_indices:
                                    safe_print(f"[DEBUG] 普通图片 idx: {idx}, data_indices[idx]: {data_indices[idx]} (type: {type(data_indices[idx])})")
                                    # 修正：data_indices[idx]为list时取最后一个元素
                                    if isinstance(data_indices[idx], list):
                                        image_types.append(f"image[{data_indices[idx][-1]}][{cleaned_type}]")
                                    else:
                                        image_types.append(f"image[{data_indices[idx]}][{cleaned_type}]")
                                
                                # 插入处理后的文本（不包含图片类型）
                                for idx, pos in enumerate(current_image_positions):
                                    # 插入处理后的文本内容
                                    processed_data.insert(pos, actual_content)
                            break  # 成功处理，跳出重试循环
                    except (RequestException, Timeout) as e:
                        if retry < MAX_RETRIES - 1:
                            safe_print(f"第 {retry + 1} 次尝试失败: {e}，等待 {RETRY_DELAY} 秒后重试...")
                            time.sleep(RETRY_DELAY)
                        else:
                            safe_print("所有重试都失败，保持原始数据")
                            for idx in current_image_indices:
                                processed_data.append(data_list[idx])
                                image_types.append(f"image[{data_indices[idx]}]")
                    except Exception as e:
                        safe_print(f"处理过程中发生异常: {e}")
                        for idx in current_image_indices:
                            processed_data.append(data_list[idx])
                            image_types.append(f"image[{data_indices[idx]}]")
                        break
                
                # 清空当前图片列表
                current_images = []
                current_image_paths = []
                current_image_indices = []
                current_image_positions = []
        
        # 修正：确保image_types和processed_data长度与data_list一致
        if len(image_types) < len(data_list):
            image_types += [None] * (len(data_list) - len(image_types))
        if len(processed_data) < len(data_list):
            processed_data += [None] * (len(data_list) - len(processed_data))
        # 更新原始块的数据
        # 修正：普通块还原为字符串
        if is_normal_block:
            # 只取第一个元素，且不能为None
            # 如果是图片，保留图片链接和内容
            if data_types[0].startswith('image') and image_types[0]:
                block['data'] = processed_data[0] if processed_data and processed_data[0] is not None else block['data']
                block['image_markdown_url'] = image_paths[0]  # 将image_markdown_url作为独立字段
                # 添加可点击的文件路径
                if image_paths[0]:
                    # 从Markdown中提取完整的相对路径
                    markdown_rel_path = extract_relative_path_from_markdown(image_paths[0])
                    img_file_path = extract_image_path(image_paths[0], image_dir)
                    if img_file_path:
                        # 生成相对路径（相对于项目根目录）
                        try:
                            rel_path = os.path.relpath(img_file_path, "/Users/liucun/Desktop/report_analysis")
                            block['image_relative_path'] = rel_path
                            # 生成绝对路径的file:// URL（当前环境可用）
                            encoded_abs_path = quote(img_file_path, safe=':/')
                            block['image_file_url'] = f"file://{encoded_abs_path}"
                            # 生成HTTP本地服务器链接（端口8000）- 使用Markdown中的完整路径
                            if markdown_rel_path:
                                http_path = quote(markdown_rel_path.replace('\\', '/'), safe='/')
                                block['image_http_url'] = f"http://localhost:8000/{http_path}"
                            else:
                                # 如果无法从Markdown提取路径，使用相对路径
                                http_path = quote(rel_path.replace('\\', '/'), safe='/')
                                block['image_http_url'] = f"http://localhost:8000/{http_path}"
                        except:
                            block['image_relative_path'] = ""
                            block['image_file_url'] = ""
                            block['image_http_url'] = ""
                # 普通块data_type加图片类型标签  
                block['data_type'] = f"image<{image_types[0]}>"
            else:
                block['data'] = processed_data[0] if processed_data and processed_data[0] is not None else block['data']
        else:
            block['data'] = processed_data
            
        # 处理聚类块中的image_paths，为每个image_path添加路径格式
        if not is_normal_block and image_paths:
            # 为聚类块中的图片添加路径格式
            image_file_urls = []
            image_relative_paths = []
            clean_image_paths = []  # 存储非None的image_path
            
            for img_path in image_paths:
                if img_path:  # 只处理非None的image_path
                    clean_image_paths.append(img_path)
                    # 从Markdown中提取完整的相对路径
                    markdown_rel_path = extract_relative_path_from_markdown(img_path)
                    # 提取实际的图片路径
                    img_file_path = extract_image_path(img_path, image_dir)
                    if img_file_path:
                        # 生成相对路径（相对于项目根目录）
                        try:
                            rel_path = os.path.relpath(img_file_path, "/Users/liucun/Desktop/report_analysis")
                            image_relative_paths.append(rel_path)
                            # 生成绝对路径的file:// URL（当前环境可用）
                            encoded_abs_path = quote(img_file_path, safe=':/')
                            image_file_urls.append(f"file://{encoded_abs_path}")
                        except:
                            image_relative_paths.append("")
                            image_file_urls.append("")
                    else:
                        image_file_urls.append("")
                        image_relative_paths.append("")
            
            # 只有当有图片路径时才添加字段
            if clean_image_paths:
                block['image_markdown_urls'] = clean_image_paths
                block['image_file_urls'] = image_file_urls
                block['image_relative_paths'] = image_relative_paths
                # 添加HTTP URL格式
                image_http_urls = []
                for i, rel_path in enumerate(image_relative_paths):
                    if rel_path and i < len(clean_image_paths):
                        # 从对应的Markdown路径中提取完整相对路径
                        markdown_rel_path = extract_relative_path_from_markdown(clean_image_paths[i])
                        if markdown_rel_path:
                            # HTTP本地服务器链接 - 使用Markdown中的完整路径
                            http_path = quote(markdown_rel_path.replace('\\', '/'), safe='/')
                            image_http_urls.append(f"http://localhost:8000/{http_path}")
                        else:
                            # 如果无法从Markdown提取路径，使用相对路径
                            http_path = quote(rel_path.replace('\\', '/'), safe='/')
                            image_http_urls.append(f"http://localhost:8000/{http_path}")
                    else:
                        image_http_urls.append("")
                block['image_http_urls'] = image_http_urls
                
        # 处理聚类块中的table_paths，为每个table_path添加路径格式
        if 'table_paths' in block and block['table_paths']:
            table_file_urls = []
            table_relative_paths = []
            for table_path in block['table_paths']:
                # 从Markdown中提取完整的相对路径
                markdown_rel_path = extract_relative_path_from_markdown(table_path)
                # 提取实际的图片路径
                img_file_path = extract_image_path(table_path, image_dir)
                if img_file_path:
                    # 生成相对路径（相对于项目根目录）
                    try:
                        rel_path = os.path.relpath(img_file_path, "/Users/liucun/Desktop/report_analysis")
                        table_relative_paths.append(rel_path)
                        # 生成绝对路径的file:// URL（当前环境可用）
                        encoded_abs_path = quote(img_file_path, safe=':/')
                        table_file_urls.append(f"file://{encoded_abs_path}")
                    except:
                        table_relative_paths.append("")
                        table_file_urls.append("")
                else:
                    table_file_urls.append("")
                    table_relative_paths.append("")
            
            # 重命名table_paths为table_markdown_urls
            block['table_markdown_urls'] = block.pop('table_paths')
            # 添加新的路径格式字段
            block['table_file_urls'] = table_file_urls
            block['table_relative_paths'] = table_relative_paths
            # 添加HTTP URL格式
            table_http_urls = []
            for i, rel_path in enumerate(table_relative_paths):
                if rel_path and i < len(block['table_markdown_urls']):
                    # 从对应的Markdown路径中提取完整相对路径
                    markdown_rel_path = extract_relative_path_from_markdown(block['table_markdown_urls'][i])
                    if markdown_rel_path:
                        # HTTP本地服务器链接 - 使用Markdown中的完整路径
                        http_path = quote(markdown_rel_path.replace('\\', '/'), safe='/')
                        table_http_urls.append(f"http://localhost:8000/{http_path}")
                    else:
                        # 如果无法从Markdown提取路径，使用相对路径
                        http_path = quote(rel_path.replace('\\', '/'), safe='/')
                        table_http_urls.append(f"http://localhost:8000/{http_path}")
                else:
                    table_http_urls.append("")
            block['table_http_urls'] = table_http_urls
            
        # 处理普通块中的table_path，为单个table_path添加路径格式
        if 'table_path' in block and block['table_path'] and not block.get('data_type', '').startswith('cluster'):
            # 重命名table_path为table_markdown_url
            block['table_markdown_url'] = block.pop('table_path')
            # 从Markdown中提取完整的相对路径
            markdown_rel_path = extract_relative_path_from_markdown(block['table_markdown_url'])
            # 提取实际的图片路径
            img_file_path = extract_image_path(block['table_markdown_url'], image_dir)
            if img_file_path:
                # 生成相对路径（相对于项目根目录）
                try:
                    rel_path = os.path.relpath(img_file_path, "/Users/liucun/Desktop/report_analysis")
                    block['table_relative_path'] = rel_path
                    # 生成绝对路径的file:// URL（当前环境可用）
                    encoded_abs_path = quote(img_file_path, safe=':/')
                    block['table_file_url'] = f"file://{encoded_abs_path}"
                    # 生成HTTP本地服务器链接（端口8000）- 使用Markdown中的完整路径
                    if markdown_rel_path:
                        http_path = quote(markdown_rel_path.replace('\\', '/'), safe='/')
                        block['table_http_url'] = f"http://localhost:8000/{http_path}"
                    else:
                        # 如果无法从Markdown提取路径，使用相对路径
                        http_path = quote(rel_path.replace('\\', '/'), safe='/')
                        block['table_http_url'] = f"http://localhost:8000/{http_path}"
                except:
                    block['table_relative_path'] = ""
                    block['table_file_url'] = ""
                    block['table_http_url'] = ""
        if 'data_type' in block:
            if block['data_type'].startswith('cluster'):
                safe_print(f"\n处理聚类块:")
                safe_print(f"原始data_type: {block['data_type']}")
                # 构建新的data_type字符串
                new_types = []
                for orig_type, img_type in zip(data_types, image_types):
                    if orig_type.startswith('image') and img_type:
                        new_types.append(f"image<{img_type}>")
                    else:
                        new_types.append(orig_type)
                block['data_type'] = f"cluster[{','.join(new_types)}]"
                safe_print(f"最终的data_type: {block['data_type']}")
            else:
                # 普通块逻辑保持不变
                pass
        
        safe_print(f"[DEBUG] 最终 image_types: {image_types}")
        safe_print(f"[DEBUG] 最终 processed_data: {processed_data}")
        return block
            
    except Exception as e:
        safe_print(f"{block_id} 错误: 处理过程中发生异常: {e}")
        for img_info in current_images:
            if isinstance(img_info, dict) and 'index' in img_info and img_info['index'] < len(processed_data):
                processed_data[img_info['index']] = img_info['markdown']
        block['data'] = processed_data
        return block
    finally:
        end_time = time.time()
        processing_time = end_time - start_time
        safe_print(f"{block_id} 处理完成 - 耗时: {processing_time:.2f}秒")

def process_blocks_parallel(blocks: List[Dict], image_dir: str) -> List[Dict]:
    """串行处理所有包含图片的块"""
    # 找出所有包含图片的块
    blocks_with_images = find_blocks_with_images(blocks)
    total_blocks = len(blocks_with_images)
    safe_print(f"\n找到 {total_blocks} 个包含图片的块")
    
    # 创建API key队列和锁
    api_key_queue = Queue()
    api_key_locks = {key: Lock() for key in API_KEYS}
    for key in API_KEYS:
        api_key_queue.put(key)
    
    # 串行处理
    processed_blocks = []
    start_time = time.time()
    failed_blocks = []
    
    # 修改重试间隔为30秒
    RETRY_DELAY = 30  # 重试间隔（秒）
    
    def process_with_retry(block, block_index):
        """带重试机制的处理函数"""
        max_retries = 3
        
        for retry in range(max_retries):
            try:
                safe_print(f"块 {block_index + 1} 第 {retry + 1} 次尝试，准备获取API key...")
                # 获取API key
                api_key = api_key_queue.get()
                safe_print(f"块 {block_index + 1} 获取到API key: {api_key[:8]}...，准备加锁")
                with api_key_locks[api_key]:  # 确保同一key不会被并发使用
                    safe_print(f"块 {block_index + 1} 获得API key锁，开始处理块数据")
                    try:
                        safe_print(f"块 {block_index + 1} (尝试 {retry + 1}/{max_retries}) 调用process_block_with_api_key")
                        # 使用同一个API key处理整个块
                        result = process_block_with_api_key(block, api_key, block_index, total_blocks, image_dir)
                        if result:
                            safe_print(f"块 {block_index + 1} 处理成功，准备归还API key")
                            processed_blocks.append(result)
                            return True
                    except TimeoutError:
                        safe_print(f"块 {block_index + 1} 超时 (第 {retry + 1} 次)")
                        if retry < max_retries - 1:
                            safe_print(f"块 {block_index + 1} 等待 {RETRY_DELAY} 秒后重试...")
                            time.sleep(RETRY_DELAY)
                        continue
                    except Exception as e:
                        safe_print(f"块 {block_index + 1} 失败: {e} (第 {retry + 1} 次)")
                        if retry < max_retries - 1:
                            safe_print(f"块 {block_index + 1} 等待 {RETRY_DELAY} 秒后重试...")
                            time.sleep(RETRY_DELAY)
                        continue
                    finally:
                        # 归还API key
                        safe_print(f"块 {block_index + 1} 归还API key: {api_key[:8]}...")
                        api_key_queue.put(api_key)
            except Exception as e:
                safe_print(f"块 {block_index + 1} 发生异常: {e} (第 {retry + 1} 次)")
                if retry < max_retries - 1:
                    safe_print(f"块 {block_index + 1} 等待 {RETRY_DELAY} 秒后重试...")
                    time.sleep(RETRY_DELAY)
                continue
        
        # 所有重试都失败
        safe_print(f"块 {block_index + 1} 所有重试都失败，写入失败列表")
        failed_blocks.append((block_index, "所有重试都失败"))
        processed_blocks.append(block)
        return False
    
    # 串行处理所有块
    safe_print("开始串行处理所有块")
    for i, block in enumerate(blocks_with_images):
        process_with_retry(block, i)
    
    end_time = time.time()
    total_time = end_time - start_time
    safe_print(f"\n所有块处理完成 - 总耗时: {total_time:.2f}秒")
    safe_print(f"平均每个块处理时间: {total_time/total_blocks:.2f}秒")
    
    if failed_blocks:
        safe_print("\n处理失败的块:")
        for block_index, error in failed_blocks:
            safe_print(f"块 {block_index + 1}: {error}")
    
    # 更新原始blocks列表
    block_dict = {json.dumps(block, sort_keys=True): block for block in blocks}
    for processed_block in processed_blocks:
        block_key = json.dumps(processed_block, sort_keys=True)
        if block_key in block_dict:
            block_dict[block_key] = processed_block
    
    return list(block_dict.values())

def process_single_file(input_json_path: str, image_dir: str) -> None:
    """
    处理单个clustering.json文件
    :param input_json_path: clustering.json文件的完整路径
    :param image_dir: 图片目录的完整路径
    """
    try:
        input_json_path = Path(input_json_path)
        if not input_json_path.exists():
            print(f"错误：文件不存在: {input_json_path}")
            return
            
        if not input_json_path.name.endswith('_clustering.json'):
            print(f"错误：不是目标文件（需要以_clustering.json结尾）: {input_json_path}")
            return
            
        print(f"\n=== 开始处理单个文件 ===")
        print(f"文件路径: {input_json_path}")
        
        # 检查目录名称格式
        report_dir = input_json_path.parent
        parts = report_dir.name.split('-')
        if len(parts) < 3:  # 至少需要股票代码、公司名和报告名
            print(f"警告：目录名称格式不正确: {report_dir.name}")
            return
            
        # 检查第一部分是否为日期（8位数字）
        is_date_format = len(parts[0]) == 8 and parts[0].isdigit()
        
        # 读取JSON文件
        with open(input_json_path, 'r', encoding='utf-8') as f:
            blocks = json.load(f)
        print(f"成功读取JSON文件，包含 {len(blocks)} 个块")
        
        # 查找包含图片的块
        blocks_with_images = find_blocks_with_images(blocks)
        if not blocks_with_images:
            print("未找到包含图片的块")
            return
            
        print(f"找到 {len(blocks_with_images)} 个包含图片的块")
        
        # 并行处理所有块
        processed_blocks = process_blocks_parallel(blocks_with_images, image_dir)
        
        # 更新原始blocks中的图片块
        for i, block in enumerate(blocks):
            if block in blocks_with_images:
                processed_index = blocks_with_images.index(block)
                blocks[i] = processed_blocks[processed_index]
        
        # 设置输出文件路径
        output_json = report_dir / f"{report_dir.name}_vlm.json"
        
        # 保存结果
        with open(output_json, 'w', encoding='utf-8') as f:
            json.dump(blocks, f, ensure_ascii=False, indent=2)
        print(f"处理完成，结果已保存到: {output_json}")
        
    except Exception as e:
        print(f"处理文件时出错: {str(e)}")
        return

def main():
    # 硬编码输入json路径
    input_json_path = "/Users/liucun/Desktop/nengyuan/601985.SH-中国核电-2024年度可持续发展报告/aligned_clustering.json"
    image_dir = "/Users/liucun/Desktop/nengyuan/601985.SH-中国核电-2024年度可持续发展报告_temp_images"
    process_single_file(input_json_path, image_dir)

if __name__ == "__main__":
    main()
    
