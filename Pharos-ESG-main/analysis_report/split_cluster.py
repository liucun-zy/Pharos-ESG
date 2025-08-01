import json
import os
import re
from collections import defaultdict
from urllib.parse import quote

def generate_cross_platform_paths(image_folder_path, image_filename, report_folder_path=None):
    """
    生成跨平台兼容的图片路径
    
    Args:
        image_folder_path: 图片文件夹的完整路径
        image_filename: 图片文件名
        report_folder_path: 报告文件夹的完整路径（可选，用于生成相对路径）
    
    Returns:
        dict: 包含各种格式路径的字典
    """
    # 构建完整图片路径
    image_path = os.path.join(image_folder_path, image_filename)
    image_path = image_path.replace('\\', '/')
    
    # 获取文件夹名称
    image_folder_name = os.path.basename(image_folder_path)
    
    # 生成各种路径格式
    paths = {}
    
    try:
        # 1. Markdown格式（相对路径）
        paths['markdown'] = f"![]({image_folder_name}/{image_filename})"
        
        # 2. 绝对路径的file:// URL
        encoded_abs_path = quote(image_path, safe=':/')
        paths['file_url'] = f"file://{encoded_abs_path}"
        
        # 3. 相对路径（优化逻辑）
        if report_folder_path:
            # 如果提供了报告文件夹路径，使用报告文件夹作为基准
            try:
                relative_path = os.path.relpath(image_path, report_folder_path)
                paths['relative'] = relative_path.replace('\\', '/')
            except:
                # 如果相对路径计算失败，使用简单的相对路径
                paths['relative'] = f"{image_folder_name}/{image_filename}"
        else:
            # 如果没有提供报告文件夹路径，使用简单的相对路径
            paths['relative'] = f"{image_folder_name}/{image_filename}"
        
        # 4. HTTP本地服务器链接
        # 只包含必要的路径部分，不包含上级目录
        if report_folder_path:
            # 检查图片文件夹是否在报告文件夹内部
            # 更精确的检查：确保图片文件夹是报告文件夹的直接子目录
            report_folder_parent = os.path.dirname(image_folder_path)
            if report_folder_parent == report_folder_path:
                # 图片文件夹在报告文件夹内部（如_pages目录）
                report_folder_name = os.path.basename(report_folder_path)
                http_path = quote(f"{report_folder_name}/{image_folder_name}/{image_filename}", safe='/')
            else:
                # 图片文件夹在报告文件夹外部（如_temp_images目录）
                # 直接使用图片文件夹名称
                http_path = quote(f"{image_folder_name}/{image_filename}", safe='/')
            paths['http_url'] = f"http://localhost:8000/{http_path}"
        else:
            # 如果没有报告文件夹路径，使用简单的相对路径
            http_path = quote(f"{image_folder_name}/{image_filename}", safe='/')
            paths['http_url'] = f"http://localhost:8000/{http_path}"
        
    except Exception as e:
        # 如果路径生成失败，使用基本的相对路径
        paths['markdown'] = f"![]({image_folder_name}/{image_filename})"
        paths['relative'] = f"{image_folder_name}/{image_filename}"
        paths['file_url'] = f"file://{image_path}"
        paths['http_url'] = f"http://localhost:8000/{quote(paths['relative'], safe='/')}"
    
    return paths

