#!/usr/bin/env python3
"""
Cost Tools for AI Agents

Allows the agent to check its own API costs in real-time.
Useful for budget awareness and monitoring usage.
"""

import sys
import os
import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta

# Add parent directory to path (for standalone execution)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.cost_tracker import CostTracker
from core.openrouter_cost_monitor import OpenRouterCostMonitor

logger = logging.getLogger(__name__)


class CostTools:
    """
    Cost tracking tools for agent self-awareness.
    
    Allows agents to:
    - Check REAL costs from OpenRouter API (ground truth!)
    - See breakdown by model (local tracker)
    - Monitor today's usage
    - Track recent expensive requests
    - Get budget warnings
    """
    
    def __init__(self, cost_tracker: CostTracker, openrouter_monitor: OpenRouterCostMonitor = None):
        """
        Initialize cost tools.
        
        Args:
            cost_tracker: Cost tracker instance (local estimates)
            openrouter_monitor: OpenRouter API monitor (REAL costs!)
        """
        self.cost_tracker = cost_tracker
        self.openrouter_monitor = openrouter_monitor
        logger.info("✅ Cost Tools initialized (with OpenRouter Monitor!)")
    
    def check_costs(self, timeframe: str = "today") -> str:
        """
        Check API costs (REAL costs from OpenRouter API!).
        
        Args:
            timeframe: "total", "today", "this_week", or "this_month"
            
        Returns:
            Formatted cost report with REAL OpenRouter costs + local breakdown
        """
        try:
            # Get REAL costs from OpenRouter API (GROUND TRUTH!)
            if self.openrouter_monitor:
                real_costs = self.openrouter_monitor.get_real_costs()
                
                if real_costs['status'] == 'ok':
                    # Map timeframe to OpenRouter data
                    if timeframe == "today":
                        period_cost = real_costs['daily']
                        period_name = "Today (REAL)"
                    elif timeframe == "this_week":
                        period_cost = real_costs['weekly']
                        period_name = "This Week (REAL)"
                    elif timeframe == "this_month":
                        period_cost = real_costs['monthly']
                        period_name = "This Month (REAL)"
                    else:
                        period_cost = real_costs['total']
                        period_name = "Total (REAL)"
                    
                    # Format report with REAL costs
                    report = f"""💰 **API Cost Report (OpenRouter)**

**{period_name}**: ${period_cost:.4f} USD

**OpenRouter Stats (GROUND TRUTH):**
- Today: ${real_costs['daily']:.4f}
- This Week: ${real_costs['weekly']:.4f}
- This Month: ${real_costs['monthly']:.4f}
- All-time: ${real_costs['total']:.4f}
"""
                    
                    # Add budget warnings if any
                    if real_costs.get('warning'):
                        report += f"\n⚠️ **Budget Warning:** {real_costs['warning']}\n"
                    
                    # Add credit info if available
                    if real_costs['limit'] is not None:
                        remaining = real_costs['remaining'] or 0
                        report += f"\n💳 **Credits:**\n"
                        report += f"- Limit: ${real_costs['limit']:.2f}\n"
                        report += f"- Remaining: ${remaining:.2f}\n"
                    
                    # Get local stats for model breakdown
                    stats = self.cost_tracker.get_statistics()
                    by_model = sorted(stats['by_model'], key=lambda x: x['cost'], reverse=True)[:3]
                    
                    if by_model:
                        report += f"\n**Most Used Models (Local Tracker):**\n"
                        for i, model_stat in enumerate(by_model, 1):
                            report += f"{i}. {model_stat['model']}: ${model_stat['cost']:.4f} ({model_stat['requests']} req)\n"
                    
                    logger.info(f"✅ Cost check: {timeframe} = ${period_cost:.4f} (REAL)")
                    return report
                
                else:
                    # OpenRouter API error - fall back to local tracker
                    logger.warning(f"⚠️ OpenRouter API error: {real_costs.get('error')}")
            
            # Fallback: Use local tracker if OpenRouter not available
            stats = self.cost_tracker.get_statistics()
            
            # Determine timeframe
            since = None
            if timeframe == "today":
                since = datetime.utcnow().replace(
                    hour=0, minute=0, second=0, microsecond=0
                ).isoformat()
                period_cost = self.cost_tracker.get_total_cost(since=since)
                period_name = "Today (Local Est.)"
            elif timeframe == "this_week":
                today = datetime.utcnow()
                monday = today - timedelta(days=today.weekday())
                since = monday.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
                period_cost = self.cost_tracker.get_total_cost(since=since)
                period_name = "This Week (Local Est.)"
            elif timeframe == "this_month":
                since = datetime.utcnow().replace(
                    day=1, hour=0, minute=0, second=0, microsecond=0
                ).isoformat()
                period_cost = self.cost_tracker.get_total_cost(since=since)
                period_name = "This Month (Local Est.)"
            else:
                period_cost = stats['total_cost']
                period_name = "Total (Local Est.)"
            
            # Format report
            report = f"""💰 **API Cost Report (Local Tracker)**

⚠️ Note: OpenRouter API not available - using local estimates

**{period_name}**: ${period_cost:.4f} USD

**Total Stats:**
- All-time cost: ${stats['total_cost']:.4f}
- Total requests: {stats['total_requests']:,}
- Total tokens: {stats['total_tokens']:,}

**Most Used Models:**
"""
            
            # Add top 3 models by cost
            by_model = sorted(stats['by_model'], key=lambda x: x['cost'], reverse=True)[:3]
            for i, model_stat in enumerate(by_model, 1):
                report += f"{i}. {model_stat['model']}: ${model_stat['cost']:.4f} ({model_stat['requests']} requests)\n"
            
            logger.info(f"✅ Cost check (local): {timeframe} = ${period_cost:.4f}")
            return report
            
        except Exception as e:
            error_msg = f"Failed to check costs: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return f"❌ {error_msg}"
    
    def get_cost_breakdown(self) -> str:
        """
        Get detailed cost breakdown by model.
        
        Returns:
            Formatted cost breakdown
        """
        try:
            stats = self.cost_tracker.get_statistics()
            
            # Sort models by cost
            by_model = sorted(stats['by_model'], key=lambda x: x['cost'], reverse=True)
            
            breakdown = """📊 **Detailed Cost Breakdown**

**By Model:**
"""
            
            for model_stat in by_model:
                model_name = model_stat['model'].split('/')[-1]  # Just the model name
                cost = model_stat['cost']
                requests = model_stat['requests']
                tokens = model_stat['tokens']
                avg_cost = cost / requests if requests > 0 else 0
                
                breakdown += f"\n**{model_name}**\n"
                breakdown += f"- Total: ${cost:.4f}\n"
                breakdown += f"- Requests: {requests:,}\n"
                breakdown += f"- Tokens: {tokens:,}\n"
                breakdown += f"- Avg per request: ${avg_cost:.4f}\n"
            
            breakdown += f"\n**Grand Total:** ${stats['total_cost']:.4f} USD"
            
            logger.info(f"✅ Cost breakdown generated ({len(by_model)} models)")
            return breakdown
            
        except Exception as e:
            error_msg = f"Failed to get cost breakdown: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return f"❌ {error_msg}"
    
    def get_recent_expensive_requests(self, limit: int = 5) -> str:
        """
        Get recent expensive API requests.
        
        Args:
            limit: Number of requests to show (default: 5)
            
        Returns:
            Formatted list of expensive requests
        """
        try:
            recent = self.cost_tracker.get_recent_requests(limit=limit)
            
            if not recent:
                return "No recent requests found."
            
            report = f"💸 **{limit} Most Recent Expensive Requests:**\n\n"
            
            for i, req in enumerate(recent, 1):
                timestamp = req['timestamp'][:19]  # YYYY-MM-DD HH:MM:SS
                model = req['model'].split('/')[-1]
                cost = req['cost']
                tokens = req['input_tokens'] + req['output_tokens']
                
                report += f"{i}. [{timestamp}] {model}\n"
                report += f"   Cost: ${cost:.4f} | Tokens: {tokens:,}\n\n"
            
            logger.info(f"✅ Recent expensive requests: {len(recent)} requests")
            return report
            
        except Exception as e:
            error_msg = f"Failed to get recent requests: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return f"❌ {error_msg}"
    
    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """
        Get tool schemas for OpenRouter function calling.
        
        Returns:
            List of tool schemas (UNIFIED cost_tracker tool!)
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": "cost_tracker",
                    "description": "Check API costs and usage statistics. Unified tool for budget awareness.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "action": {
                                "type": "string",
                                "enum": ["check", "breakdown", "recent"],
                                "description": "Action: 'check' (cost summary), 'breakdown' (by model), 'recent' (expensive requests)"
                            },
                            "timeframe": {
                                "type": "string",
                                "enum": ["total", "today", "this_week", "this_month"],
                                "description": "Timeframe for 'check' action (default: today)"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Number of requests for 'recent' action (default: 5)",
                                "minimum": 1,
                                "maximum": 20
                            }
                        },
                        "required": ["action"]
                    }
                }
            }
        ]
    
    def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """
        Execute a cost tool (UNIFIED!).
        
        Args:
            tool_name: Name of the tool (should be 'cost_tracker')
            arguments: Tool arguments with 'action', 'timeframe', 'limit'
            
        Returns:
            Tool result
        """
        if tool_name != "cost_tracker":
            return f"❌ Unknown cost tool: {tool_name}"
        
        action = arguments.get("action")
        
        if action == "check":
            timeframe = arguments.get("timeframe", "today")
            return self.check_costs(timeframe=timeframe)
        
        elif action == "breakdown":
            return self.get_cost_breakdown()
        
        elif action == "recent":
            limit = arguments.get("limit", 5)
            return self.get_recent_expensive_requests(limit=limit)
        
        else:
            return f"❌ Unknown action for cost_tracker: {action}"


if __name__ == "__main__":
    # Test
    from core.cost_tracker import CostTracker
    from core.postgres_manager import create_postgres_manager_from_env
    
    pg = create_postgres_manager_from_env()
    if not pg:
        print("❌ PostgreSQL required for CostTracker!")
        exit(1)
    
    tracker = CostTracker(postgres_manager=pg)
    tools = CostTools(tracker)
    
    print("\n🧪 Testing Cost Tools\n")
    
    # Test 1: Check costs
    print("1️⃣ Check Costs (Today):")
    print(tools.check_costs("today"))
    print()
    
    # Test 2: Get breakdown
    print("2️⃣ Cost Breakdown:")
    print(tools.get_cost_breakdown())
    print()
    
    # Test 3: Recent expensive
    print("3️⃣ Recent Expensive Requests:")
    print(tools.get_recent_expensive_requests(limit=3))
    print()
    
    # Test 4: Tool schemas
    print("4️⃣ Tool Schemas:")
    schemas = tools.get_tool_schemas()
    for schema in schemas:
        print(f"   - {schema['function']['name']}")
    
    print("\n✅ Cost Tools Test Complete!")

