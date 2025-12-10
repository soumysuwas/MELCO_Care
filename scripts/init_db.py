"""
MELCO-Care Database Initialization Script
Run this to create and seed the database
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from database.seed_data import seed_database


if __name__ == "__main__":
    print("🚀 Initializing MELCO-Care Database...")
    seed_database()