def extract_metadata_from_filename(file_path):
    """
    从文件路径中提取元数据信息
    
    Args:
        file_path: 文件路径，例如：
        "/path/300497.SZ-富祥药业-2024年度环境、社会及公司治理(ESG)报告_grouped.json"
    
    Returns:
        dict: 包含元数据的字典，包含以下字段：
        - stock_code: 股票代码
        - company_name: 公司名称
        - report_year: 报告年份
        - report_title: 报告标题（完整）
        - report_type: 报告类型（统一为"ESG_Report"）
        - market: 市场（统一为"China"）
        - original_filename: 原始文件名
    """
    # 获取文件名（不含路径和扩展名）
    filename = os.path.splitext(os.path.basename(file_path))[0]
    
    # 移除 _grouped 后缀（如果存在）
    if filename.endswith('_grouped'):
        filename = filename[:-8]
    elif filename.endswith('_vlm'):
        filename = filename[:-4]
    
    # 定义正则表达式模式来解析文件名
    # 支持两种格式:
    # 格式1: 股票代码-公司名称-年份年度报告类型
    # 格式2: 股票代码-公司名称-年份年报告类型
    patterns = [
        r'^([^-]+)-([^-]+)-(\d{4})年度(.+)$',  # 有"年度"的格式
        r'^([^-]+)-([^-]+)-(\d{4})年(.+)$'      # 没有"年度"的格式
    ]
    
    match = None
    has_year_degree = False
    
    for i, pattern in enumerate(patterns):
        match = re.match(pattern, filename)
        if match:
            has_year_degree = (i == 0)  # 第一个模式包含"年度"
            break
    
    if match:
        stock_code = match.group(1).strip()
        company_name = match.group(2).strip()
        report_year = int(match.group(3))
        report_type = match.group(4).strip()
        
        # 构建完整的报告标题
        if has_year_degree:
            report_title = f"{report_year}年度{report_type}"
        else:
            report_title = f"{report_year}年{report_type}"
        
        return {
            "stock_code": stock_code,
            "company_name": company_name,
            "report_year": report_year,
            "report_title": report_title,
            "report_type": "ESG_Report",
            "market": "China",
            "original_filename": os.path.basename(file_path)
        }
    else:
        # 如果无法解析，返回默认值
        return {
            "stock_code": "UNKNOWN",
            "company_name": "未知公司",
            "report_year": None,
            "report_title": "未知报告",
            "report_type": "ESG_Report",
            "market": "China",
            "original_filename": os.path.basename(file_path)
        }

