#!/usr/bin/env python3
"""
Graph RAG (Retrieval-Augmented Generation)

Uses graph traversal to find relevant context instead of pure vector search.
Inspired by Recall.ai's "Augmented Browsing" but for chat context.
"""

import re
from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict

from core.state_manager import StateManager
from core.memory_system import MemorySystem
from core.consciousness_broadcast import broadcast_consciousness_event


@dataclass
class GraphContext:
    """Context retrieved via graph traversal"""
    nodes: List[Dict]  # Relevant nodes found
    edges: List[Dict]  # Relevant edges
    content: str  # Formatted text for LLM context
    relevance_score: float  # 0-1 how relevant
    path_description: str  # How we found this


class GraphRAG:
    """
    Graph-based Retrieval-Augmented Generation
    
    Uses knowledge graph structure to find relevant context.
    Better than pure vector search because it understands relationships!
    """
    
    def __init__(self, postgres_manager=None, state_manager=None, memory_system=None):
        if not postgres_manager:
            raise ValueError("PostgresManager is REQUIRED for GraphRAG!")
        self.postgres_manager = postgres_manager
        self.state_manager = state_manager
        self.memory_system = memory_system
    
    def extract_entities(self, query: str) -> Dict[str, List[str]]:
        """
        Extract potential entities from query.
        
        Returns:
            {
                'people': ['user', 'assistant'],
                'tags': ['coding', 'food'],
                'concepts': ['love', 'memory']
            }
        """
        query_lower = query.lower()
        
        entities = {
            'people': [],
            'tags': [],
            'concepts': []
        }
        
        # Known people
        people_names = ['user', 'assistant', 'agent']
        for name in people_names:
            if name in query_lower:
                entities['people'].append(name)
        
        # Extract hashtags
        hashtags = re.findall(r'#(\w+)', query_lower)
        entities['tags'].extend(hashtags)
        
        # Common concepts (expandable!)
        concepts = ['love', 'coding', 'memory', 'food', 'work', 'art', 
                   'music', 'relationship', 'trust', 'boundaries']
        for concept in concepts:
            if concept in query_lower:
                entities['concepts'].append(concept)
        
        return entities
    
    def find_starting_nodes(self, entities: Dict[str, List[str]]) -> List[Dict]:
        """
        Find graph nodes that match extracted entities.
        These are our starting points for traversal.
        """
        starting_nodes = []
        
        # Get all blocks
        blocks = self.state_manager.list_blocks(include_hidden=False)
        
        # Match people
        for person in entities['people']:
            person_id = f"person_{person.lower()}"
            starting_nodes.append({
                'id': person_id,
                'type': 'Person',
                'name': person.title(),
                'source': 'entity_extraction'
            })
        
        # Match tags
        for tag in entities['tags']:
            tag_id = f"tag_{tag.lower()}"
            starting_nodes.append({
                'id': tag_id,
                'type': 'Tag',
                'name': f'#{tag}',
                'source': 'entity_extraction'
            })
        
        # Match concepts in core memory blocks
        for concept in entities['concepts']:
            for block in blocks:
                if concept.lower() in block.content.lower():
                    starting_nodes.append({
                        'id': block.label,
                        'type': 'CoreMemory',
                        'name': block.label.title(),
                        'content': block.content[:200],
                        'source': 'concept_match'
                    })
                    break  # One match per concept
        
        return starting_nodes
    
    def traverse_graph(self, starting_nodes: List[Dict], depth: int = 2) -> Tuple[List[Dict], List[Dict]]:
        """
        Traverse graph from starting nodes.
        
        Args:
            starting_nodes: Where to start
            depth: How many hops (1-3 recommended)
        
        Returns:
            (collected_nodes, collected_edges)
        """
        visited_nodes = {}
        collected_edges = []
        to_visit = [(node, 0) for node in starting_nodes]  # (node, current_depth)
        
        blocks = self.state_manager.list_blocks(include_hidden=False)
        
        while to_visit:
            current_node, current_depth = to_visit.pop(0)
            node_id = current_node['id']
            
            if node_id in visited_nodes or current_depth >= depth:
                continue
            
            visited_nodes[node_id] = current_node
            
            # Find connected nodes based on node type
            if current_node['type'] == 'Person':
                # Find memories ABOUT this person
                person_name = current_node['name'].lower()
                for block in blocks:
                    if person_name in block.content.lower():
                        connected_node = {
                            'id': block.label,
                            'type': 'CoreMemory',
                            'name': block.label.title(),
                            'content': block.content[:300]
                        }
                        to_visit.append((connected_node, current_depth + 1))
                        collected_edges.append({
                            'source': block.label,
                            'target': node_id,
                            'type': 'ABOUT'
                        })
            
            elif current_node['type'] == 'Tag':
                # Find memories with this tag
                tag_name = current_node['name'].replace('#', '')
                for block in blocks:
                    if f'#{tag_name}' in block.content.lower():
                        connected_node = {
                            'id': block.label,
                            'type': 'CoreMemory',
                            'name': block.label.title(),
                            'content': block.content[:300]
                        }
                        to_visit.append((connected_node, current_depth + 1))
                        collected_edges.append({
                            'source': block.label,
                            'target': current_node['id'],
                            'type': 'TAGGED_WITH'
                        })
            
            elif current_node['type'] == 'CoreMemory':
                # Extract people and tags from this memory
                content = current_node.get('content', '')
                
                # Find people mentioned
                for name in ['user', 'assistant', 'agent']:
                    if name in content.lower():
                        person_node = {
                            'id': f'person_{name}',
                            'type': 'Person',
                            'name': name.title()
                        }
                        to_visit.append((person_node, current_depth + 1))
                
                # Find hashtags
                hashtags = re.findall(r'#(\w+)', content.lower())
                for tag in hashtags:
                    tag_node = {
                        'id': f'tag_{tag}',
                        'type': 'Tag',
                        'name': f'#{tag}'
                    }
                    to_visit.append((tag_node, current_depth + 1))
        
        return list(visited_nodes.values()), collected_edges
    
    def format_context(self, nodes: List[Dict], edges: List[Dict], query: str) -> str:
        """
        Format collected nodes/edges into LLM context.
        """
        context_parts = []
        
        # Group nodes by type
        by_type = defaultdict(list)
        for node in nodes:
            by_type[node['type']].append(node)
        
        context_parts.append(f"# Context Retrieved via Graph Traversal\n")
        context_parts.append(f"Query: {query}\n")
        
        # Core Memories
        if by_type['CoreMemory']:
            context_parts.append("\n## Core Memories:")
            for node in by_type['CoreMemory']:
                content = node.get('content', node.get('name', ''))
                context_parts.append(f"- {node['name']}: {content}")
        
        # People
        if by_type['Person']:
            context_parts.append("\n## Related People:")
            people = ', '.join(n['name'] for n in by_type['Person'])
            context_parts.append(f"- {people}")
        
        # Tags
        if by_type['Tag']:
            context_parts.append("\n## Related Tags:")
            tags = ', '.join(n['name'] for n in by_type['Tag'])
            context_parts.append(f"- {tags}")
        
        # Relationships
        if edges:
            context_parts.append(f"\n## Relationships: ({len(edges)} connections)")
            edge_summary = defaultdict(int)
            for edge in edges:
                edge_summary[edge['type']] += 1
            for edge_type, count in edge_summary.items():
                context_parts.append(f"- {edge_type}: {count}")
        
        return '\n'.join(context_parts)
    
    def retrieve(self, query: str, depth: int = 2, max_context_length: int = 2000) -> GraphContext:
        """
        Main retrieval method.
        
        Args:
            query: User's question/message
            depth: Graph traversal depth (1-3)
            max_context_length: Max chars for context
        
        Returns:
            GraphContext with relevant nodes, edges, formatted text
        """
        print(f"🔍 Graph RAG: Query='{query[:50]}...', depth={depth}")
        
        # 🧠⚡ PHASE 1: EMBEDDING (analyzing query)
        broadcast_consciousness_event('graph_search_active', {
            'phase': 'embedding',
            'query': query[:100],
            'depth': depth
        })
        
        # Extract entities
        entities = self.extract_entities(query)
        print(f"   Entities: {entities}")
        
        # 🧠⚡ PHASE 2: SEARCHING (finding relevant nodes)
        broadcast_consciousness_event('graph_search_active', {
            'phase': 'searching',
            'query': query[:100],
            'entities': entities
        })
        
        # Find starting nodes
        starting_nodes = self.find_starting_nodes(entities)
        print(f"   Starting nodes: {len(starting_nodes)}")
        
        if not starting_nodes:
            # Fallback: use all core memories
            blocks = self.state_manager.list_blocks(include_hidden=False)
            starting_nodes = [{
                'id': b.label,
                'type': 'CoreMemory',
                'name': b.label.title(),
                'content': b.content[:200]
            } for b in blocks[:3]]
        
        # Traverse graph
        nodes, edges = self.traverse_graph(starting_nodes, depth=depth)
        print(f"   Collected: {len(nodes)} nodes, {len(edges)} edges")
        
        # 🧠⚡ PHASE 3: NODES FOUND (highlight in frontend!)
        node_ids = [n['id'] for n in nodes]
        broadcast_consciousness_event('graph_search_active', {
            'phase': 'nodes_found',
            'query': query[:100],
            'nodes_found': node_ids,
            'node_count': len(nodes),
            'edge_count': len(edges)
        })
        
        # Format context
        formatted = self.format_context(nodes, edges, query)
        
        # Truncate if too long
        if len(formatted) > max_context_length:
            formatted = formatted[:max_context_length] + "\n... (truncated)"
        
        # Calculate relevance (simple heuristic)
        relevance = min(1.0, (len(nodes) + len(edges)) / 20)
        
        path_desc = f"Found {len(nodes)} nodes via {len(edges)} relationships"
        
        # 🧠⚡ PHASE 4: CONTEXT READY (sending to Claude!)
        broadcast_consciousness_event('graph_search_active', {
            'phase': 'context_ready',
            'query': query[:100],
            'context_length': len(formatted),
            'relevance_score': relevance
        })
        
        return GraphContext(
            nodes=nodes,
            edges=edges,
            content=formatted,
            relevance_score=relevance,
            path_description=path_desc
        )


# Convenience function
def get_graph_context(query: str, depth: int = 2) -> str:
    """
    Quick function to get graph context for a query.
    
    Usage:
        context = get_graph_context("What do you know about User and coding?")
    """
    rag = GraphRAG()
    result = rag.retrieve(query, depth=depth)
    return result.content

