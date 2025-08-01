"""
API客户端模块

提供统一的API客户端接口，支持：
- DeepSeek API（用于智能标题匹配）
- Qwen VL API（用于图像标题提取）
- 统一的错误处理和重试机制
- 图片压缩和优化
"""

import requests
import base64
import logging
import time
import os
import io
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Tuple
from PIL import Image
from tenacity import retry, stop_after_attempt, wait_exponential

try:
    from .utils import setup_logging
except ImportError:
    from utils import setup_logging


class APIClientBase(ABC):
    """API客户端基类"""
    
    def __init__(self, config: Dict[str, Any], logger: Optional[logging.Logger] = None):
        self.config = config
        self.logger = logger or setup_logging()
        self.api_key = config.get("api_key")
        self.api_url = config.get("api_url")
        self.model = config.get("model")
        self.timeout = config.get("timeout", 60)
        self.max_retries = config.get("max_retries", 3)
        self.retry_delay = config.get("retry_delay", 5)
        
        if not self.api_key:
            raise ValueError("API密钥不能为空")
    
    @abstractmethod
    def call_api(self, messages: List[Dict], **kwargs) -> Dict[str, Any]:
        """调用API的抽象方法"""
        pass
    
    def _make_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """发送HTTP请求"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(
            self.api_url, 
            headers=headers, 
            json=payload, 
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()


class DeepSeekClient(APIClientBase):
    """DeepSeek API客户端"""
    
    # 系统提示词
    SYSTEM_PROMPT_SELECT_TITLE = (
        "你是一个结构化文档标题对齐专家，你的任务是从给定的候选标题列表中，选择最符合目标文本上下文的标题。\n"
        "要求：\n"
        "1. 只能从以下候选里选择一个\n"
        "2. 不要生成新的标题\n"
        "3. 输出格式：选择：<你选的标题>"
    )
    
    SYSTEM_PROMPT_INSERT_POSITION = (
        "你是一个结构化文档分析专家，专门判断标题在非结构化文本中应插入的位置。你的任务是根据目标标题与文档内容的语义、结构、主题关系，判断其最自然、合理的插入位置。\n"
        "判断时需要考虑：\n"
        "1. 语义连贯性：插入后与上下文是否自然衔接\n"
        "2. 结构合理性：是否适合作为新的主题的开始\n"
        "3. 内容相关性：与周围内容的主题是否相关\n"
        "你需要准确判断应将标题插入到哪一行文本之前，或指出当前范围内不适合插入"
    )
    
    def __init__(self, config: Dict[str, Any], logger: Optional[logging.Logger] = None):
        super().__init__(config, logger)
        self.logger.info(f"初始化DeepSeek客户端，模型: {self.model}")
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def call_api(self, messages: List[Dict], **kwargs) -> Dict[str, Any]:
        """
        调用DeepSeek API
        
        Args:
            messages: 消息列表
            **kwargs: 额外参数
        
        Returns:
            API响应
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", 512),
            "temperature": kwargs.get("temperature", 0.1),
        }
        
        try:
            return self._make_request(payload)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                self.logger.warning("达到速率限制，等待重试...")
                time.sleep(self.retry_delay)
                raise
            else:
                self.logger.error(f"DeepSeek API请求失败: {e}")
                raise
    
    def select_title(self, content: str, candidates: List[str], **kwargs) -> Optional[str]:
        """
        从候选标题中选择最佳匹配
        
        Args:
            content: 上下文内容
            candidates: 候选标题列表
            **kwargs: 额外参数
        
        Returns:
            选择的标题
        """
        if not candidates:
            return None
        
        prompt = f"上下文内容：\n{content}\n\n候选标题：\n"
        for i, candidate in enumerate(candidates, 1):
            prompt += f"{i}. {candidate}\n"
        prompt += "\n请选择最符合上下文的标题："
        
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT_SELECT_TITLE},
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = self.call_api(messages, **kwargs)
            result = response["choices"][0]["message"]["content"]
            
            # 解析选择结果
            if "选择：" in result:
                selected = result.split("选择：")[1].strip()
                # 验证选择是否在候选列表中
                for candidate in candidates:
                    if candidate in selected or selected in candidate:
                        return candidate
            
            return None
        except Exception as e:
            self.logger.error(f"标题选择失败: {e}")
            return None
    
    def find_insert_position(self, content: str, target_title: str, **kwargs) -> Optional[int]:
        """
        找到标题的最佳插入位置
        
        Args:
            content: 文档内容
            target_title: 目标标题
            **kwargs: 额外参数
        
        Returns:
            插入位置（行号）
        """
        lines = content.split('\n')
        prompt = f"文档内容：\n{content}\n\n目标标题：{target_title}\n\n请分析应在哪一行之前插入这个标题，或说明不适合插入。"
        
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT_INSERT_POSITION},
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = self.call_api(messages, **kwargs)
            result = response["choices"][0]["message"]["content"]
            
            # 简单的位置解析逻辑（可以根据需要改进）
            import re
            line_match = re.search(r'第(\d+)行', result)
            if line_match:
                return int(line_match.group(1))
            
            # 如果没有明确指定行号，返回None
            return None
        except Exception as e:
            self.logger.error(f"插入位置分析失败: {e}")
            return None


