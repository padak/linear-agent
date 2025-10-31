#!/usr/bin/env python3
"""Integration test for memory layer (mem0 + ChromaDB + embeddings)."""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from linear_chief.config import ensure_directories
from linear_chief.memory import MemoryManager, IssueVectorStore


async def test_memory_layer():
    """Test mem0 and ChromaDB integration."""
    print("🧠 Memory Layer Integration Test\n")

    # Ensure directories exist
    ensure_directories()
    print("✓ Directories created\n")

    # Test 1: MemoryManager (mem0)
    print("1️⃣ Testing MemoryManager (mem0)...")
    try:
        memory = MemoryManager()
        
        # Add briefing context
        await memory.add_briefing_context(
            "Test briefing: Found 5 issues, 2 blocked, 1 urgent",
            metadata={"issue_count": 5}
        )
        print("   ✓ Added briefing context")
        
        # Add user preference
        await memory.add_user_preference(
            "Focus on P0 and blocked issues",
            metadata={"category": "priority"}
        )
        print("   ✓ Added user preference")
        
        # Retrieve context
        context = await memory.get_agent_context(days=7)
        print(f"   ✓ Retrieved {len(context)} context items")
        
        # Retrieve preferences
        prefs = await memory.get_user_preferences()
        print(f"   ✓ Retrieved {len(prefs)} preferences")
        
        print("   ✅ MemoryManager working!\n")
        
    except Exception as e:
        print(f"   ❌ MemoryManager error: {e}\n")
        return False

    # Test 2: IssueVectorStore (ChromaDB + embeddings)
    print("2️⃣ Testing IssueVectorStore (ChromaDB + embeddings)...")
    try:
        store = IssueVectorStore()
        
        # Add sample issues
        sample_issues = [
            {
                "id": "PROJ-101",
                "title": "Fix authentication bug in login",
                "description": "Users cannot log in with valid credentials",
            },
            {
                "id": "PROJ-102", 
                "title": "Add user authentication to API",
                "description": "Implement JWT auth for API endpoints",
            },
            {
                "id": "PROJ-103",
                "title": "Refactor database schema",
                "description": "Optimize database indexes for performance",
            },
        ]
        
        print("   📝 Adding issues to vector store...")
        for issue in sample_issues:
            await store.add_issue(
                issue_id=issue["id"],
                title=issue["title"],
                description=issue["description"],
                metadata={"test": True}
            )
        print(f"   ✓ Added {len(sample_issues)} issues")
        
        # Get stats
        stats = store.get_stats()
        print(f"   ✓ Vector store has {stats['total_issues']} issues")
        print(f"   ✓ Using model: {stats['embedding_model']}")
        
        # Test semantic search
        print("\n   🔍 Testing semantic search...")
        results = await store.search_similar("authentication problems", limit=2)
        print(f"   ✓ Found {len(results)} similar issues:")
        for r in results:
            print(f"      - {r['issue_id']}: {r['document'][:50]}...")
        
        # Test embedding retrieval
        embedding = await store.get_issue_embedding("PROJ-101")
        print(f"   ✓ Retrieved embedding vector (dim={len(embedding)})")
        
        print("   ✅ IssueVectorStore working!\n")
        
    except Exception as e:
        print(f"   ❌ IssueVectorStore error: {e}\n")
        import traceback
        traceback.print_exc()
        return False

    print("✅ All memory layer tests passed!\n")
    print("Memory features ready:")
    print("  • Briefing context storage (mem0)")
    print("  • User preference learning")
    print("  • Issue embeddings (sentence-transformers)")
    print("  • Semantic search (ChromaDB)")
    print("  • Persistent storage")
    
    return True


if __name__ == "__main__":
    success = asyncio.run(test_memory_layer())
    sys.exit(0 if success else 1)
