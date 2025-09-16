#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script for removing empty folders.
This script recursively deletes all empty subfolders under a given directory.
"""

import os
import shutil
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def is_folder_empty(folder_path: str) -> bool:
    """
    Check if a folder is empty.

    Args:
        folder_path (str): The folder path to check.

    Returns:
        bool: True if the folder is empty, False otherwise.
    """
    try:
        if not os.path.exists(folder_path):
            return True

        if not os.path.isdir(folder_path):
            return False

        items = os.listdir(folder_path)
        return len(items) == 0

    except Exception as e:
        logger.error(f"Error occurred while checking folder {folder_path}: {e}")
        return False


def get_short_path(full_path: str, max_length: int = 80) -> str:
    """
    Generate a shortened version of the given path for display.

    Args:
        full_path (str): The original full path.
        max_length (int, optional): Maximum allowed length. Defaults to 80.

    Returns:
        str: A shortened path string.
    """
    if len(full_path) <= max_length:
        return full_path

    parts = full_path.split(os.sep)
    if len(parts) <= 2:
        return full_path

    start_parts = parts[:2]
    end_parts = parts[-2:]

    short_path = os.sep.join(start_parts) + "\\...\\" + os.sep.join(end_parts)
    return short_path


def remove_empty_folders(root_path: str, dry_run: bool = True) -> tuple:
    """
    Recursively remove empty folders under the given root path.

    Args:
        root_path (str): The root directory to scan.
        dry_run (bool, optional): If True, only simulate deletions without
            actually removing folders. Defaults to True.

    Returns:
        tuple: A tuple (count, folders) where count is the number of removed
            folders, and folders is the list of removed folder paths.
    """
    removed_count = 0
    removed_folders = []

    try:
        for root, dirs, _ in os.walk(root_path, topdown=False):
            for dir_name in dirs:
                dir_path = os.path.join(root, dir_name)

                if is_folder_empty(dir_path):
                    short_path = get_short_path(dir_path)
                    if dry_run:
                        logger.info(f"[Dry Run] Would remove empty folder: {short_path}")
                    else:
                        try:
                            shutil.rmtree(dir_path)
                            logger.info(f"Removed empty folder: {short_path}")
                        except Exception as e:
                            logger.error(f"Failed to remove {dir_path}: {e}")
                            continue
                    removed_count += 1
                    removed_folders.append(dir_path)

    except Exception as e:
        logger.error(f"Error occurred during empty folder removal: {e}")

    return removed_count, removed_folders


def main():
    """
    Main entry point for the script.
    Prompts the user for a target directory and removes empty folders.
    """
    root_path = input("Enter the root directory path: ").strip()
    dry_run_input = input("Dry run mode? (y/n, default y): ").strip().lower()
    dry_run = dry_run_input != 'n'

    if not os.path.exists(root_path):
        logger.error("The provided path does not exist.")
        return

    removed_count, removed_folders = remove_empty_folders(root_path, dry_run)

    if dry_run:
        logger.info(f"[Dry Run] Total empty folders found: {removed_count}")
    else:
        logger.info(f"Total empty folders removed: {removed_count}")

    if removed_count > 0:
        logger.info("List of removed folders:")
        for folder in removed_folders:
            logger.info(f" - {folder}")


if __name__ == "__main__":
    main()
