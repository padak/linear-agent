#!/usr/bin/env python3
"""Database initialization script.

Creates SQLite database schema and ensures all tables are ready.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from linear_chief.config import ensure_directories, DATABASE_PATH
from linear_chief.storage import init_db


def main():
    """Initialize database schema."""
    print("Linear Chief of Staff - Database Setup")
    print("=" * 60)

    # Ensure directories exist
    print(f"\n1. Creating directories...")
    ensure_directories()
    print(f"   ✓ Directories created")

    # Initialize database
    print(f"\n2. Initializing database schema...")
    print(f"   Database: {DATABASE_PATH}")

    try:
        init_db()
        print(f"   ✓ Database schema initialized successfully")
    except Exception as e:
        print(f"   ✗ Failed to initialize database: {e}")
        sys.exit(1)

    # Verify database exists
    if DATABASE_PATH.exists():
        size_kb = DATABASE_PATH.stat().st_size / 1024
        print(f"\n3. Verification:")
        print(f"   ✓ Database file exists: {DATABASE_PATH}")
        print(f"   ✓ Size: {size_kb:.2f} KB")
    else:
        print(f"\n3. Verification:")
        print(f"   ✗ Database file not found: {DATABASE_PATH}")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("Database setup complete!")
    print("\nNext steps:")
    print("  1. Configure .env with API keys")
    print("  2. Run: python -m linear_chief test")
    print("  3. Run: python -m linear_chief briefing")


if __name__ == "__main__":
    main()
