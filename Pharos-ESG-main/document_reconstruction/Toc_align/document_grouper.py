# document_grouper.py

"""
A utility for preprocessing Markdown files by grouping content based on page index tags.

This script reads a Markdown file containing special tags like '<page_idx:N>',
and reorganizes its content into distinct blocks, each corresponding to a page.
It is designed to handle raw preprocessed files and prepare them for further
analysis by structuring them logically. The script supports batch processing of
all relevant files within a specified directory structure.
"""

import re
import os
from pathlib import Path
from collections import defaultdict
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


def is_table_line(line: str) -> bool:
    """
    Checks if a given line is part of a Markdown or HTML table.

    Args:
        line: The line of text to check.

    Returns:
        True if the line is identified as part of a table, False otherwise.
    """
    line_stripped = line.strip()
    # Identifies HTML table tags, Markdown table headers, separators, or rows.
    return (
        line_stripped.startswith('<table') or
        line_stripped.startswith('|') or
        line_stripped.startswith('---') or
        ('|' in line_stripped and not line_stripped.startswith('#'))
    )


def group_content_by_page_index(input_md_path: str, output_md_path: str):
    """
    Groups content of a Markdown file by page index tags.

    Reads the input file, groups lines under their most recent '<page_idx:N>'
    tag, and writes the structured content to the output file.

    Args:
        input_md_path: Path to the input Markdown file.
        output_md_path: Path where the grouped Markdown file will be saved.
    """
    logging.info(f"Processing file: {Path(input_md_path).name}")

    with open(input_md_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    page_idx_pattern = re.compile(r'<page_idx:(\d+)>')
    grouped_content = defaultdict(list)
    current_page_index = None

    for line in lines:
        match = page_idx_pattern.match(line.strip())
        if match:
            current_page_index = match.group(1)
        elif current_page_index is not None:
            grouped_content[current_page_index].append(line.rstrip())

    # Write the grouped content to the output file
    with open(output_md_path, 'w', encoding='utf-8') as f:
        page_indices = sorted(grouped_content, key=int)
        for i, page_idx in enumerate(page_indices):
            f.write(f'<page_idx:{page_idx}>\n')
            f.write('[\n\n')
            content_lines = [l for l in grouped_content[page_idx] if l.strip()]

            line_idx = 0
            while line_idx < len(content_lines):
                line = content_lines[line_idx]
                f.write(line + '\n')
                # Avoid adding an extra newline between an image and a table
                is_image = line.strip().startswith('![')
                is_followed_by_table = (
                    line_idx + 1 < len(content_lines) and
                    is_table_line(content_lines[line_idx + 1])
                )

                if not (is_image and is_followed_by_table):
                    if line_idx < len(content_lines) - 1:
                        f.write('\n')
                line_idx += 1
            f.write('\n]\n')
            if i < len(page_indices) - 1:
                f.write('\n')

    logging.info(f"Successfully created: {Path(output_md_path).name}")


def find_preprocessed_files(base_path: str) -> list[Path]:
    """
    Finds all preprocessed Markdown files (*_preprocessed.md) in a directory.

    Args:
        base_path: The root directory to search.

    Returns:
        A list of Path objects for the found files.
    """
    return list(Path(base_path).rglob("*_preprocessed.md"))


def batch_process_directory(input_base_path: str):
    """
    Batch processes all preprocessed Markdown files in a directory.

    Args:
        input_base_path: The base directory containing the files to process.
    """
    base_path = Path(input_base_path)

    logging.info("Starting batch process for page grouping...")
    logging.info(f"Input directory: {base_path}")
    print("=" * 80)

    preprocessed_files = find_preprocessed_files(str(base_path))

    if not preprocessed_files:
        logging.warning("No preprocessed Markdown files found.")
        logging.warning("Please check the directory path and file naming convention (*_preprocessed.md).")
        return

    logging.info(f"Found {len(preprocessed_files)} files to process.")
    print("=" * 80)

    total_files = len(preprocessed_files)
    success_count = 0
    failure_count = 0

    for i, input_file in enumerate(preprocessed_files, 1):
        logging.info(f"\n Processing {i}/{total_files}: {input_file.name}")
        try:
            output_file = input_file.parent / "grouped.md"
            group_content_by_page_index(str(input_file), str(output_file))
            success_count += 1
        except Exception as e:
            logging.error(f"Failed to process {input_file.name}: {e}")
            failure_count += 1

    print("\n" + "=" * 80)
    logging.info("Batch processing complete!")
    logging.info(f"Total files: {total_files}")
    logging.info(f"Successful: {success_count}")
    logging.info(f"Failed: {failure_count}")
    if total_files > 0:
        success_rate = (success_count / total_files) * 100
        logging.info(f"Success rate: {success_rate:.1f}%")
    logging.info("All output files ('grouped.md') have been saved in their respective subdirectories.")


if __name__ == "__main__":
    # The base path containing the mineru_output subdirectories
    INPUT_BASE_PATH = r""
    batch_process_directory(INPUT_BASE_PATH)