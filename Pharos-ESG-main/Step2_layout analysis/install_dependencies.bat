@echo off
echo ========================================
echo PDF文档分析工具 - 依赖安装脚本
echo ========================================
echo.

:: 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到Python，请先安装Python 3.7+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo Python已安装，版本信息:
python --version
echo.

:: 检查pip是否可用
pip --version >nul 2>&1
if errorlevel 1 (
    echo 错误: pip不可用，请检查Python安装
    pause
    exit /b 1
)

echo pip已可用，版本信息:
pip --version
echo.

:: 升级pip
echo 正在升级pip...
python -m pip install --upgrade pip
echo.

:: 安装依赖包
echo 正在安装依赖包...
echo.

:: 安装基础依赖
echo 安装基础依赖...
pip install pathlib2 typing-extensions
if errorlevel 1 (
    echo 警告: 基础依赖安装失败，继续安装其他依赖...
)

:: 安装图像处理依赖
echo 安装图像处理依赖...
pip install Pillow opencv-python numpy
if errorlevel 1 (
    echo 警告: 图像处理依赖安装失败，继续安装其他依赖...
)

:: 安装PDF处理依赖
echo 安装PDF处理依赖...
pip install PyMuPDF pdf2image
if errorlevel 1 (
    echo 警告: PDF处理依赖安装失败，继续安装其他依赖...
)

:: 安装OCR依赖
echo 安装OCR依赖...
pip install pytesseract easyocr
if errorlevel 1 (
    echo 警告: OCR依赖安装失败，继续安装其他依赖...
)

:: 安装数据处理依赖
echo 安装数据处理依赖...
pip install pandas tqdm requests
if errorlevel 1 (
    echo 警告: 数据处理依赖安装失败，继续安装其他依赖...
)

:: 尝试安装magic_pdf（可能需要特殊安装方式）
echo 尝试安装magic_pdf核心库...
pip install magic_pdf
if errorlevel 1 (
    echo 警告: magic_pdf安装失败，可能需要手动安装
    echo 请参考magic_pdf的官方安装文档
)

echo.
echo ========================================
echo 依赖安装完成！
echo ========================================
echo.

:: 验证安装
echo 正在验证安装...
python -c "import sys; print('Python版本:', sys.version)"
python -c "import pathlib; print('pathlib: 已安装')" 2>nul || echo "pathlib: 未安装"
python -c "import PIL; print('Pillow: 已安装')" 2>nul || echo "Pillow: 未安装"
python -c "import cv2; print('OpenCV: 已安装')" 2>nul || echo "OpenCV: 未安装"
python -c "import fitz; print('PyMuPDF: 已安装')" 2>nul || echo "PyMuPDF: 未安装"
python -c "import magic_pdf; print('magic_pdf: 已安装')" 2>nul || echo "magic_pdf: 未安装"

echo.
echo 如果magic_pdf显示未安装，请手动安装该库
echo 安装完成后，可以运行以下命令测试:
echo python create_jsonandimage.py
echo.
pause 