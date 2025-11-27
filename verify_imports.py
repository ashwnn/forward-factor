"""Verification script for dependency upgrades.

Run this script after installing the new requirements to verify that
Pydantic and FastAPI import correctly without errors.
"""
import sys
import importlib.metadata

def verify_imports():
    print("Verifying imports...")
    
    try:
        import pydantic
        print(f"✅ Pydantic imported successfully (version: {pydantic.__version__})")
    except ImportError as e:
        print(f"❌ Failed to import Pydantic: {e}")
    except AttributeError as e:
        print(f"❌ Pydantic AttributeError (Compatibility Issue): {e}")
        
    try:
        import fastapi
        print(f"✅ FastAPI imported successfully (version: {fastapi.__version__})")
    except ImportError as e:
        print(f"❌ Failed to import FastAPI: {e}")
        
    try:
        import sqlalchemy
        print(f"✅ SQLAlchemy imported successfully (version: {sqlalchemy.__version__})")
    except ImportError as e:
        print(f"❌ Failed to import SQLAlchemy: {e}")

    try:
        import pytest
        print(f"✅ Pytest imported successfully (version: {pytest.__version__})")
    except ImportError as e:
        print(f"❌ Failed to import Pytest: {e}")

if __name__ == "__main__":
    verify_imports()
