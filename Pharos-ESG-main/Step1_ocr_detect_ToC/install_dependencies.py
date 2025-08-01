#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安装依赖脚本
安装PaddleOCR和其他必要的包
"""

import os
import sys
import subprocess
import platform

def run_command(command, description):
    """运行命令并显示结果"""
    print(f"\n{description}...")
    print(f"执行命令: {command}")
    
    try:
        result = subprocess.run(command, shell=True, check=True, 
                              capture_output=True, text=True)
        print(f"✅ {description}成功")
        if result.stdout:
            print(f"输出: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description}失败")
        print(f"错误: {e.stderr}")
        return False

def check_python_version():
    """检查Python版本"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print(f"❌ Python版本过低: {version.major}.{version.minor}")
        print("需要Python 3.8或更高版本")
        return False
    print(f"✅ Python版本: {version.major}.{version.minor}.{version.micro}")
    return True

def install_paddlepaddle():
    """安装PaddlePaddle"""
    system = platform.system()
    
    if system == "Darwin":  # macOS
        # 检查是否为Apple Silicon
        if platform.machine() == "arm64":
            print("检测到Apple Silicon Mac，安装MPS版本")
            return run_command(
                "pip install paddlepaddle",
                "安装PaddlePaddle (Apple Silicon)"
            )
        else:
            print("检测到Intel Mac，安装CPU版本")
            return run_command(
                "pip install paddlepaddle",
                "安装PaddlePaddle (Intel Mac)"
            )
    elif system == "Windows":
        return run_command(
            "pip install paddlepaddle",
            "安装PaddlePaddle (Windows)"
        )
    elif system == "Linux":
        return run_command(
            "pip install paddlepaddle",
            "安装PaddlePaddle (Linux)"
        )
    else:
        print(f"❌ 不支持的操作系统: {system}")
        return False

def install_paddleocr():
    """安装PaddleOCR"""
    return run_command(
        "pip install paddleocr",
        "安装PaddleOCR"
    )

def install_other_dependencies():
    """安装其他依赖"""
    dependencies = [
        "PyMuPDF",  # fitz
        "Pillow",   # PIL
        "numpy",
        "pathlib",
        "typing"
    ]
    
    success = True
    for dep in dependencies:
        if not run_command(f"pip install {dep}", f"安装{dep}"):
            success = False
    
    return success

def check_cuda():
    """检查CUDA环境"""
    print("\n检查CUDA环境...")
    
    try:
        import torch
        if torch.cuda.is_available():
            print("✅ CUDA可用")
            print(f"CUDA版本: {torch.version.cuda}")
            print(f"GPU数量: {torch.cuda.device_count()}")
            for i in range(torch.cuda.device_count()):
                gpu_name = torch.cuda.get_device_name(i)
                print(f"GPU {i}: {gpu_name}")
        else:
            print("⚠️  CUDA不可用，将使用CPU模式")
    except ImportError:
        print("⚠️  PyTorch未安装，无法检查CUDA")
        print("建议安装PyTorch以获得更好的性能")
        print("安装命令: pip install torch torchvision torchaudio")

def test_installation():
    """测试安装"""
    print("\n测试安装...")
    
    try:
        from paddleocr import PaddleOCR
        print("✅ PaddleOCR导入成功")
        
        # 测试初始化
        ocr = PaddleOCR(use_textline_orientation=True, lang='ch')
        print("✅ PaddleOCR初始化成功")
        
        import fitz
        print("✅ PyMuPDF导入成功")
        
        import PIL
        print("✅ Pillow导入成功")
        
        print("✅ 所有依赖安装成功！")
        return True
        
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def main():
    """主函数"""
    print("="*50)
    print("PDF目录页提取工具 - 依赖安装脚本")
    print("="*50)
    
    # 检查Python版本
    if not check_python_version():
        sys.exit(1)
    
    # 升级pip
    run_command("python -m pip install --upgrade pip", "升级pip")
    
    # 安装依赖
    success = True
    
    if not install_paddlepaddle():
        success = False
    
    if not install_paddleocr():
        success = False
    
    if not install_other_dependencies():
        success = False
    
    # 检查CUDA
    check_cuda()
    
    # 测试安装
    if success:
        if test_installation():
            print("\n" + "="*50)
            print("🎉 安装完成！")
            print("="*50)
            print("现在可以使用以下命令运行程序:")
            print("python simple_main.py <输入目录> <输出目录> [gpu]")
            print("示例: python simple_main.py USESG/downloaded_pdfs processed_pdfs gpu")
        else:
            print("\n❌ 安装测试失败，请检查错误信息")
            sys.exit(1)
    else:
        print("\n❌ 部分依赖安装失败，请检查错误信息")
        sys.exit(1)

if __name__ == "__main__":
    main() 