"""
Agent Configuration Version Manager (PostgreSQL-ONLY)
=====================================================

Git-like versioning system for agent configurations.
Every change creates a new version, allowing rollback.

100% PostgreSQL - NO SQLite!

Author: Substrate AI Team 💜
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .postgres_manager import PostgresManager

logger = logging.getLogger(__name__)


class AgentVersion:
    """Represents a single version of agent configuration"""
    
    def __init__(
        self,
        version_id: str,
        agent_id: str,
        timestamp: datetime,
        config: Dict[str, Any],
        system_prompt: str,
        memory_blocks: Dict[str, Any],
        change_description: Optional[str] = None,
        parent_version: Optional[str] = None,
        is_current: bool = False
    ):
        self.version_id = version_id
        self.agent_id = agent_id
        self.timestamp = timestamp
        self.config = config
        self.system_prompt = system_prompt
        self.memory_blocks = memory_blocks
        self.change_description = change_description or "No description"
        self.parent_version = parent_version
        self.is_current = is_current
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "version_id": self.version_id,
            "agent_id": self.agent_id,
            "timestamp": self.timestamp.isoformat() if isinstance(self.timestamp, datetime) else self.timestamp,
            "config": self.config,
            "system_prompt": self.system_prompt,
            "memory_blocks": self.memory_blocks,
            "change_description": self.change_description,
            "parent_version": self.parent_version,
            "is_current": self.is_current
        }
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=2)


class VersionManager:
    """
    Manages agent configuration versions in PostgreSQL.
    
    100% PostgreSQL backend!
    
    Features:
    - Auto-versioning on every save
    - Rollback to any previous version
    - Diff between versions
    - Export/import .af files with versions
    """
    
    def __init__(self, postgres_manager: 'PostgresManager'):
        """
        Initialize version manager with PostgreSQL.
        
        Args:
            postgres_manager: PostgresManager instance (REQUIRED!)
        """
        if not postgres_manager:
            raise ValueError("VersionManager requires PostgresManager! No SQLite fallback.")
        
        self.pg = postgres_manager
        logger.info("✅ Version Manager initialized (PostgreSQL-only)")
    
    def create_version(
        self,
        agent_id: str,
        config: Dict[str, Any],
        system_prompt: str,
        memory_blocks: Dict[str, Any],
        change_description: Optional[str] = None
    ) -> AgentVersion:
        """
        Create a new version of agent configuration in PostgreSQL.
        
        Args:
            agent_id: Agent identifier
            config: Model configuration (model, temperature, etc.)
            system_prompt: System prompt text
            memory_blocks: Memory blocks dictionary
            change_description: Description of changes
            
        Returns:
            AgentVersion object
        """
        with self.pg._get_connection() as conn:
            cursor = conn.cursor()
            
            # Get current version (to set as parent)
            cursor.execute("""
                SELECT version_id FROM agent_versions
                WHERE agent_id = %s AND is_current = TRUE
            """, (agent_id,))
            result = cursor.fetchone()
            parent_version = result[0] if result else None
            
            # Generate version ID
            now = datetime.utcnow()
            version_id = f"v_{int(now.timestamp() * 1000)}"
            
            # Unset current version
            cursor.execute("""
                UPDATE agent_versions 
                SET is_current = FALSE 
                WHERE agent_id = %s AND is_current = TRUE
            """, (agent_id,))
            
            # Insert new version
            cursor.execute("""
                INSERT INTO agent_versions (
                    version_id, agent_id, timestamp, config, 
                    system_prompt, memory_blocks, change_description,
                    parent_version, is_current
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, TRUE)
            """, (
                version_id,
                agent_id,
                now,
                json.dumps(config),
                system_prompt,
                json.dumps(memory_blocks),
                change_description,
                parent_version
            ))
            
            cursor.close()
        
        logger.info(f"✅ Version created: {version_id}")
        if change_description:
            logger.info(f"   📝 {change_description}")
        
        return AgentVersion(
            version_id=version_id,
            agent_id=agent_id,
            timestamp=now,
            config=config,
            system_prompt=system_prompt,
            memory_blocks=memory_blocks,
            change_description=change_description,
            parent_version=parent_version,
            is_current=True
        )
    
    def get_current_version(self, agent_id: str) -> Optional[AgentVersion]:
        """Get current active version from PostgreSQL"""
        with self.pg._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT version_id, agent_id, timestamp, config, 
                       system_prompt, memory_blocks, change_description, parent_version
                FROM agent_versions
                WHERE agent_id = %s AND is_current = TRUE
            """, (agent_id,))
            
            result = cursor.fetchone()
            cursor.close()
        
        if not result:
            return None
        
        config = result[3]
        if isinstance(config, str):
            config = json.loads(config)
        
        memory_blocks = result[5]
        if isinstance(memory_blocks, str):
            memory_blocks = json.loads(memory_blocks)
        
        return AgentVersion(
            version_id=result[0],
            agent_id=result[1],
            timestamp=result[2],
            config=config,
            system_prompt=result[4],
            memory_blocks=memory_blocks,
            change_description=result[6],
            parent_version=result[7],
            is_current=True
        )
    
    def get_version(self, version_id: str) -> Optional[AgentVersion]:
        """Get specific version by ID from PostgreSQL"""
        with self.pg._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT version_id, agent_id, timestamp, config, 
                       system_prompt, memory_blocks, change_description, parent_version, is_current
                FROM agent_versions
                WHERE version_id = %s
            """, (version_id,))
            
            result = cursor.fetchone()
            cursor.close()
        
        if not result:
            return None
        
        config = result[3]
        if isinstance(config, str):
            config = json.loads(config)
        
        memory_blocks = result[5]
        if isinstance(memory_blocks, str):
            memory_blocks = json.loads(memory_blocks)
        
        return AgentVersion(
            version_id=result[0],
            agent_id=result[1],
            timestamp=result[2],
            config=config,
            system_prompt=result[4],
            memory_blocks=memory_blocks,
            change_description=result[6],
            parent_version=result[7],
            is_current=result[8]
        )
    
    def list_versions(self, agent_id: str, limit: int = 50) -> List[AgentVersion]:
        """List all versions for an agent (newest first) from PostgreSQL"""
        with self.pg._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT version_id, agent_id, timestamp, config, 
                       system_prompt, memory_blocks, change_description, parent_version, is_current
                FROM agent_versions
                WHERE agent_id = %s
                ORDER BY timestamp DESC
                LIMIT %s
            """, (agent_id, limit))
            
            results = cursor.fetchall()
            cursor.close()
        
        versions = []
        for result in results:
            config = result[3]
            if isinstance(config, str):
                config = json.loads(config)
            
            memory_blocks = result[5]
            if isinstance(memory_blocks, str):
                memory_blocks = json.loads(memory_blocks)
            
            versions.append(AgentVersion(
                version_id=result[0],
                agent_id=result[1],
                timestamp=result[2],
                config=config,
                system_prompt=result[4],
                memory_blocks=memory_blocks,
                change_description=result[6],
                parent_version=result[7],
                is_current=result[8]
            ))
        
        return versions
    
    def rollback_to_version(self, version_id: str) -> AgentVersion:
        """
        Rollback to a specific version.
        Creates a new version based on the old one.
        """
        # Get the target version
        target = self.get_version(version_id)
        if not target:
            raise ValueError(f"Version {version_id} not found")
        
        # Create new version (rollback creates a new version in history)
        return self.create_version(
            agent_id=target.agent_id,
            config=target.config,
            system_prompt=target.system_prompt,
            memory_blocks=target.memory_blocks,
            change_description=f"Rollback to {version_id}"
        )
    
    def get_diff(self, version_id_1: str, version_id_2: str) -> Dict[str, Any]:
        """
        Compare two versions and return differences.
        """
        v1 = self.get_version(version_id_1)
        v2 = self.get_version(version_id_2)
        
        if not v1 or not v2:
            return {"error": "One or both versions not found"}
        
        diff = {
            "version_1": version_id_1,
            "version_2": version_id_2,
            "timestamp_1": v1.timestamp.isoformat() if isinstance(v1.timestamp, datetime) else v1.timestamp,
            "timestamp_2": v2.timestamp.isoformat() if isinstance(v2.timestamp, datetime) else v2.timestamp,
            "changes": {}
        }
        
        # Config differences
        if v1.config != v2.config:
            diff["changes"]["config"] = {
                "old": v1.config,
                "new": v2.config
            }
        
        # System prompt differences
        if v1.system_prompt != v2.system_prompt:
            diff["changes"]["system_prompt"] = {
                "old_length": len(v1.system_prompt),
                "new_length": len(v2.system_prompt),
                "old": v1.system_prompt[:200] + "..." if len(v1.system_prompt) > 200 else v1.system_prompt,
                "new": v2.system_prompt[:200] + "..." if len(v2.system_prompt) > 200 else v2.system_prompt
            }
        
        # Memory block differences
        if v1.memory_blocks != v2.memory_blocks:
            diff["changes"]["memory_blocks"] = {
                "old": v1.memory_blocks,
                "new": v2.memory_blocks
            }
        
        return diff
    
    def export_to_agent_file(self, agent_id: str, output_path: str):
        """
        Export agent configuration to .af file.
        """
        current = self.get_current_version(agent_id)
        if not current:
            raise ValueError(f"No current version found for agent {agent_id}")
        
        agent_data = {
            "agent_id": agent_id,
            "name": "Substrate AI",
            "version": current.version_id,
            "timestamp": current.timestamp.isoformat() if isinstance(current.timestamp, datetime) else current.timestamp,
            "config": current.config,
            "system_prompt": current.system_prompt,
            "memory_blocks": current.memory_blocks
        }
        
        with open(output_path, 'w') as f:
            json.dump(agent_data, f, indent=2)
        
        logger.info(f"✅ Agent exported to {output_path}")
    
    def delete_all_versions(self, agent_id: str) -> int:
        """
        Delete all versions for an agent.
        
        Returns:
            Number of versions deleted
        """
        with self.pg._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT COUNT(*) FROM agent_versions WHERE agent_id = %s
            """, (agent_id,))
            count = cursor.fetchone()[0]
            
            cursor.execute("""
                DELETE FROM agent_versions WHERE agent_id = %s
            """, (agent_id,))
            
            cursor.close()
        
        logger.warning(f"🗑️ Deleted {count} versions for agent {agent_id}")
        return count
