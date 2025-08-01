#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
优化的OCR处理模块
使用PaddleOCR替换Tesseract，支持CUDA、繁体中文和英文
"""

import os
import sys
import re
import logging
import fitz  # PyMuPDF
from PIL import Image
import io
import numpy as np
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class OptimizedOCR:
    """优化的OCR处理器"""
    
    def __init__(self, use_gpu: bool = True, lang: str = 'ch'):
        """
        初始化OCR处理器
        
        Args:
            use_gpu: 是否使用GPU
            lang: 语言设置 ('ch' for Chinese, 'en' for English, 'ch' for both)
        """
        self.use_gpu = use_gpu
        self.lang = lang
        self.ocr = None
        self._init_ocr()
    
    def _init_ocr(self):
        """初始化PaddleOCR"""
        try:
            from paddleocr import PaddleOCR
            
            # 检测GPU可用性
            if self.use_gpu:
                try:
                    import torch
                    if torch.cuda.is_available():
                        logger.info("✅ 检测到CUDA GPU，启用GPU加速")
                        use_gpu = True
                    else:
                        logger.warning("❌ CUDA不可用，使用CPU模式")
                        use_gpu = False
                except ImportError:
                    logger.warning("❌ PyTorch未安装，使用CPU模式")
                    use_gpu = False
            else:
                use_gpu = False
            
            # 初始化PaddleOCR - 支持中文繁体和英文
            self.ocr = PaddleOCR(
                use_textline_orientation=True,
                lang='ch'  # 中文（包含繁体）
            )
            logger.info(f"✅ PaddleOCR初始化成功 (GPU: {use_gpu})")
            
        except ImportError:
            logger.error("❌ PaddleOCR未安装，请运行: pip install paddlepaddle paddleocr")
            raise
        except Exception as e:
            logger.error(f"❌ PaddleOCR初始化失败: {e}")
            raise
    
    def extract_text_from_page(self, doc: fitz.Document, page_num: int) -> str:
        """从PDF页面提取文本层"""
        try:
            page = doc.load_page(page_num)
            text = page.get_text()
            return text.strip()
        except Exception as e:
            logger.error(f"提取第{page_num + 1}页文本失败: {e}")
            return ""
    
    def ocr_page_image(self, page: fitz.Page, dpi: int = 300) -> str:
        """对PDF页面进行OCR识别"""
        try:
            # 将页面渲染为高分辨率图像
            mat = fitz.Matrix(dpi/72, dpi/72)  # 72是PDF的默认DPI
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("png")
            
            # 使用PaddleOCR识别
            result = self.ocr.ocr(img_data)
            
            if not result or not result[0]:
                return ""
            
            # 提取识别的文本
            text_lines = []
            for line in result[0]:
                if line and len(line) >= 2:
                    text_lines.append(line[1][0])
            
            return "\n".join(text_lines)
            
        except Exception as e:
            logger.error(f"OCR识别失败: {e}")
            return ""

class TOCDetector:
    """目录页检测器"""
    
    def __init__(self):
        # 目录关键词（支持繁体和英文）
        self.toc_keywords = {
            'chinese': [
                '目录', '目錄', '目次', '索引', '章节目录', '章節目錄',
                'table of contents', 'contents', 'index'
            ],
            'english': [
                'table of contents', 'contents', 'index', 'toc',
                'chapter', 'section', 'part', 'appendix', 'references',
                'bibliography', 'glossary'
            ]
        }
        
        # 目录项模式
        self.item_patterns = [
            r'^\s*\d+\.\s+[^\n]+',  # 1. 标题
            r'^\s*\d+\.\d+\.\s+[^\n]+',  # 1.1. 标题
            r'^\s*[一二三四五六七八九十]+[、.]\s+[^\n]+',  # 一、 二、
            r'^\s*[（(][一二三四五六七八九十]+[）)]\s+[^\n]+',  # (一) (二)
            r'^\s*[A-Z][\.\)]\s+[^\n]+',  # A. B. A) B)
            r'^\s*[◎●■◆•·○]\s+[^\n]+',  # 特殊符号
        ]
        
        # 页码模式
        self.page_patterns = [
            r'\.{3,}\s*\d+$',  # ... 数字
            r'\.{3,}\d+$',     # ...数字
            r'\.{2,}\s*\d+$',  # .. 数字
            r'\.{2,}\d+$',     # ..数字
        ]
    
    def is_toc_page(self, text: str) -> bool:
        """
        判断是否为目录页
        
        Args:
            text: 页面文本内容
            
        Returns:
            是否为目录页
        """
        if not text:
            return False
        
        # 转换为小写进行匹配
        text_lower = text.lower()
        
        # 1. 检查是否包含目录关键词
        for keyword in self.toc_keywords['chinese'] + self.toc_keywords['english']:
            if keyword in text_lower:
                return True
        
        # 2. 增强的目录页检测
        return self._enhanced_toc_detection(text)
    
    def _enhanced_toc_detection(self, text: str) -> bool:
        """增强的目录页检测逻辑"""
        if not text:
            return False
        
        lines = text.split('\n')
        toc_indicators = 0
        lines_with_content = 0
        
        # 检查每行是否包含目录特征
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            lines_with_content += 1
            
            # 检查章节编号模式
            if re.search(r'^\d+\.?\s+[A-Za-z\u4e00-\u9fff]', line):
                toc_indicators += 2
            
            # 检查页码模式
            if re.search(r'\.{3,}\s*\d+\s*$', line):
                toc_indicators += 2
            
            # 检查省略号
            if re.search(r'\.{3,}|…{3,}', line):
                toc_indicators += 1
            
            # 检查章节关键词
            chapter_keywords = ['chapter', 'section', 'part', 'appendix', 'references',
                              '章', '節', '部', '篇', '编', '編', '附录', '附錄', '参考文献']
            if any(keyword in line.lower() for keyword in chapter_keywords):
                toc_indicators += 1
            
            # 检查数字-数字模式
            if re.search(r'\d+[\.-]\d+', line):
                toc_indicators += 1
            
            # 检查目录页特有格式
            if re.search(r'^\d+\s+[A-Za-z\u4e00-\u9fff].*\s+\d+$', line):
                toc_indicators += 2
        
        # 排除非目录内容
        non_toc_keywords = ['季度', '年度', '报告', '報告', 'quarter', 'annual', 'report', 
                           '业绩', '業績', '表现', '表現', '良好', '下滑', '恢复']
        if any(keyword in text.lower() for keyword in non_toc_keywords):
            return False
        
        # 判断条件
        if lines_with_content == 0:
            return False
        
        toc_density = toc_indicators / lines_with_content
        
        # 需要更高的密度和更多的特征
        if toc_density > 0.5 and toc_indicators >= 5:
            return True
        
        # 或者有很强的目录特征
        if toc_indicators >= 8:
            return True
        
        return False

class PDFProcessor:
    """PDF处理器"""
    
    def __init__(self, use_gpu: bool = True, max_pages: int = 5):
        """
        初始化PDF处理器
        
        Args:
            use_gpu: 是否使用GPU
            max_pages: 最大检查页数（默认5页）
        """
        self.ocr = OptimizedOCR(use_gpu=use_gpu)
        self.toc_detector = TOCDetector()
        self.max_pages = max_pages
    
    def find_toc_pages(self, pdf_path: str) -> List[int]:
        """
        查找目录页（只查找第一个目录页）
        
        Args:
            pdf_path: PDF文件路径
            
        Returns:
            目录页页码列表（从0开始，只包含第一个找到的目录页）
        """
        try:
            doc = fitz.open(pdf_path)
            total_pages = len(doc)
            check_pages = min(self.max_pages, total_pages)
            
            logger.info(f"开始检查PDF前{check_pages}页...")
            
            for page_num in range(check_pages):
                logger.info(f"检查第{page_num + 1}页...")
                
                # 1. 首先尝试文字层匹配
                text = self.ocr.extract_text_from_page(doc, page_num)
                if text:
                    logger.debug(f"第{page_num + 1}页文本预览: {text[:200]}...")
                
                if self.toc_detector.is_toc_page(text):
                    logger.info(f"通过文字层匹配找到目录页: 第{page_num + 1}页")
                    doc.close()
                    return [page_num]  # 找到第一个目录页就返回
                
                # 2. 如果文字层匹配失败，尝试OCR
                page = doc.load_page(page_num)
                ocr_text = self.ocr.ocr_page_image(page)
                
                if ocr_text and self.toc_detector.is_toc_page(ocr_text):
                    logger.info(f"通过OCR匹配找到目录页: 第{page_num + 1}页")
                    doc.close()
                    return [page_num]  # 找到第一个目录页就返回
            
            doc.close()
            logger.warning(f"在前{check_pages}页中未找到目录页")
            return []
            
        except Exception as e:
            logger.error(f"查找目录页失败: {e}")
            return []
    
    def extract_toc_images(self, pdf_path: str, toc_pages: List[int], output_dir: str) -> List[str]:
        """
        提取目录页图像
        
        Args:
            pdf_path: PDF文件路径
            toc_pages: 目录页页码列表
            output_dir: 输出目录
            
        Returns:
            提取的图像文件路径列表
        """
        try:
            os.makedirs(output_dir, exist_ok=True)
            doc = fitz.open(pdf_path)
            
            image_paths = []
            
            for page_num in toc_pages:
                page = doc.load_page(page_num)
                
                # 高分辨率渲染
                mat = fitz.Matrix(3.0, 3.0)  # 3倍缩放
                pix = page.get_pixmap(matrix=mat)
                
                # 保存为JPG
                image_path = os.path.join(output_dir, f"toc_page_{page_num + 1}.jpg")
                pix.save(image_path)
                
                image_paths.append(image_path)
                logger.info(f"已提取目录页图像: {image_path}")
            
            doc.close()
            return image_paths
            
        except Exception as e:
            logger.error(f"提取目录页图像失败: {e}")
            return []
    
    def remove_toc_pages(self, pdf_path: str, toc_pages: List[int], output_path: str) -> bool:
        """
        从PDF中删除目录页
        
        Args:
            pdf_path: 原PDF文件路径
            toc_pages: 目录页页码列表
            output_path: 输出PDF路径
            
        Returns:
            是否成功
        """
        try:
            doc = fitz.open(pdf_path)
            
            # 删除指定页面
            for page_num in reversed(toc_pages):  # 从后往前删除
                doc.delete_page(page_num)
            
            # 保存新PDF
            doc.save(output_path)
            doc.close()
            
            logger.info(f"已生成去目录PDF: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"删除目录页失败: {e}")
            return False
    
    def process_pdf(self, pdf_path: str, output_dir: str) -> Dict[str, Any]:
        """
        处理单个PDF文件
        
        Args:
            pdf_path: PDF文件路径
            output_dir: 输出目录
            
        Returns:
            处理结果字典
        """
        result = {
            'success': False,
            'toc_pages': [],
            'image_paths': [],
            'output_pdf': '',
            'error': ''
        }
        
        try:
            # 1. 查找目录页
            toc_pages = self.find_toc_pages(pdf_path)
            
            if not toc_pages:
                result['error'] = '未找到目录页'
                return result
            
            # 2. 提取目录页图像
            image_paths = self.extract_toc_images(pdf_path, toc_pages, output_dir)
            
            # 3. 删除目录页并保存新PDF
            pdf_name = Path(pdf_path).stem
            output_pdf = os.path.join(output_dir, f"{pdf_name}_no_toc.pdf")
            
            if self.remove_toc_pages(pdf_path, toc_pages, output_pdf):
                result['success'] = True
                result['toc_pages'] = toc_pages
                result['image_paths'] = image_paths
                result['output_pdf'] = output_pdf
            else:
                result['error'] = '删除目录页失败'
            
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"处理PDF失败: {e}")
        
        return result

def main():
    """主函数 - 硬编码循环处理"""
    # 硬编码路径配置
    input_dir = r"/Users/liucun/Desktop/目录页提取代码/USESG/downloaded_pdfs"  # 输入PDF目录
    output_base_dir = r"/Users/liucun/Desktop/目录页提取代码/processed_pdfs"   # 输出基础目录
    
    # 检查输入目录是否存在
    if not os.path.exists(input_dir):
        logger.error(f"输入目录不存在: {input_dir}")
        return
    
    # 创建输出目录
    success_dir = os.path.join(output_base_dir, "success")
    failed_dir = os.path.join(output_base_dir, "failed")
    os.makedirs(success_dir, exist_ok=True)
    os.makedirs(failed_dir, exist_ok=True)
    
    # 创建处理器
    processor = PDFProcessor(use_gpu=False, max_pages=5)  # 使用CPU模式，只检查前5页
    
    # 统计信息
    total_files = 0
    success_count = 0
    failed_count = 0
    failed_files = []
    
    # 获取所有PDF文件
    pdf_files = [f for f in os.listdir(input_dir) if f.lower().endswith('.pdf')]
    
    if not pdf_files:
        logger.warning(f"在目录 {input_dir} 中未找到PDF文件")
        return
    
    logger.info(f"找到 {len(pdf_files)} 个PDF文件，开始处理...")
    
    # 循环处理每个PDF文件
    for i, pdf_filename in enumerate(pdf_files, 1):
        pdf_path = os.path.join(input_dir, pdf_filename)
        logger.info(f"\n处理进度: {i}/{len(pdf_files)} - {pdf_filename}")
        
        total_files += 1
        
        try:
            # 为每个PDF创建独立的子文件夹
            pdf_name = Path(pdf_filename).stem
            pdf_output_dir = os.path.join(success_dir, pdf_name)
            os.makedirs(pdf_output_dir, exist_ok=True)
            
            # 处理PDF
            result = processor.process_pdf(pdf_path, pdf_output_dir)
            
            if result['success']:
                success_count += 1
                logger.info(f"✅ 成功处理: {pdf_filename}")
                logger.info(f"   目录页: {[p+1 for p in result['toc_pages']]}")
                logger.info(f"   输出目录: {pdf_output_dir}")
            else:
                failed_count += 1
                failed_files.append(pdf_filename)
                logger.warning(f"❌ 处理失败: {pdf_filename} - {result['error']}")
                
                # 复制失败的文件到failed目录
                failed_pdf_dir = os.path.join(failed_dir, pdf_name)
                os.makedirs(failed_pdf_dir, exist_ok=True)
                import shutil
                shutil.copy2(pdf_path, os.path.join(failed_pdf_dir, pdf_filename))
                
        except Exception as e:
            failed_count += 1
            failed_files.append(pdf_filename)
            logger.error(f"❌ 处理异常: {pdf_filename} - {e}")
            
            # 复制异常的文件到failed目录
            pdf_name = Path(pdf_filename).stem
            failed_pdf_dir = os.path.join(failed_dir, pdf_name)
            os.makedirs(failed_pdf_dir, exist_ok=True)
            import shutil
            shutil.copy2(pdf_path, os.path.join(failed_pdf_dir, pdf_filename))
    
    # 生成处理报告
    report_file = os.path.join(output_base_dir, "processing_report.txt")
    try:
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("PDF目录页提取处理报告\n")
            f.write("=" * 50 + "\n")
            f.write(f"处理时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"输入目录: {input_dir}\n")
            f.write(f"输出目录: {output_base_dir}\n")
            f.write(f"总文件数: {total_files}\n")
            f.write(f"成功处理: {success_count}\n")
            f.write(f"处理失败: {failed_count}\n")
            f.write(f"成功率: {success_count/total_files*100:.1f}%\n\n")
            
            if failed_files:
                f.write("失败的文件列表:\n")
                f.write("-" * 30 + "\n")
                for file in failed_files:
                    f.write(f"- {file}\n")
            
            f.write(f"\n输出目录结构:\n")
            f.write(f"- {success_dir}/ - 成功处理的文件（每个PDF一个子文件夹）\n")
            f.write(f"- {failed_dir}/ - 处理失败的原PDF文件\n")
            f.write(f"- {report_file} - 本报告\n")
        
        logger.info(f"📊 处理报告已生成: {report_file}")
        
    except Exception as e:
        logger.error(f"生成报告失败: {e}")
    
    # 打印最终统计
    print("\n" + "="*50)
    print("处理完成！")
    print("="*50)
    print(f"总文件数: {total_files}")
    print(f"成功处理: {success_count}")
    print(f"处理失败: {failed_count}")
    print(f"成功率: {success_count/total_files*100:.1f}%")
    
    print(f"\n输出目录结构:")
    print(f"✅ 成功文件: {success_dir}/")
    print(f"❌ 失败文件: {failed_dir}/")
    print(f"📊 处理报告: {report_file}")
    
    if failed_files:
        print(f"\n失败的文件:")
        for file in failed_files:
            print(f"  - {file}")
    
    print("="*50)

if __name__ == "__main__":
    main() 