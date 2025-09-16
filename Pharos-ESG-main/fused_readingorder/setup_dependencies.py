#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dependency Setup Script for Fused Reading Order Modeling.

This script helps install and update the required dependencies
to resolve version conflicts and missing packages.
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors."""
    print(f"\n{description}...")
    print(f"Command: {command}")
    
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            check=True, 
            capture_output=True, 
            text=True
        )
        print(f"✓ Success: {description}")
        if result.stdout:
            print(f"Output: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed: {description}")
        print(f"Error: {e.stderr.strip()}")
        return False

def check_python_version():
    """Check if Python version is compatible."""
    version = sys.version_info
    print(f"Python version: {version.major}.{version.minor}.{version.micro}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("Python 3.8+ is required")
        return False
    
    print("✓ Python version is compatible")
    return True

def update_pip():
    """Update pip to latest version."""
    return run_command(
        f"{sys.executable} -m pip install --upgrade pip",
        "Updating pip"
    )

def install_pytorch():
    """Install PyTorch with appropriate configuration."""
    # Check if CUDA is available
    try:
        import torch
        if torch.cuda.is_available():
            print("✓ PyTorch with CUDA already installed")
            return True
    except ImportError:
        pass
    
    # Install CPU version for compatibility
    return run_command(
        f"{sys.executable} -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu",
        "Installing PyTorch (CPU version)"
    )

def fix_transformers():
    """Fix transformers and tokenizers version conflict."""
    commands = [
        (f"{sys.executable} -m pip uninstall -y transformers tokenizers", "Uninstalling conflicting packages"),
        (f"{sys.executable} -m pip install transformers>=4.33.0", "Installing compatible transformers"),
    ]
    
    for command, description in commands:
        if not run_command(command, description):
            return False
    return True

def install_core_dependencies():
    """Install core dependencies."""
    dependencies = [
        "numpy>=1.24.0",
        "opencv-python>=4.8.0",
        "Pillow>=10.0.0",
        "sentence-transformers>=2.2.0",
        "huggingface-hub>=0.16.0",
        "scipy>=1.11.0",
        "scikit-learn>=1.3.0",
    ]
    
    for dep in dependencies:
        if not run_command(
            f"{sys.executable} -m pip install '{dep}'",
            f"Installing {dep}"
        ):
            print(f"⚠ Warning: Failed to install {dep}, continuing...")
    
    return True

def install_optional_dependencies():
    """Install optional dependencies for enhanced functionality."""
    optional_deps = [
        "pandas>=2.0.0",
        "matplotlib>=3.7.0",
        "seaborn>=0.12.0",
        "tqdm>=4.65.0",
        "rich>=13.5.0",
    ]
    
    print("\nInstalling optional dependencies...")
    for dep in optional_deps:
        run_command(
            f"{sys.executable} -m pip install '{dep}'",
            f"Installing {dep} (optional)"
        )

def verify_installation():
    """Verify that all dependencies are properly installed."""
    print("\n=== Verifying Installation ===")
    
    tests = [
        ("import torch; print(f'PyTorch: {torch.__version__}')", "PyTorch"),
        ("import transformers; print(f'Transformers: {transformers.__version__}')", "Transformers"),
        ("import sentence_transformers; print(f'Sentence Transformers: {sentence_transformers.__version__}')", "Sentence Transformers"),
        ("import numpy; print(f'NumPy: {numpy.__version__}')", "NumPy"),
        ("import cv2; print(f'OpenCV: {cv2.__version__}')", "OpenCV"),
        ("import PIL; print(f'Pillow: {PIL.__version__}')", "Pillow"),
    ]
    
    success_count = 0
    for test_code, name in tests:
        try:
            result = subprocess.run(
                [sys.executable, "-c", test_code],
                capture_output=True,
                text=True,
                check=True
            )
            print(f"✓ {result.stdout.strip()}")
            success_count += 1
        except subprocess.CalledProcessError:
            print(f"{name}: Not available")
    
    print(f"\nVerification complete: {success_count}/{len(tests)} packages working")
    return success_count == len(tests)

def create_test_script():
    """Create a test script to verify the installation."""
    test_script = '''
#!/usr/bin/env python3
# Test script for fused reading order dependencies

def test_imports():
    """Test all required imports."""
    try:
        print("Testing imports...")
        
        import torch
        print(f"✓ PyTorch {torch.__version__}")
        
        import transformers
        print(f"✓ Transformers {transformers.__version__}")
        
        try:
            import sentence_transformers
            print(f"✓ Sentence Transformers {sentence_transformers.__version__}")
        except ImportError:
            print("⚠ Sentence Transformers not available (will use fallback)")
        
        import numpy as np
        print(f"✓ NumPy {np.__version__}")
        
        import cv2
        print(f"✓ OpenCV {cv2.__version__}")
        
        from PIL import Image
        print(f"✓ Pillow {Image.__version__}")
        
        print("\n✓ All core dependencies are working!")
        return True
        
    except ImportError as e:
        print(f"Import error: {e}")
        return False

def test_basic_functionality():
    """Test basic functionality."""
    try:
        print("\nTesting basic functionality...")
        
        # Test layout analysis
        from layout import DocumentElement, BoundingBox, LayoutAnalyzer
        
        elements = [
            DocumentElement(1, "Test", BoundingBox(0, 0, 100, 50), "text"),
            DocumentElement(2, "Test 2", BoundingBox(0, 60, 100, 110), "text"),
        ]
        
        analyzer = LayoutAnalyzer()
        layout_type, region_tree = analyzer.analyze_layout(elements)
        
        print(f"✓ Layout analysis working: {layout_type.value}")
        
        print("\n✓ Basic functionality test passed!")
        return True
        
    except Exception as e:
        print(f" Functionality test failed: {e}")
        return False

if __name__ == "__main__":
    print("=== Fused Reading Order Dependency Test ===")
    
    imports_ok = test_imports()
    functionality_ok = test_basic_functionality()
    
    if imports_ok and functionality_ok:
        print("\n All tests passed! You can now run the full demo.")
        print("Run: python demo.py")
    else:
        print("\n Some tests failed. Please check the installation.")
        print("Run: python setup_dependencies.py")
'''
    
    with open("test_installation.py", "w") as f:
        f.write(test_script)
    
    print("✓ Created test_installation.py")

def main():
    """Main setup function."""
    print("=== Fused Reading Order Dependency Setup ===")
    print("This script will install and update required dependencies.")
    print()
    
    # Check Python version
    if not check_python_version():
        return False
    
    # Update pip
    if not update_pip():
        print("⚠ Warning: Failed to update pip, continuing...")
    
    # Install PyTorch
    if not install_pytorch():
        print(" Failed to install PyTorch")
        return False
    
    # Fix transformers version conflict
    if not fix_transformers():
        print(" Failed to fix transformers")
        return False
    
    # Install core dependencies
    if not install_core_dependencies():
        print(" Failed to install core dependencies")
        return False
    
    # Install optional dependencies
    install_optional_dependencies()
    
    # Verify installation
    if verify_installation():
        print("\n Setup completed successfully!")
        
        # Create test script
        create_test_script()
        
        print("\nNext steps:")
        print("1. Test installation: python test_installation.py")
        print("2. Run simplified demo: python simple_demo.py")
        print("3. Run full demo: python demo.py")
        
        return True
    else:
        print("\n Setup completed with some issues.")
        print("You can still try running the simplified demo: python simple_demo.py")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)