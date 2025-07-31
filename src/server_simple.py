#!/usr/bin/env python3
"""
Rize AI Scheduler MCP Server - Simplified Version
For Claude Desktop compatibility
"""

import asyncio
import sys
import os
from typing import Dict, Any, Optional

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import TextContent, CallToolRequest, CallToolResult, Tool
    MCP_AVAILABLE = True
except ImportError as e:
    print(f"[ERROR] MCP library import failed: {e}", file=sys.stderr)
    sys.exit(1)

# 导入Rize客户端
try:
    from rize_client import RizeClient
except ImportError:
    print("[WARNING] rize_client import failed, using mock client", file=sys.stderr)
    class RizeClient:
        def __init__(self):
            pass
        async def execute_query(self, query, variables=None):
            return {"data": {"success": True}}

# 全局变量
app = Server("rize-ai-scheduler")

@app.list_tools()
async def handle_list_tools():
    """列出所有可用工具"""
    return [
        Tool(
            name="test_connection",
            description="Test Rize API connection",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="list_projects",
            description="Get list of projects",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of projects to return",
                        "default": 10
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="create_project",
            description="Create a new project",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Project name"
                    },
                    "emoji": {
                        "type": "string",
                        "description": "Project emoji (optional)"
                    }
                },
                "required": ["name"]
            }
        ),
        Tool(
            name="start_session_timer",
            description="Start a work session timer",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_type": {
                        "type": "string",
                        "description": "Session type (FOCUS, BREAK, etc.)",
                        "default": "FOCUS"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="stop_session_timer",
            description="Stop the current session timer (requires confirmation)",
            inputSchema={
                "type": "object",
                "properties": {
                    "confirm": {
                        "type": "boolean",
                        "description": "Confirm that you want to stop the current session",
                        "default": False
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="get_current_session",
            description="Get current active session",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="create_session",
            description="Create a new session with flexible time settings",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_type": {
                        "type": "string",
                        "description": "Session type (focus/break/meeting etc.)",
                        "default": "focus"
                    },
                    "title": {
                        "type": "string",
                        "description": "Session title (optional)"
                    },
                    "description": {
                        "type": "string",
                        "description": "Session description (optional)"
                    },
                    "duration_minutes": {
                        "type": "integer",
                        "description": "Session duration in minutes (used if specific times not provided)",
                        "default": 90,
                        "minimum": 5,
                        "maximum": 480
                    },
                    "start_time": {
                        "type": "string",
                        "description": "Session start time (ISO8601 format, e.g., '2024-07-21T09:00:00' or '2024-07-21 09:00')"
                    },
                    "end_time": {
                        "type": "string",
                        "description": "Session end time (ISO8601 format, e.g., '2024-07-21T11:00:00' or '2024-07-21 11:00')"
                    }
                },
                "required": []
            }
        )
    ]

@app.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    """处理工具调用请求"""
    try:
        arguments = arguments or {}
        
        if name == "test_connection":
            result = await test_connection_handler()
        elif name == "list_projects":
            result = await list_projects_handler(arguments)
        elif name == "create_project":
            result = await create_project_handler(arguments)
        elif name == "start_session_timer":
            result = await start_session_timer_handler(arguments)
        elif name == "stop_session_timer":
            result = await stop_session_timer_handler(arguments)
        elif name == "get_current_session":
            result = await get_current_session_handler()
        elif name == "create_session":
            result = await create_session_handler(arguments)
        else:
            result = f"[ERROR] Unknown tool: {name}"
        
        return [TextContent(type="text", text=str(result))]
        
    except Exception as e:
        error_msg = f"[ERROR] Tool call failed: {str(e)}"
        return [TextContent(type="text", text=error_msg)]

async def test_connection_handler() -> str:
    """测试Rize API连接"""
    try:
        client = RizeClient()
        success, message = await client.test_connection()
        return message
    except Exception as e:
        return f"[ERROR] Connection test failed: {str(e)}"

async def list_projects_handler(args: Dict[str, Any]) -> str:
    """获取项目列表"""
    try:
        client = RizeClient()
        limit = args.get("limit", 10)
        
        result = await client.get_projects(limit)
        
        if "errors" in result:
            return f"[ERROR] Failed to get projects: {result['errors']}"
        
        projects = result.get("data", {}).get("projects", {}).get("edges", [])
        
        if not projects:
            return "[INFO] No projects found. Use create_project to create one."
        
        output = f"[SUCCESS] Found {len(projects)} projects:\n\n"
        
        for edge in projects:
            project = edge["node"]
            emoji = project.get("emoji", "")
            name = project["name"]
            project_id = project["id"]
            
            output += f"{emoji} {name} (ID: {project_id})\n"
        
        return output.strip()
        
    except Exception as e:
        return f"[ERROR] Failed to list projects: {str(e)}"

