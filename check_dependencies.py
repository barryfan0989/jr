#!/usr/bin/env python3
"""
演唱會通知助手 - 依賴檢查腳本
驗證所有必要的依賴是否已安裝
"""

import sys
import importlib.util

# 定義必需的依賴
REQUIRED_PACKAGES = {
    'flask': 'Flask',
    'flask_cors': 'Flask-CORS',
    'flask_session': 'Flask-Session',
    'werkzeug': 'Werkzeug',
    'requests': 'requests',
    'bs4': 'beautifulsoup4',
    'pandas': 'pandas',
    'openpyxl': 'openpyxl',
    'lxml': 'lxml',
    'playwright': 'playwright',
}

def check_package(module_name, package_name):
    """檢查單個包是否已安裝"""
    spec = importlib.util.find_spec(module_name)
    return spec is not None

def main():
    print("\n" + "="*50)
    print("🎵 演唱會通知助手 - 依賴檢查")
    print("="*50 + "\n")
    
    missing_packages = []
    installed_packages = []
    
    for module_name, package_name in REQUIRED_PACKAGES.items():
        sys.stdout.write(f"檢查 {package_name}... ")
        sys.stdout.flush()
        
        if check_package(module_name, package_name):
            print("✅")
            installed_packages.append(package_name)
        else:
            print("❌")
            missing_packages.append(package_name)
    
    print("\n" + "="*50)
    print(f"✅ 已安裝: {len(installed_packages)}/{len(REQUIRED_PACKAGES)}")
    print("="*50 + "\n")
    
    if missing_packages:
        print("❌ 缺失的依賴:")
        for pkg in missing_packages:
            print(f"  - {pkg}")
        
        print("\n💡 安裝缺失的依賴:")
        print("  pip install -r requirements.txt")
        print()
        return 1
    else:
        print("✅ 所有依賴都已安裝！")
        print("\n🚀 你可以現在啟動應用了：")
        print("  1. python app.py          # 啟動後端")
        print("  2. cd mobile_ui && npm start  # 啟動前端")
        print()
        return 0

if __name__ == '__main__':
    sys.exit(main())
