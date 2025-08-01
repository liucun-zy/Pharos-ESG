import json
import re

# 硬编码输入输出路径
INPUT_JSON = '/Users/liucun/Desktop/report_analysis/300497.SZ-富祥药业-2024年度环境、社会及公司治理(ESG)报告/300497.SZ-富祥药业-2024年度环境、社会及公司治理(ESG)报告.json'
OUTPUT_MD = '/Users/liucun/Desktop/report_analysis/300497.SZ-富祥药业-2024年度环境、社会及公司治理(ESG)报告/output.md'

def html_table_to_md(html_table: str) -> str:
    """
    将简单的HTML表格转换为Markdown表格。
    仅适用于简单的无嵌套表格。
    """
    # 提取表格行
    rows = re.findall(r'<tr>(.*?)</tr>', html_table, re.S)
    md_rows = []
    for i, row in enumerate(rows):
        # 提取单元格
        cells = re.findall(r'<t[dh]>(.*?)</t[dh]>', row, re.S)
        # 去除HTML标签和多余空白
        cells = [re.sub(r'<.*?>', '', cell).replace('\n', '').strip() for cell in cells]
        md_rows.append(' | '.join(cells))
    if not md_rows:
        return ''
    # 添加分隔行
    if len(md_rows) > 1:
        md_rows.insert(1, ' | '.join(['---'] * len(md_rows[0].split(' | '))))
    return '\n'.join(md_rows)


def json_to_md(objs, output_md_path):
    md_lines = []
    for obj in objs:
        page_idx = obj.get('page_idx', '')
        prefix = f'<page_idx:{page_idx}>'
        if obj['type'] == 'image':
            md_lines.append(prefix)
            md_lines.append(f"{obj['img_path']}")
            md_lines.append('')
            md_lines.append('')
        elif obj['type'] == 'table':
            md_lines.append(prefix)
            md_lines.append(f"{obj['img_path']}")
            table_body = obj.get('table_body', '').replace('\n', '').strip()
            if table_body:
                # 直接保留原始HTML格式
                md_lines.append(prefix)
                md_lines.append(table_body)
            md_lines.append('')
            md_lines.append('')
        elif obj['type'] == 'text':
            text = obj.get('text', '').strip()
            text_level = obj.get('text_level')
            md_lines.append(prefix)
            if text_level:
                md_lines.append(f"{'#' * text_level} {text}")
            else:
                md_lines.append(text)
            md_lines.append('')
            md_lines.append('')
    # 写入Markdown文件
    with open(output_md_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(md_lines).strip() + '\n')


def main():
    # 直接使用硬编码路径
    with open(INPUT_JSON, 'r', encoding='utf-8') as f:
        objs = json.load(f)
    json_to_md(objs, OUTPUT_MD)


if __name__ == '__main__':
    main() 