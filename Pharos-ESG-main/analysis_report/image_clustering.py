import json
from typing import List, Dict, Set, Tuple
from pathlib import Path

def process_group(blocks: List[Dict], level: str) -> Tuple[Dict, List[Tuple[int, int]]]:
    """处理一组相关的文本块，返回结果和使用的索引列表"""
    images = []
    texts = []
    text_indices = []  # (page_idx, reading_order)
    data_types = []
    table_paths = []
    
    print(f"\n开始处理 {level} 级别的块: {blocks[0][level] if blocks else 'None'}")
    print(f"该组包含 {len(blocks)} 个块")
    
    for block in blocks:
        idx_tuple = (block['page_idx'], block['reading_order'])
        print(f"处理块: {block['data'][:50]}...")  # 打印每个块的前50个字符
        if block['data'].startswith('!['):  # 图片块
            print(f"找到图片块")
            images.append(block['data'])
            text_indices.append(idx_tuple)
            data_types.append('image')
        else:  # 文本块
            print(f"找到文本: {block['data'][:50]}...")
            texts.append(block['data'])
            text_indices.append(idx_tuple)
            data_types.append(block['data_type'])
        if block['data_type'].startswith('table') and 'table_path' in block:
            table_paths.append(block['table_path'])
    
    print(f"该组包含 {len(images)} 张图片和 {len(texts)} 个文本块")
    
    if images and texts:
        print(f"处理 {len(images)} 张图片和 {len(texts)} 个文本块")
        
        # 保留原始标题信息
        first_block = blocks[0]
        result = {
            'level': level,
            'h1': first_block['h1'],
            'h2': first_block['h2'],
            'h3': first_block['h3'],
            'h4': first_block['h4'],
            'images': images,
            'texts': texts,
            'data_indices': text_indices,
            'data_types': data_types,
            'page_idx': first_block['page_idx']
        }
        if table_paths:
            result['table_paths'] = table_paths
        return result, text_indices
    else:
        if not images:
            print(f"警告: 在 {level} 级别没有找到有效的图片")
        if not texts:
            print(f"警告: 在 {level} 级别没有找到有效的文本")
    return None, []

def process_blocks_by_level(blocks: List[Dict], processed_blocks: Set[Tuple[int, int]]) -> Tuple[List[Dict], List[List[Tuple[int, int]]]]:
    """按层级处理文本块，返回结果和所有使用的索引组合"""
    results = []
    all_index_groups = []  # 存储所有索引组合
    
    print(f"\n开始处理文本块，总数: {len(blocks)}")
    
    # 先按 page_idx 分组
    page_groups = {}
    for block in blocks:
        page_idx = block['page_idx']
        if page_idx not in page_groups:
            page_groups[page_idx] = []
        page_groups[page_idx].append(block)
    
    print(f"找到 {len(page_groups)} 个分组")
    for page_idx, page_blocks in page_groups.items():
        print(f"处理分组: page_idx={page_idx}")
        section_groups = {}
        for block in page_blocks:
            idx_tuple = (page_idx, block['reading_order'])
            if idx_tuple in processed_blocks:
                continue
            key = (block['h1'], block['h2'], block['h3'], block['h4'])
            if key not in section_groups:
                section_groups[key] = []
            section_groups[key].append(block)
            processed_blocks.add(idx_tuple)
        
        # 处理所有分组
        for key, group in section_groups.items():
            print(f"处理分组: h1={key[0]}, h2={key[1]}, h3={key[2]}, h4={key[3]}")
            result, indices = process_group(group, 'h4')
            if result:
                results.append(result)
                all_index_groups.append(indices)
    
    print(f"\n总共处理了 {len(results)} 个分组")
    return results, all_index_groups

def get_ordered_blocks(blocks: List[Dict], index_groups: List[List[Tuple[int, int]]]) -> List[Dict]:
    """根据索引组合顺序获取块，保持原始顺序并插入聚类块"""
    index_to_block = {(block['page_idx'], block['reading_order']): block for block in blocks}
    processed_indices = set()
    for group in index_groups:
        processed_indices.update(group)
    all_indices = set((block['page_idx'], block['reading_order']) for block in blocks)
    unprocessed_indices = sorted(all_indices - processed_indices)
    ordered_blocks = []
    current_index = 0
    
    # 处理每个索引组合
    for group in sorted(index_groups, key=lambda x: min(x)):  # 按组合中最小索引排序
        min_group_index = min(group)
        
        # 添加组合前的单个索引块
        while current_index < len(unprocessed_indices) and unprocessed_indices[current_index] < min_group_index:
            index = unprocessed_indices[current_index]
            if index in index_to_block:
                ordered_blocks.append(index_to_block[index])
            current_index += 1
        
        # 获取聚类块中所有数据的类型和内容
        data_types = []
        data_contents = []
        table_paths = []
        
        for index in group:
            block = index_to_block[index]
            data_types.append(block['data_type'])
            data_contents.append(block['data'])
            if block['data_type'].startswith('table') and 'table_path' in block:
                table_paths.append(block['table_path'])
        
        # 添加聚类块
        cluster_block = {
            'data_indices': group,
            'data': data_contents,
            'data_type': f"cluster[{','.join(data_types)}]",
            'h1': index_to_block[group[0]]['h1'],
            'h2': index_to_block[group[0]]['h2'],
            'h3': index_to_block[group[0]]['h3'],
            'h4': index_to_block[group[0]]['h4'],
            'page_idx': index_to_block[group[0]]['page_idx']
        }
        
        # 如果有表格名称，添加到聚类块中
        if table_paths:
            cluster_block['table_paths'] = table_paths
        
        ordered_blocks.append(cluster_block)
    
    # 添加剩余的单个索引块
    while current_index < len(unprocessed_indices):
        index = unprocessed_indices[current_index]
        if index in index_to_block:
            ordered_blocks.append(index_to_block[index])
        current_index += 1
    
    return ordered_blocks