class DeepSeekR1Client(APIClientBase):
    """DeepSeek R1 API客户端 - 专门用于插入未匹配章节标题"""
    
    # 系统提示词 - 专门用于插入位置分析
    SYSTEM_PROMPT_INSERT_POSITION = (
        "你是一个结构化文档分析专家，专门判断标题在非结构化文本中应插入的位置。你的任务是根据目标标题与文档内容的语义、结构、主题关系，判断其最自然、合理的插入位置。\n"
        "判断时需要考虑：\n"
        "1. 语义连贯性：插入后与上下文是否自然衔接\n"
        "2. 结构合理性：是否适合作为新的主题的开始\n"
        "3. 内容相关性：与周围内容的主题是否相关\n"
        "4. 章节逻辑：是否符合文档的整体结构逻辑\n"
        "你需要准确判断应将标题插入到哪一行文本之前，或指出当前范围内不适合插入。\n"
        "输出格式：插入位置：第X行之前（或：不适合插入）"
    )
    
    def __init__(self, config: Dict[str, Any], logger: Optional[logging.Logger] = None):
        super().__init__(config, logger)
        self.logger.info(f"初始化DeepSeek R1客户端，模型: {self.model}")
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def call_api(self, messages: List[Dict], **kwargs) -> Dict[str, Any]:
        """
        调用DeepSeek R1 API
        
        Args:
            messages: 消息列表
            **kwargs: 额外参数
        
        Returns:
            API响应
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", 1024),
            "temperature": kwargs.get("temperature", 0.1),
            "stream": kwargs.get("stream", False)
        }
        
        try:
            return self._make_request(payload)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                self.logger.warning("DeepSeek R1 达到速率限制，等待重试...")
                time.sleep(self.retry_delay)
                raise
            else:
                self.logger.error(f"DeepSeek R1 API请求失败: {e}")
                raise
    
    def find_insert_position(self, content: str, target_title: str, **kwargs) -> Optional[int]:
        """
        找到标题的最佳插入位置
        
        Args:
            content: 文档内容（限制长度以避免过长）
            target_title: 目标标题
            **kwargs: 额外参数
        
        Returns:
            插入位置（行号）
        """
        # 限制内容长度，避免文件名过长错误
        max_content_length = kwargs.get("max_content_length", 5000)
        if len(content) > max_content_length:
            content = content[:max_content_length] + "\n...(内容已截断)"
        
        lines = content.split('\n')
        prompt = f"""文档内容：
{content}

目标标题：{target_title}

请分析这个标题应该插入到文档的哪个位置。考虑以下因素：
1. 语义相关性：标题内容与周围文本的主题关联
2. 结构逻辑：插入位置是否符合文档结构
3. 上下文连贯性：插入后是否自然流畅