async def create_project_handler(args: Dict[str, Any]) -> str:
    """创建新项目"""
    try:
        client = RizeClient()
        name = args.get("name")
        
        if not name:
            return "[ERROR] Missing required parameter: name"
        
        result = await client.create_project(
            name=name,
            emoji=args.get("emoji")
        )
        
        if "errors" in result.get("data", {}).get("createProject", {}):
            errors = result["data"]["createProject"]["errors"]
            return f"[ERROR] Failed to create project: {[err['message'] for err in errors]}"
        
        project = result.get("data", {}).get("createProject", {}).get("project")
        if not project:
            return "[ERROR] Failed to create project: No response data"
        
        emoji = project.get("emoji", "")
        project_name = project["name"]
        project_id = project["id"]
        
        return f"[SUCCESS] Project created: {emoji} {project_name} (ID: {project_id})"
        
    except Exception as e:
        return f"[ERROR] Failed to create project: {str(e)}"

async def start_session_timer_handler(args: Dict[str, Any]) -> str:
    """启动会话计时器"""
    try:
        client = RizeClient()
        session_type = args.get("session_type", "FOCUS")
        
        result = await client.start_session_timer(session_type)
        
        if "errors" in result.get("data", {}).get("startSessionTimer", {}):
            errors = result["data"]["startSessionTimer"]["errors"]
            return f"[ERROR] Failed to start timer: {[err['message'] for err in errors]}"
        
        session = result.get("data", {}).get("startSessionTimer", {}).get("session")
        if not session:
            return "[ERROR] Failed to start timer: No response data"
        
        session_id = session["id"]
        start_time = session.get("startTime", "")
        
        return f"[SUCCESS] Timer started! Session ID: {session_id}, Start time: {start_time}"
        
    except Exception as e:
        return f"[ERROR] Failed to start timer: {str(e)}"

async def stop_session_timer_handler(args: dict) -> str:
    """停止会话计时器"""
    try:
        client = RizeClient()
        confirm = args.get("confirm", False)
        
        # 如果用户已经确认，直接执行停止操作
        if confirm:
            result = await client.stop_session_timer()
            
            if "errors" in result.get("data", {}).get("stopSessionTimer", {}):
                errors = result["data"]["stopSessionTimer"]["errors"]
                return f"[ERROR] Failed to stop timer: {[err['message'] for err in errors]}"
            
            session = result.get("data", {}).get("stopSessionTimer", {}).get("session")
            if not session:
                return "[ERROR] Failed to stop timer: No response data"
            
            session_id = session["id"]
            end_time = session.get("endTime", "")
            
            return f"[SUCCESS] Timer stopped! Session ID: {session_id}, End time: {end_time}"
        
        # 如果没有确认，先检查当前会话并请求确认
        current_result = await client.get_current_session()
        current_session = current_result.get("data", {}).get("currentSession")
        
        if not current_session:
            return "[INFO] 没有活动的会话需要停止。"
        
        # 显示当前会话信息并请求确认
        session_id = current_session["id"]
        title = current_session.get("title", "当前会话")
        start_time = current_session.get("startTime", "")
        
        confirm_msg = f"[CONFIRM] 即将停止以下会话：\n\n"
        confirm_msg += f"  - 会话ID: {session_id}\n"
        confirm_msg += f"  - 标题: {title}\n"
        confirm_msg += f"  - 开始时间: {start_time}\n\n"
        confirm_msg += "这将结束当前会话并记录使用时间。\n"
        confirm_msg += "如果确认要停止，请再次调用 stop_session_timer 并添加参数 confirm=true"
        
        return confirm_msg
        
    except Exception as e:
        return f"[ERROR] Failed to process stop request: {str(e)}"

