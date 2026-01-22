#!/usr/bin/env python3
"""
Setup Script: Import ALEX Example Agent (PostgreSQL-ONLY)

This script automatically imports the ALEX example agent on first setup.
Run this after installing dependencies and configuring your .env file.

100% PostgreSQL - NO SQLite!
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.postgres_manager import create_postgres_manager_from_env
from core.state_manager import StateManager
from tools.agent_file_importer import AgentFileImporter
from core.version_manager import VersionManager


def setup_alex_agent():
    """Import ALEX agent if not already loaded (PostgreSQL-only!)"""
    
    print("\n" + "="*60)
    print("🤖 SETTING UP ALEX AGENT (PostgreSQL)")
    print("="*60 + "\n")
    
    # Initialize PostgreSQL manager (REQUIRED!)
    postgres_manager = create_postgres_manager_from_env()
    if not postgres_manager:
        print("❌ PostgreSQL is REQUIRED! Configure .env and ensure PostgreSQL is running.")
        print("   Required env vars: POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER")
        sys.exit(1)
    
    print("✅ PostgreSQL connected!")
    
    # Initialize state manager (PostgreSQL-backed)
    state_manager = StateManager(postgres_manager=postgres_manager)
    
    # Check if agent already exists in PostgreSQL
    agents = postgres_manager.get_all_agents()
    if agents:
        print(f"✅ Agent(s) already configured in PostgreSQL:")
        for agent in agents:
            print(f"   • {agent.name} (ID: {agent.id})")
        print("   Skipping import...")
        return
    
    # Find ALEX agent file
    script_dir = Path(__file__).parent
    alex_file = script_dir.parent / "examples" / "agents" / "alex.af"
    
    if not alex_file.exists():
        print(f"⚠️  ALEX agent file not found: {alex_file}")
        print("   Skipping import...")
        return
    
    print(f"📦 Importing ALEX agent from: {alex_file}")
    
    # Import agent
    try:
        version_manager = VersionManager(postgres_manager=postgres_manager)
        importer = AgentFileImporter(
            state_manager=state_manager,
            version_manager=version_manager,
            postgres_manager=postgres_manager
        )
        result = importer.import_agent(str(alex_file))
        
        print(f"\n✅ ALEX agent imported to PostgreSQL!")
        print(f"   • Agent ID: {result['agent_id']}")
        print(f"   • Messages imported: {result['messages_imported']}")
        print(f"   • Version: {result['version_id']}")
        
    except Exception as e:
        print(f"\n❌ Error importing ALEX agent: {e}")
        print("   You can import it manually later:")
        print(f"   python tools/agent_file_importer.py {alex_file}")
        return
    
    print("\n" + "="*60)
    print("🎉 SETUP COMPLETE!")
    print("="*60)
    print("\nYou can now start the server:")
    print("  python api/server.py")
    print("\nThen open http://localhost:5173 in your browser to chat with ALEX!")
    print()


if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    setup_alex_agent()