def process_directory(base_path: str):
    """
    处理目录下的所有_output.json文件
    :param base_path: 基础路径
    """
    base_path = Path(base_path)
    
    # 获取md_files目录
    md_files_dir = base_path / "md_files"
    if not md_files_dir.exists():
        print(f"错误：未找到md_files目录: {md_files_dir}")
        return
    
    print(f"\n开始处理目录: {md_files_dir}")
    
    # 统计信息
    total_files = 0
    processed_files = 0
    failed_files = 0
    
    # 遍历所有子目录
    for report_dir in md_files_dir.iterdir():
        if report_dir.is_dir():
            # 检查目录名称格式
            parts = report_dir.name.split('_')
            if len(parts) < 3:  # 至少需要股票代码、公司名和报告名
                print(f"警告：目录名称格式不正确: {report_dir.name}")
                continue
                
            # 检查第一部分是否为日期（8位数字）
            is_date_format = len(parts[0]) == 8 and parts[0].isdigit()
            
            # 查找_output.json文件
            json_file = next(report_dir.glob("*_output.json"), None)
            
            if not json_file:
                print(f"警告：在 {report_dir} 中未找到_output.json文件")
                continue
            
            total_files += 1
            print(f"\n处理文件: {json_file}")
            
            try:
                # 读取JSON文件
                with open(json_file, 'r', encoding='utf-8') as f:
                    pages = json.load(f)
                print(f"成功读取JSON文件，包含 {len(pages)} 页")
                
                blocks = []
                for page in pages:
                    page_idx = page.get('page_idx', None)
                    for block in page.get('content', []):
                        block['page_idx'] = page_idx
                        blocks.append(block)
                print(f"合并后总块数: {len(blocks)}")
                
                # 用于跟踪已处理的块
                processed_blocks = set()
                
                # 按层级处理文本块
                _, index_groups = process_blocks_by_level(blocks, processed_blocks)
                
                # 获取按原始顺序排列的所有块，并插入聚类块
                ordered_blocks = get_ordered_blocks(blocks, index_groups)
                
                # 设置输出文件路径
                output_json = report_dir / f"{report_dir.name}_clustering.json"
                
                # 保存结果
                with open(output_json, 'w', encoding='utf-8') as f:
                    json.dump(ordered_blocks, f, ensure_ascii=False, indent=2)
                print(f"处理完成，结果已保存到: {output_json}")
                processed_files += 1
                
            except Exception as e:
                print(f"处理文件时出错: {str(e)}")
                failed_files += 1
                continue
    
    # 打印统计信息
    print(f"\n处理完成！统计信息:")
    print(f"- 总文件数: {total_files}")
    print(f"- 成功处理: {processed_files}")
    print(f"- 处理失败: {failed_files}")

def process_single_file(input_file: str):
    """
    处理单个_output.json文件的入口函数
    :param input_file: _output.json文件的完整路径
    :return: bool, 是否处理成功
    """
    try:
        input_file = Path(input_file)
        if not input_file.exists():
            print(f"错误：文件不存在: {input_file}")
            return False
            
        if not input_file.name.endswith('_output.json'):
            print(f"错误：不是目标文件（需要以_output.json结尾）: {input_file}")
            return False
            
        print(f"\n=== 开始处理单个文件 ===")
        print(f"文件路径: {input_file}")
        
        with open(input_file, 'r', encoding='utf-8') as f:
            pages = json.load(f)
        print(f"成功读取JSON文件，包含 {len(pages)} 页")
        
        blocks = []
        for page in pages:
            page_idx = page.get('page_idx', None)
            for block in page.get('content', []):
                block['page_idx'] = page_idx
                blocks.append(block)
        print(f"合并后总块数: {len(blocks)}")
        
        # 用于跟踪已处理的块
        processed_blocks = set()
        
        # 按层级处理文本块
        _, index_groups = process_blocks_by_level(blocks, processed_blocks)
        
        # 获取按原始顺序排列的所有块，并插入聚类块
        ordered_blocks = get_ordered_blocks(blocks, index_groups)
        
        # 设置输出文件路径
        output_json = input_file.parent / f"{input_file.stem.replace('_output', '')}_clustering.json"
        
        # 保存结果
        with open(output_json, 'w', encoding='utf-8') as f:
            json.dump(ordered_blocks, f, ensure_ascii=False, indent=2)
        print(f"处理完成，结果已保存到: {output_json}")
        return True
            
    except Exception as e:
        print(f"处理文件时出错: {str(e)}")
        return False

if __name__ == "__main__":
    # 始终处理硬编码路径
    file_path = "/Users/liucun/Desktop/nengyuan/601985.SH-中国核电-2024年度可持续发展报告/aligned_output.json"
    process_single_file(file_path) 