async def get_current_session_handler() -> str:
    """获取当前活动会话"""
    try:
        client = RizeClient()
        
        result = await client.get_current_session()
        
        if "errors" in result:
            return f"[ERROR] Failed to get current session: {result['errors']}"
        
        session = result.get("data", {}).get("currentSession")
        
        if not session:
            return "[INFO] No active session. Use start_session_timer to begin one."
        
        session_id = session["id"]
        title = session.get("title", "Current session")
        session_type = session.get("type", "")
        start_time = session.get("startTime", "")
        
        return f"[SUCCESS] Active session: {title} (ID: {session_id}, Type: {session_type}, Started: {start_time})"
        
    except Exception as e:
        return f"[ERROR] Failed to get current session: {str(e)}"

def validate_session_params(args: dict) -> tuple[bool, str]:
    """验证会话参数，返回(是否需要确认, 确认消息)"""
    issues = []
    suggestions = []
    
    # 检查时间相关参数
    start_time = args.get("start_time")
    end_time = args.get("end_time")
    duration_minutes = args.get("duration_minutes")
    
    if not start_time and not end_time:
        issues.append("开始时间和结束时间都未指定")
        suggestions.append("• 指定开始时间 (如: start_time='2025-07-21 14:00')")
        suggestions.append("• 或指定结束时间 (如: end_time='2025-07-21 15:30')")
    
    # 检查会话标题
    title = args.get("title")
    if not title:
        issues.append("会话标题未指定")
        suggestions.append("• 添加标题 (如: title='专注工作')")
    
    # 检查持续时间合理性
    if duration_minutes and (duration_minutes < 5 or duration_minutes > 480):
        issues.append(f"持续时间 {duration_minutes} 分钟可能不合理")
        suggestions.append("• 建议持续时间在 5-480 分钟之间")
    
    # 如果有问题，生成确认消息
    if issues:
        confirm_msg = "[CONFIRM] 创建会话前需要确认以下信息：\n\n"
        confirm_msg += "发现的问题：\n"
        for issue in issues:
            confirm_msg += f"  - {issue}\n"
        confirm_msg += "\n建议的参数：\n"
        for suggestion in suggestions:
            confirm_msg += f"  {suggestion}\n"
        confirm_msg += f"\n当前参数：\n"
        for key, value in args.items():
            confirm_msg += f"  - {key}: {value}\n"
        confirm_msg += "\n请明确指定缺失的参数后重新调用 create_session。"
        return True, confirm_msg
    
    return False, ""

async def create_session_handler(args: dict) -> str:
    """创建新会话"""
    try:
        # 首先验证参数是否需要确认
        needs_confirm, confirm_msg = validate_session_params(args)
        if needs_confirm:
            return confirm_msg
        
        client = RizeClient()
        session_type = args.get("session_type", "focus")
        title = args.get("title")
        description = args.get("description")
        duration_minutes = args.get("duration_minutes", 90)
        start_time = args.get("start_time")
        end_time = args.get("end_time")
        
        result = await client.create_session(
            session_type=session_type,
            title=title,
            description=description,
            duration_minutes=duration_minutes,
            start_time=start_time,
            end_time=end_time
        )
        
        if "errors" in result.get("data", {}).get("createSession", {}):
            errors = result["data"]["createSession"]["errors"]
            return f"[ERROR] Failed to create session: {[err['message'] for err in errors]}"
        
        session = result.get("data", {}).get("createSession", {}).get("session")
        if not session:
            return "[ERROR] Failed to create session: No response data"
        
        session_id = session["id"]
        session_title = session.get("title", "New session")
        session_type = session.get("type", "")
        start_time = session.get("startTime", "")
        end_time = session.get("endTime", "")
        
        return f"[SUCCESS] Session created: {session_title} (ID: {session_id}, Type: {session_type}, Duration: {start_time} to {end_time})"
        
    except Exception as e:
        return f"[ERROR] Failed to create session: {str(e)}"

async def run_server():
    """运行MCP服务器"""
    try:
        from mcp.server import InitializationOptions
        
        init_options = InitializationOptions(
            server_name="rize-ai-scheduler",
            server_version="1.0.0",
            capabilities={}
        )
        
        async with stdio_server() as streams:
            await app.run(
                streams[0], 
                streams[1], 
                initialization_options=init_options
            )
                    
    except Exception as e:
        print(f"[ERROR] Server startup failed: {e}", file=sys.stderr)
        sys.exit(1)

def main():
    """入口函数"""
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    print("[INFO] Starting Rize AI Scheduler MCP Server...", file=sys.stderr)
    
    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        print("[INFO] Server stopped", file=sys.stderr)
    except Exception as e:
        print(f"[ERROR] Critical error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()