def restore_and_group_by_page(input_path, output_path, image_folder_path):
    with open(input_path, 'r', encoding='utf-8') as f:
        blocks = json.load(f)

    # 先拆分聚类块，保留data_type分配
    flat_blocks = []
    for block in blocks:
        if block.get('data_type', '').startswith('cluster'):
            data_indices = block['data_indices']
            data_list = block['data']
            # 解析data_types为列表
            data_types = []
            if 'data_types' in block and block['data_types']:
                data_types = block['data_types']
            else:
                # cluster[text,image,text] 这种格式
                type_str = block['data_type'][len('cluster['):-1]
                data_types = [t.strip() for t in type_str.split(',')]
            
            # 获取table相关的路径信息
            table_paths = block.get('table_markdown_urls', [])  # 更新字段名
            table_file_urls = block.get('table_file_urls', [])
            table_http_urls = block.get('table_http_urls', [])
            table_relative_paths = block.get('table_relative_paths', [])
            table_index = 0  # 用于跟踪table类型的索引
            
            # 获取image相关的路径信息
            image_paths = block.get('image_markdown_urls', [])  # 更新字段名
            image_file_urls = block.get('image_file_urls', [])
            image_http_urls = block.get('image_http_urls', [])
            image_relative_paths = block.get('image_relative_paths', [])
            
            # 过滤掉data为null的元素
            valid_data = []
            valid_indices = []
            valid_types = []
            
            for i, (idx, data) in enumerate(zip(data_indices, data_list)):
                # 跳过null数据
                if data is None:
                    continue
                    
                valid_data.append(data)
                valid_indices.append(idx)
                dtype = data_types[i] if i < len(data_types) else 'text'
                valid_types.append(dtype)
            
            # 使用过滤后的数据创建块
            image_index = 0  # 用于跟踪图片路径数组的索引
            table_index = 0  # 用于跟踪表格路径数组的索引
            
            for i, (idx, data) in enumerate(zip(valid_indices, valid_data)):
                page_idx, original_reading_order = idx
                dtype = valid_types[i]
                
                # 选择 reading_order 策略：
                # 方案1：保持原始 reading_order（保持与原文档的对应关系）
                reading_order = original_reading_order
                
                # 方案2：重新分配连续的 reading_order（如果需要连续性，取消下面的注释）
                # reading_order = i + 1  # 从1开始的连续编号
                
                block_dict = {
                    "h1": block.get("h1"),
                    "h2": block.get("h2"),
                    "h3": block.get("h3"),
                    "h4": block.get("h4"),
                    "data_type": dtype,
                    "data": data,
                    "reading_order": reading_order,
                    "page_idx": page_idx
                }
                
                # 如果是图片类型，添加image相关路径字段
                if isinstance(dtype, str) and dtype.startswith('image'):
                    # 使用图片索引来获取对应的路径信息
                    if image_index < len(image_paths):
                        block_dict["image_markdown_url"] = image_paths[image_index]
                    if image_index < len(image_file_urls):
                        block_dict["image_file_url"] = image_file_urls[image_index]
                    if image_index < len(image_relative_paths):
                        block_dict["image_relative_path"] = image_relative_paths[image_index]
                    if image_index < len(image_http_urls):
                        block_dict["image_http_url"] = image_http_urls[image_index]
                    image_index += 1  # 处理完一个图片后，索引+1
                    
                # 如果是表格类型，添加table相关路径字段
                elif isinstance(dtype, str) and dtype.startswith('table'):
                    # 使用表格索引来获取对应的路径信息
                    if table_index < len(table_paths):
                        block_dict["table_markdown_url"] = table_paths[table_index]
                    if table_index < len(table_file_urls):
                        block_dict["table_file_url"] = table_file_urls[table_index]
                    if table_index < len(table_relative_paths):
                        block_dict["table_relative_path"] = table_relative_paths[table_index]
                    if table_index < len(table_http_urls):
                        block_dict["table_http_url"] = table_http_urls[table_index]
                    table_index += 1  # 处理完一个表格后，索引+1
                    
                flat_blocks.append(block_dict)
        else:
            # 处理普通块，确保图片和表格字段正确传递
            if 'image_markdown_url' in block:
                # 普通图片块已经有正确的字段名，不需要修改
                pass
            if 'table_markdown_url' in block:
                # 普通表格块已经有正确的字段名，不需要修改
                pass
            flat_blocks.append(block)

    # 按 page_idx 聚合
    page_dict = defaultdict(list)
    for block in flat_blocks:
        page_dict[block['page_idx']].append(block)

    # 删除每个块中的 page_idx 字段
    for page_blocks in page_dict.values():
        for block in page_blocks:
            block.pop('page_idx', None)

    # 按 page_idx 排序，content 内按 reading_order 排序
    result = []
    for page_idx in sorted(page_dict):
        content = sorted(page_dict[page_idx], key=lambda b: b['reading_order'])
        
        # 构建对应的图片路径（多种格式）
        image_filename = f"{page_idx}.jpg"
        
        # 使用跨平台路径生成函数，传递报告文件夹路径
        report_folder_path = os.path.dirname(image_folder_path)
        paths = generate_cross_platform_paths(image_folder_path, image_filename, report_folder_path)
        
        result.append({
            "page_idx": page_idx,
            "page_markdown_url": paths['markdown'],  # Markdown格式的图片链接
            "page_file_url": paths['file_url'],  # 绝对路径file://链接（本机有效）
            "page_relative_path": paths['relative'],  # 系统相对路径
            "page_http_url": paths['http_url'],  # HTTP本地服务器链接
            "content": content
        })

    # 提取元数据
    metadata = extract_metadata_from_filename(output_path)
    
    # 构建最终输出结构，元数据在前
    final_output = {
        "metadata": metadata,
        "pages": result
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(final_output, f, ensure_ascii=False, indent=2)

def display_json_with_images(json_path, image_folder_path):
    """
    在Jupyter中并排显示JSON内容和对应的图片
    """
    import json
    from IPython.display import HTML, Image, display
    import pandas as pd
    
    # 读取JSON文件
    with open(json_path, 'r', encoding='utf-8') as f:
        json_data = json.load(f)
    
    # 检查新的JSON结构
    if "metadata" in json_data and "pages" in json_data:
        metadata = json_data["metadata"]
        data = json_data["pages"]
        
        # 显示元数据信息
        metadata_html = f"""
        <div style="background-color: #e6f3ff; padding: 15px; margin-bottom: 20px; border-radius: 8px; border-left: 4px solid #007acc;">
            <h3 style="margin-top: 0; color: #007acc;">📊 报告元数据</h3>
            <table style="width: 100%; border-collapse: collapse;">
                <tr><td style="font-weight: bold; padding: 5px;">股票代码:</td><td style="padding: 5px;">{metadata.get('stock_code', 'N/A')}</td></tr>
                <tr><td style="font-weight: bold; padding: 5px;">公司名称:</td><td style="padding: 5px;">{metadata.get('company_name', 'N/A')}</td></tr>
                <tr><td style="font-weight: bold; padding: 5px;">报告年份:</td><td style="padding: 5px;">{metadata.get('report_year', 'N/A')}</td></tr>
                <tr><td style="font-weight: bold; padding: 5px;">报告标题:</td><td style="padding: 5px;">{metadata.get('report_title', 'N/A')}</td></tr>
                <tr><td style="font-weight: bold; padding: 5px;">报告类型:</td><td style="padding: 5px;">{metadata.get('report_type', 'N/A')}</td></tr>
                <tr><td style="font-weight: bold; padding: 5px;">市场:</td><td style="padding: 5px;">{metadata.get('market', 'N/A')}</td></tr>
            </table>
        </div>
        """
        display(HTML(metadata_html))
    else:
        # 兼容旧格式
        data = json_data
    
    # 创建HTML表格显示
    html_content = """
    <style>
    .content-table {
        width: 100%;
        border-collapse: collapse;
        margin-bottom: 20px;
    }
    .content-table th {
        background-color: #f2f2f2;
        padding: 12px;
        text-align: center;
        font-weight: bold;
        border: 1px solid #ddd;
    }
    .content-table td {
        padding: 10px;
        border: 1px solid #ddd;
        vertical-align: top;
    }
    .content-cell {
        max-height: 500px;
        overflow-y: auto;
        background-color: #f9f9f9;
    }
    .image-cell {
        text-align: center;
        background-color: #f9f9f9;
    }
    .page-header {
        background-color: #e6f3ff;
        padding: 8px;
        margin-bottom: 10px;
        border-radius: 5px;
        font-weight: bold;
    }
    .content-cell pre {
        margin: 0;
        white-space: pre-wrap;
        font-size: 12px;
        text-align: left;
    }
    img.page-img {
        max-width: 100%;
        max-height: 400px;
        border: 1px solid #ddd;
        border-radius: 5px;
        cursor: zoom-in;
        transition: box-shadow 0.2s;
    }
    .img-modal {
        display: none;
        position: fixed;
        z-index: 9999;
        left: 0; top: 0; width: 100vw; height: 100vh;
        background: rgba(0,0,0,0.7);
        justify-content: center;
        align-items: center;
    }
    .img-modal img {
        max-width: 90vw;
        max-height: 90vh;
        box-shadow: 0 0 20px #fff;
        border-radius: 8px;
        background: #fff;
    }
    .img-modal.active { display: flex; }
    </style>
    """
    
    for item in data:
        page_idx = item['page_idx']
        content = json.dumps(item['content'], ensure_ascii=False, indent=2)
        page_path = item.get('page_file_url', item.get('page_relative_path', ''))
        
        html_content += f"""
        <div class="page-header">📄 Page {page_idx}</div>
        <table class="content-table">
        <tr>
            <th style="width:50%;">页面内容 (JSON格式)</th>
            <th style="width:50%;">页面图片</th>
        </tr>
        <tr>
            <td class="content-cell">
                <pre>{content}</pre>
            </td>
            <td class="image-cell">
                <img class='page-img' src="{page_path}" alt="Page {page_idx}" onclick="showImgModal(this)">
            </td>
        </tr>
        </table>
        <hr style="margin: 30px 0;">
        """
    
    # 添加弹窗和JS
    html_content += """
    <script>
    function showImgModal(img) {
        var modal = document.getElementById('img-modal');
        var modalImg = document.getElementById('img-modal-img');
        modalImg.src = img.src;
        modal.classList.add('active');
    }
    function hideImgModal() {
        var modal = document.getElementById('img-modal');
        modal.classList.remove('active');
    }
    </script>
    <div id="img-modal" class="img-modal" onclick="hideImgModal()">
        <img id="img-modal-img" src="" />
    </div>
    """
    
    display(HTML(html_content))

def test_metadata_extraction():
    """测试元数据提取功能"""
    test_cases = [
        "300497.SZ-富祥药业-2024年度环境、社会及公司治理(ESG)报告_grouped.json",
        "000001.SZ-平安银行-2023年度可持续发展报告_vlm.json",
        "600036.SH-招商银行-2022年度ESG报告.json",
        "BABA.US-阿里巴巴-2024年度环境报告_grouped.json",
        "600720.SH-中交设计-2024年环境、社会与治理报告_grouped.json",  # 新增：没有"年度"的格式
        "601677.SH-明泰铝业-2024年度ESG报告_grouped.json"  # 新增：有"年度"的格式
    ]
    
    print("🧪 元数据提取测试:")
    print("=" * 60)
    
    for filename in test_cases:
        print(f"\n📄 文件名: {filename}")
        metadata = extract_metadata_from_filename(filename)
        for key, value in metadata.items():
            print(f"   {key}: {value}")
        print("-" * 40)

def process_esg_report(report_folder_path, report_name=None):
    """
    处理ESG报告的通用函数
    
    Args:
        report_folder_path: 报告文件夹路径
        report_name: 报告名称（可选，从文件夹名称自动推断）
    """
    if report_name is None:
        report_name = os.path.basename(report_folder_path)
    
    # 构建文件路径
    input_path = os.path.join(report_folder_path, f"{report_name}_vlm.json")
    output_path = os.path.join(report_folder_path, f"{report_name}_grouped.json")
    image_folder_path = os.path.join(report_folder_path, f"{report_name}_pages")
    
    # 检查文件是否存在
    if not os.path.exists(input_path):
        print(f"❌ 输入文件不存在: {input_path}")
        return False
    
    if not os.path.exists(image_folder_path):
        print(f"❌ 图片文件夹不存在: {image_folder_path}")
        return False
    
    print(f"🚀 开始处理: {os.path.basename(input_path)}")
    print(f"📁 输入文件: {input_path}")
    print(f"📁 输出文件: {output_path}")
    print(f"📁 图片文件夹: {image_folder_path}")
    
    try:
        restore_and_group_by_page(input_path, output_path, image_folder_path)
        print(f"✅ 处理完成: {os.path.basename(output_path)}")
        
        # 显示提取的元数据
        with open(output_path, 'r', encoding='utf-8') as f:
            result = json.load(f)
            if "metadata" in result:
                print(f"\n📊 提取的元数据:")
                for key, value in result["metadata"].items():
                    print(f"   {key}: {value}")
        
        return True
        
    except Exception as e:
        print(f"❌ 处理失败: {e}")
        return False

if __name__ == "__main__":
    # 测试元数据提取
    test_metadata_extraction()
    
    # 配置区域 - 修改这里的路径来处理不同的报告
    # ================================================================
    
    # 设置要处理的报告文件夹路径（取消注释其中一行来运行）
    # report_folder = None  # 默认不处理任何报告
    
    # 示例1: 处理富祥药业报告
    # report_folder = "/Users/liucun/Desktop/report_analysis/300497.SZ-富祥药业-2024年度环境、社会及公司治理(ESG)报告"
    
    # 示例2: 处理健帆生物报告
    report_folder = "/Users/liucun/Desktop/yiyao_fuxaing/300497.SZ-富祥药业-2024年度环境、社会及公司治理(ESG)报告"
    # 示例3: 处理兴齐眼药报告
    # report_folder = "/Users/liucun/Desktop/report_analysis/300573.SZ-兴齐眼药-2024年度环境,社会与治理(ESG)报告"
    
    # ================================================================
    
    if report_folder is not None:
        success = process_esg_report(report_folder)
        if success:
            print(f"\n🎉 报告处理成功！")
        else:
            print(f"\n❌ 报告处理失败！")
    else:
        print("💡 请在配置区域指定要处理的报告文件夹路径")
        print("💡 取消注释并设置 report_folder = \"...\" 来运行处理")

# 使用示例（在Jupyter中运行）:
# display_json_with_images(
#     "/Users/liucun/Desktop/report_analysis/300497.SZ-富祥药业-2024年度环境、社会及公司治理(ESG)报告/300497.SZ-富祥药业-2024年度环境、社会及公司治理(ESG)报告_grouped.json",
#     "/Users/liucun/Desktop/report_analysis/300497.SZ-富祥药业-2024年度环境、社会及公司治理(ESG)报告/300497.SZ-富祥药业-2024年度环境、社会及公司治理(ESG)报告_pages"
# ) 