#用于只创建json和图片，不生成md

import os
import json
from pathlib import Path
import traceback

from magic_pdf.data.data_reader_writer import FileBasedDataWriter, FileBasedDataReader
from magic_pdf.data.dataset import PymuDocDataset
from magic_pdf.model.doc_analyze_by_custom_model import doc_analyze
from magic_pdf.config.enums import SupportedPdfParseMethod

def process_pdf(pdf_file_path, output_base_dir="E:\ESGdata\md_jpg"):
    """
    处理PDF文件并生成JSON和图片输出
    
    Args:
        pdf_file_path (str): PDF文件的路径
        output_base_dir (str): 输出文件的基础目录
        
    Returns:
        dict: 包含处理结果的字典，包括：
            - model_inference_result: 模型推理结果
            - content_list: 内容列表JSON
            - output_files: 输出文件路径字典
    """
    try:
        # 使用Path对象处理路径
        pdf_path = Path(pdf_file_path)
        pdf_dir_name = pdf_path.parent.name
        
        # 设置输出目录
        local_md_dir = str(pdf_path.parent)  # JSON文件保存在PDF同目录
        local_image_dir = str(Path(output_base_dir) / "md_jpg" / pdf_dir_name)  # 图片保存在指定目录
        
        # 获取文件名（不含扩展名）
        name_without_suff = pdf_path.stem
        
        # 创建输出目录
        os.makedirs(local_image_dir, exist_ok=True)
        
        # 初始化数据写入器
        image_writer, md_writer = FileBasedDataWriter(local_image_dir), FileBasedDataWriter(local_md_dir)
        
        # 读取PDF文件
        reader1 = FileBasedDataReader("")
        pdf_bytes = reader1.read(str(pdf_path))
        
        # 创建数据集实例
        ds = PymuDocDataset(pdf_bytes)
        
        # 根据PDF类型进行推理
        if ds.classify() == SupportedPdfParseMethod.OCR:
            infer_result = ds.apply(doc_analyze, ocr=True)
            pipe_result = infer_result.pipe_ocr_mode(image_writer)
        else:
            infer_result = ds.apply(doc_analyze, ocr=False)
            pipe_result = infer_result.pipe_txt_mode(image_writer)
        
        # 获取结果
        model_inference_result = infer_result.get_infer_res()
        
        # 生成内容列表JSON
        image_dir = str(os.path.basename(local_image_dir))
        content_list = pipe_result.get_content_list(image_dir)
        
        # 设置JSON文件路径
        json_file_path = str(pdf_path.parent / f"{name_without_suff}.json")
        
        # 保存JSON文件
        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump(content_list, f, ensure_ascii=False, indent=4)
        
        # 注释掉MD生成部分
        # md_content = pipe_result.get_markdown(os.path.basename(local_image_dir))
        # pipe_result.dump_md(md_writer, f"{name_without_suff}.md", os.path.basename(local_image_dir))
        
        # 返回处理结果
        return {
            "model_inference_result": model_inference_result,
            "content_list": content_list,
            "output_files": {
                "json": json_file_path,
                "images_dir": local_image_dir
            }
        }
    except Exception as e:
        print(f"处理PDF时发生错误: {str(e)}")
        print(f"错误详情: {traceback.format_exc()}")
        raise

def process_all_pdfs(base_dir="E:\ESGdata\success"):
    """
    处理指定目录下所有文件夹中的PDF文件
    
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
        
        # 查找目录中的PDF文件
        for file_name in os.listdir(folder_path):
            if file_name.lower().endswith('.pdf'):
                pdf_path = folder_path / file_name
                try:
                    i += 1
                    print(f"正在处理第{i}个文件: {pdf_path}")
                    result = process_pdf(str(pdf_path))
                    print(f"处理完成: {pdf_path}")
                    print(f"JSON文件已保存到: {result['output_files']['json']}")
                    print(f"图片目录: {result['output_files']['images_dir']}")
                    success_count += 1
                    print("-" * 50)
         
                except Exception as e:
                    error_count += 1
                    print(f"处理第{i}个文件时出错")
                    print(f"处理文件 {pdf_path} 时出错: {str(e)}")
                    print(f"错误详情: {traceback.format_exc()}")
                    print("继续处理下一个文件...")
                    print("-" * 50)
                    continue
        
        # 处理完一个文件夹后显示统计信息
        print(f"当前统计: 成功 {success_count} 个，失败 {error_count} 个")
        print("=" * 50)

if __name__ == "__main__":
    # 处理所有PDF文件
    process_all_pdfs()



