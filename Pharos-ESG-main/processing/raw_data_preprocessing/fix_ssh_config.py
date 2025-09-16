#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to fix and restore SSH configuration file format.
- Backs up the original SSH config file.
- Ensures proper directory structure.
- Writes a corrected SSH configuration for the AutoDL server.
"""

import os
import shutil
from pathlib import Path


def fix_ssh_config():
    """
    Fix SSH configuration file format by backing up the original and
    rewriting with proper settings.
    """
    ssh_config_path = Path.home() / ".ssh" / "config"

    # Backup original config file if it exists
    if ssh_config_path.exists():
        backup_path = ssh_config_path.with_suffix('.config.backup')
        shutil.copy2(ssh_config_path, backup_path)
        print(f"Original configuration file backed up to: {backup_path}")

    # Corrected SSH configuration content
    config_content = """# AutoDL server configuration
Host autodl
    HostName connect.bjb1.seetacloud.com
    Port 14318
    User root
    ServerAliveInterval 60
    ServerAliveCountMax 3
    # If using key authentication, uncomment the line below and specify key path
    # IdentityFile ~/.ssh/id_rsa
"""

    # Ensure .ssh directory exists
    ssh_config_path.parent.mkdir(parents=True, exist_ok=True)

    # Write corrected configuration
    with open(ssh_config_path, 'w', encoding='utf-8') as f:
        f.write(config_content)

    print(f"SSH configuration file has been fixed: {ssh_config_path}")
    print("\nYou can now connect using:")
    print("ssh autodl")
    print("\nOr use the full command:")
    print("ssh -p 14318 root@connect.bjb1.seetacloud.com")


if __name__ == "__main__":
    fix_ssh_config()