请指出具体的插入位置（第几行之前），或说明不适合插入。"""
        
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT_INSERT_POSITION},
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = self.call_api(messages, **kwargs)
            result = response["choices"][0]["message"]["content"]
            
            self.logger.debug(f"DeepSeek R1 插入位置分析结果: {result}")
            
            # 解析插入位置
            import re
            
            # 匹配各种可能的位置表达方式
            patterns = [
                r'第(\d+)行之前',
                r'第(\d+)行',
                r'行(\d+)',
                r'位置[：:](\d+)',
                r'插入[：:]第(\d+)行'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, result)
                if match:
                    line_num = int(match.group(1))
                    # 确保行号在有效范围内
                    if 1 <= line_num <= len(lines) + 1:
                        return line_num
            
            # 如果明确说明不适合插入
            if any(keyword in result for keyword in ["不适合插入", "不建议插入", "无法插入"]):
                self.logger.info(f"DeepSeek R1 判断标题 '{target_title}' 不适合插入")
                return None
            
            # 如果没有明确指定位置，返回None
            self.logger.warning(f"DeepSeek R1 未能解析出明确的插入位置: {result}")
            return None
            
        except Exception as e:
            self.logger.error(f"DeepSeek R1 插入位置分析失败: {e}")
            return None
    
    def analyze_title_context(self, content: str, target_title: str, **kwargs) -> Dict[str, Any]:
        """
        分析标题与内容的上下文关系
        
        Args:
            content: 文档内容
            target_title: 目标标题
            **kwargs: 额外参数
        
        Returns:
            分析结果字典
        """
        prompt = f"""文档内容：
{content}

目标标题：{target_title}

请分析这个标题与文档内容的关系：
1. 相关性评分（1-10分）
2. 最佳插入位置
3. 插入理由
4. 可能的风险或问题

