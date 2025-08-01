import re
from collections import defaultdict

def is_table_line(line):
    l = line.strip()
    # 只要是html表格、表格的表头、分隔线或表格行都算
    return (
        l.startswith('<table') or
        l.startswith('|') or
        l.startswith('---') or
        ('|' in l and not l.startswith('#'))
    )

def group_by_page_idx(input_md, output_md):
    with open(input_md, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    page_idx_pattern = re.compile(r'<page_idx:(\d+)>')
    grouped = defaultdict(list)  # page_idx -> [content_lines]
    current_idx = None

    for line in lines:
        match = page_idx_pattern.match(line.strip())
        if match:
            current_idx = match.group(1)
        else:
            if current_idx is not None:
                grouped[current_idx].append(line.rstrip())

    # 写入新文件
    with open(output_md, 'w', encoding='utf-8') as f:
        idxs = sorted(grouped, key=lambda x: int(x))
        for idx_i, idx in enumerate(idxs):
            f.write(f'<page_idx:{idx}>' + '\n')
            f.write('[\n')
            f.write('\n')  # 在[后加一个空行
            content_lines = [l for l in grouped[idx] if l.strip() != '']
            i = 0
            while i < len(content_lines):
                l = content_lines[i]
                f.write(l + '\n')
                # 判断是否为图片行，且下一个是表格行，则不加空行
                if (
                    l.strip().startswith('![')
                    and i + 1 < len(content_lines)
                    and is_table_line(content_lines[i + 1])
                ):
                    pass  # 不加空行
                elif i != len(content_lines) - 1:
                    f.write('\n')
                i += 1
            f.write('\n')  # 在]前加一个空行
            f.write(']\n')
            # 分组之间再加一个空行
            if idx_i != len(idxs) - 1:
                f.write('\n')

if __name__ == "__main__":
    # 示例用法
    input_md = "/Users/liucun/Desktop/300529.SZ-健帆生物-2024年度环境,社会及公司治理(ESG)报告/300529.SZ-健帆生物-2024年度环境,社会及公司治理(ESG)报告_preprocessed.md"
    output_md = "/Users/liucun/Desktop/300529.SZ-健帆生物-2024年度环境,社会及公司治理(ESG)报告/grouped.md"
    group_by_page_idx(input_md, output_md) 