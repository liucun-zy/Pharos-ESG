import re
import json

input_md = "/Users/liucun/Desktop/nengyuan/601985.SH-中国核电-2024年度可持续发展报告/aligned_output.md"
output_json = input_md.replace(".md", ".json")

page_re = re.compile(r'^<page_idx[：:]*\[(\d+)\>|^<page_idx[：:](\d+)>')
h1_re = re.compile(r'^# (.*)')
h2_re = re.compile(r'^## (.*)')
h3_re = re.compile(r'^### (.*)')
h4_re = re.compile(r'^#### (.*)')
img_re = re.compile(r'^!\[\]\((.+?)\)$')
table_re = re.compile(r'^<html>.*?<table>.*?</table>.*?</html>', re.DOTALL)

def process_page(lines, page_idx, h1, h2, h3, h4):
    content = []
    reading_order = 0
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i].strip()
        # 标题处理
        if not line:
            i += 1
            continue
        if h1_re.match(line):
            h1 = h1_re.match(line).group(1)
            h2 = h3 = h4 = "null"
            i += 1
            continue
        if h2_re.match(line):
            h2 = h2_re.match(line).group(1)
            h3 = h4 = "null"
            i += 1
            continue
        if h3_re.match(line):
            h3 = h3_re.match(line).group(1)
            h4 = "null"
            i += 1
            continue
        if h4_re.match(line):
            h4 = h4_re.match(line).group(1)
            i += 1
            continue

        # -------- 图片-表格绑定 -----------
        if img_re.match(line):
            j = i + 1
            while j < n and not lines[j].strip():
                j += 1
            if j < n and table_re.match(lines[j].strip()):
                table_data = lines[j].strip()
                content.append({
                    "h1": h1, "h2": h2, "h3": h3, "h4": h4,
                    "data_type": "table",
                    "table_path": line,
                    "data": table_data,
                    "reading_order": reading_order
                })
                reading_order += 1
                i = j + 1
                continue
            else:
                content.append({
                    "h1": h1, "h2": h2, "h3": h3, "h4": h4,
                    "data_type": "image",
                    "data": line,
                    "reading_order": reading_order
                })
                reading_order += 1
                i += 1
                continue

        if table_re.match(line):
            content.append({
                "h1": h1, "h2": h2, "h3": h3, "h4": h4,
                "data_type": "table",
                "data": line,
                "reading_order": reading_order
            })
            reading_order += 1
            i += 1
            continue

        content.append({
            "h1": h1, "h2": h2, "h3": h3, "h4": h4,
            "data_type": "text",
            "data": line,
            "reading_order": reading_order
        })
        reading_order += 1
        i += 1

    # 返回内容和最新标题状态
    return {
        "page_idx": page_idx,
        "content": content
    }, h1, h2, h3, h4

def parse_markdown_file(file_path):
    pages = []
    with open(file_path, "r", encoding="utf-8") as f:
        lines = [line.rstrip('\n') for line in f]
    i = 0
    n = len(lines)
    h1 = h2 = h3 = h4 = "null"  # 全局标题状态
    while i < n:
        line = lines[i].strip()
        page_match = page_re.match(line)
        if page_match:
            page_idx = int(page_match.group(1) or page_match.group(2))
            while i < n and not lines[i].strip().startswith('['):
                i += 1
            if i >= n:
                break
            i += 1  # 跳过 '['
            page_content = []
            while i < n and not lines[i].strip().startswith(']'):
                page_content.append(lines[i])
                i += 1
            i += 1  # 跳过 ']'
            page_result, h1, h2, h3, h4 = process_page(page_content, page_idx, h1, h2, h3, h4)
            pages.append(page_result)
        else:
            i += 1
    return pages

if __name__ == "__main__":
    pages = parse_markdown_file(input_md)
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(pages, f, ensure_ascii=False, indent=2)
    print(f"转换完成，输出文件：{output_json}")