请以JSON格式返回分析结果。"""
        
        messages = [
            {"role": "system", "content": "你是一个文档结构分析专家，请提供详细的分析结果。"},
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = self.call_api(messages, **kwargs)
            result = response["choices"][0]["message"]["content"]
            
            # 尝试解析JSON结果
            try:
                import json
                analysis = json.loads(result)
                return analysis
            except json.JSONDecodeError:
                # 如果不是JSON格式，返回原始文本
                return {"raw_analysis": result}
                
        except Exception as e:
            self.logger.error(f"DeepSeek R1 上下文分析失败: {e}")
            return {"error": str(e)}


class QwenVLClient(APIClientBase):
    """Qwen VL API客户端"""
    
    def __init__(self, config: Dict[str, Any], logger: Optional[logging.Logger] = None):
        super().__init__(config, logger)
        self.max_image_size_mb = config.get("max_image_size_mb", 1.0)
        self.image_quality_reduction = config.get("image_quality_reduction", 5)
        self.logger.info(f"初始化Qwen VL客户端，模型: {self.model}")
    
    def compress_image(self, image_path: str, max_size_mb: Optional[float] = None, 
                      quality_reduction: Optional[int] = None) -> bytes:
        """
        压缩图片到指定大小以下
        
        Args:
            image_path: 图片路径
            max_size_mb: 最大文件大小（MB）
            quality_reduction: 每次压缩的质量减少百分比
        
        Returns:
            压缩后的图片数据
        """
        max_size_mb = max_size_mb or self.max_image_size_mb
        quality_reduction = quality_reduction or self.image_quality_reduction
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
    
    def call_api_with_retry(self, messages: List[Dict], max_retries: Optional[int] = None, 
                           quality_reduction: Optional[int] = None, **kwargs) -> Dict[str, Any]:
        """
        带重试机制的VLM API调用，支持413错误时压缩图片
        
        Args:
            messages: API消息
            max_retries: 最大重试次数
            quality_reduction: 每次压缩的质量减少百分比
            **kwargs: 其他API参数
        
        Returns:
            API响应
        """
        max_retries = max_retries or self.max_retries
        quality_reduction = quality_reduction or self.image_quality_reduction
        retry_count = 0
        last_error = None
        
        while retry_count < max_retries:
            try:
                return self.call_api(messages, **kwargs)
                
            except requests.exceptions.HTTPError as e:
                last_error = e
                if e.response.status_code == 413:  # Request Entity Too Large
                    retry_count += 1
                    if retry_count >= max_retries:
                        self.logger.error(f"图片压缩{max_retries}次后仍然太大，放弃处理")
                        raise last_error
                        
                    self.logger.warning(f"图片太大，正在进行第{retry_count}次压缩尝试（质量减少{quality_reduction}%）")
                    
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
                                                # 压缩图片
                                                compressed_image = self.compress_image(
                                                    temp_path, 
                                                    quality_reduction=quality_reduction
                                                )
                                                # 更新messages中的图片
                                                content_item["image_url"]["url"] = (
                                                    f"data:image/jpeg;base64,"
                                                    f"{base64.b64encode(compressed_image).decode('utf-8')}"
                                                )
                                            finally:
                                                # 清理临时文件
                                                if os.path.exists(temp_path):
                                                    os.remove(temp_path)
                                        except Exception as e:
                                            self.logger.error(f"压缩图片时出错: {str(e)}")
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
    
    def call_api(self, messages: List[Dict], **kwargs) -> Dict[str, Any]:
        """
        调用Qwen VL API
        
        Args:
            messages: 消息列表
            **kwargs: 额外参数
        
        Returns:
            API响应
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", 2048),
            "temperature": kwargs.get("temperature", 0.0),
            "top_p": kwargs.get("top_p", 1.0),
            "n": kwargs.get("n", 1)
        }
        
        return self._make_request(payload)
    
    def extract_titles_from_image(self, image_path: str, sample_base64_files: List[str], 
                                 **kwargs) -> Optional[str]:
        """
        从图片中提取标题结构
        
        Args:
            image_path: 图片文件路径
            sample_base64_files: 示例文件路径列表
            **kwargs: 额外参数
        
        Returns:
            提取的标题JSON字符串
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
            
            # 读取示例图片的Base64编码
            examples = []
            for sample_file in sample_base64_files:
                if os.path.exists(sample_file):
                    with open(sample_file, 'r') as f:
                        examples.append(f.read().strip())
                else:
                    self.logger.warning(f"示例文件不存在: {sample_file}")
            
            # 构造提示词（三个部分）
            prompt_parts = self._build_title_extraction_prompt()
            
            # 构造多模态消息
            messages = self._build_title_extraction_messages(prompt_parts, img_b64, examples)
            
            # 调用API
            response = self.call_api_with_retry(messages, **kwargs)
            
            # 防止频繁请求
            time.sleep(2)
            
            return response["choices"][0]["message"]["content"]
            
        except Exception as e:
            self.logger.error(f"标题提取失败: {e}")
            return None
    
    def _build_title_extraction_prompt(self) -> Tuple[str, str, str]:
        """构建标题提取提示词，返回三个部分"""
        
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
        
        return prompt_text_part1, prompt_text_part2, prompt_text_part3
    
    def _build_title_extraction_messages(self, prompt_parts: Tuple[str, str, str], 
                                        img_b64: str, examples: List[str]) -> List[Dict]:
        """构建标题提取消息"""
        prompt_text_part1, prompt_text_part2, prompt_text_part3 = prompt_parts
        
        content_list = [
            # 提示词第一部分文本
            {
                "type": "text",
                "text": prompt_text_part1
            }
        ]
        
        # 只有在示例图片存在时才添加
        if len(examples) > 1 and examples[1]:  # example2_base64 (sample2base64.txt)
            content_list.extend([
                # 示例图片 1
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{examples[1]}",
                        "detail": "high"
                    }
                },
                # 提示词第二部分文本
                {
                    "type": "text",
                    "text": prompt_text_part2
                }
            ])
        
        if len(examples) > 0 and examples[0]:  # example1_base64 (sample1base64.txt)
            content_list.extend([
                # 示例图片 2
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{examples[0]}",
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
        
        return [{"role": "user", "content": content_list}]


def create_api_client(api_type: str, config: Dict[str, Any], 
                     logger: Optional[logging.Logger] = None) -> APIClientBase:
    """
    创建API客户端的工厂函数
    
    Args:
        api_type: API类型（"deepseek", "deepseek_r1" 或 "qwen"）
        config: 配置字典
        logger: 日志器
    
    Returns:
        API客户端实例
    """
    if api_type.lower() == "deepseek":
        return DeepSeekClient(config, logger)
    elif api_type.lower() == "deepseek_r1":
        return DeepSeekR1Client(config, logger)
    elif api_type.lower() == "qwen":
        return QwenVLClient(config, logger)
    else:
        raise ValueError(f"不支持的API类型: {api_type}") 