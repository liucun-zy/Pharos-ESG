#
import os
import json
from pathlib import Path
from magic_pdf.data.data_reader_writer import FileBasedDataWriter, FileBasedDataReader
from magic_pdf.data.dataset import PymuDocDataset
from magic_pdf.model.doc_analyze_by_custom_model import doc_analyze
from magic_pdf.config.enums import SupportedPdfParseMethod


def process_pdf_to_json(pdf_file_path: str):
    """
    处理PDF文件并生成JSON格式输出
    
    Args:
        pdf_file_path (str): PDF文件的路径
        
    Returns:
        dict: 包含处理结果的字典，包括：
            - content_list: 内容列表JSON
            - json_file_path: JSON文件路径
    """
    try:
        # 使用Path对象处理路径
        pdf_path = Path(pdf_file_path)
        
        # 检查文件扩展名
        if not pdf_path.suffix.lower() == '.pdf':
            raise ValueError(f"不支持的文件类型: {pdf_path.suffix}，只支持PDF文件")
        
        # 检查文件是否存在
        if not pdf_path.exists():
            raise FileNotFoundError(f"文件不存在: {pdf_file_path}")
        
        print(f"开始处理文件: {pdf_path}")
        print(f"文件大小: {pdf_path.stat().st_size} 字节")
        
        # 获取文件名（不含扩展名）
        name_without_suff = pdf_path.stem
        
        # 设置输出目录（保存在PDF同目录下）
        output_dir = str(pdf_path.parent)
        
        # 创建临时目录用于处理
        temp_image_dir = str(pdf_path.parent / f"{name_without_suff}_temp_images")
        os.makedirs(temp_image_dir, exist_ok=True)
        
        # 初始化写入器
        image_writer = FileBasedDataWriter(temp_image_dir)
        md_writer = FileBasedDataWriter(output_dir)
        
        # 读取PDF文件
        print("正在读取PDF文件...")
        reader1 = FileBasedDataReader("")
        pdf_bytes = reader1.read(str(pdf_path))
        print(f"PDF文件读取完成，大小: {len(pdf_bytes)} 字节")
        
        # 创建数据集实例
        print("正在创建数据集实例...")
        ds = PymuDocDataset(pdf_bytes)
        
        # 进行推理
        print("正在进行文档分析...")
        if ds.classify() == SupportedPdfParseMethod.OCR:
            infer_result = ds.apply(doc_analyze, ocr=True)
            pipe_result = infer_result.pipe_ocr_mode(image_writer)
        else:
            infer_result = ds.apply(doc_analyze, ocr=False)
            pipe_result = infer_result.pipe_txt_mode(image_writer)
        
        print("文档分析完成")
        
        # 生成内容列表JSON
        print("正在生成内容列表JSON...")
        image_dir = str(os.path.basename(temp_image_dir))
        content_list = pipe_result.get_content_list(image_dir)
        
        # 设置JSON文件路径
        json_file_path = str(pdf_path.parent / f"{name_without_suff}.json")
        
        # 保存JSON文件
        print(f"正在保存JSON文件到: {json_file_path}")
        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump(content_list, f, ensure_ascii=False, indent=4)
        
        print(f"JSON文件已保存到: {json_file_path}")
        
        # 清理临时图片目录
        if os.path.exists(temp_image_dir):
            import shutil
            try:
                shutil.rmtree(temp_image_dir)
                print(f"已删除临时图片目录: {temp_image_dir}")
            except Exception as e:
                print(f"删除临时图片目录失败: {e}")
        
        return {
            "content_list": content_list,
            "json_file_path": json_file_path
        }
        
    except Exception as e:
        print(f"处理PDF时发生错误: {str(e)}")
        print(f"错误类型: {type(e).__name__}")
        print(f"文件路径: {pdf_file_path}")
        raise


def process_all_pdfs(base_dir="F:\output\single_toc"):
    """
    处理指定目录下所有文件夹中的PDF文件，生成JSON格式
    
    Args:
        base_dir (str): 包含PDF文件的根目录
    """
    base_path = Path(base_dir)
    i = 0
    success_count = 0
    error_count = 0
    
    # 遍历目录下的所有文件夹
    for folder_name in os.listdir(base_path):
        folder_path = base_path / folder_name
        
        # 确保是目录
        if not folder_path.is_dir():
            continue  
        
        # 查找目录中的PDF文件（支持大小写扩展名）
        for file_name in os.listdir(folder_path):
            if file_name.lower().endswith('.pdf'):
                pdf_path = folder_path / file_name
                try:
                    i += 1
                    print(f"正在处理第{i}个文件: {pdf_path}") 
                    result = process_pdf_to_json(str(pdf_path))
                    print(f"处理完成: {pdf_path}")
                    print(f"JSON文件已保存到: {result['json_file_path']}")
                    success_count += 1
                    print("-" * 50)
         
                except Exception as e:
                    error_count += 1
                    print(f"处理第{i}个文件时出错")
                    print(f"处理文件 {pdf_path} 时出错: {str(e)}")
                    print("继续处理下一个文件...")
                    print("-" * 50)
                    continue

        
        # 处理完一个文件夹后显示统计信息
        print(f"当前统计: 成功 {success_count} 个，失败 {error_count} 个")
        print("=" * 50)


if __name__ == '__main__':
    # 处理所有PDF文件
    process_all_pdfs()