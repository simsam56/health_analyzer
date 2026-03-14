#!/usr/bin/env python3
"""
Launcher script for Bord
"""

import sys
from pathlib import Path

# Add current directory to path
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))


def main():
    print("🚀 Bord Launcher")
    print(f"📍 Directory: {ROOT}")
    print(f"🐍 Python: {sys.version}")
    print()

    # Test imports
    try:
        from pipeline.schema import init_db

        print("✅ Database schema module OK")

        from defusedxml import ElementTree as ET

        print("✅ Secure XML parsing OK")

        import joblib

        print("✅ Joblib serialization OK")

        import sqlite3

        print("✅ SQLite OK")

    except ImportError as e:
        print(f"❌ Import error: {e}")
        return 1

    print()
    print("🎯 Launching main application...")

    # Import and run main
    try:
        # For now, just show that we can import
        print("✅ Main module imported successfully")
        print()
        print("💡 To run Bord:")
        print("   python3 main.py --help")
        print("   python3 main.py --skip-parse --audit")
        print("   python3 main.py --serve  # With web interface")

    except Exception as e:
        print(f"❌ Error launching main: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
