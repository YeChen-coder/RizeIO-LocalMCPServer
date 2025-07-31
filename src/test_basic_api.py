#!/usr/bin/env python3
"""
基础的Rize API测试
"""

import asyncio
import sys
import os
from rize_client import RizeClient

async def test_basic_queries():
    """测试基础查询"""
    try:
        client = RizeClient()
        
        print("1. Testing connection...")
        success, message = await client.test_connection()
        print(f"   {message}")
        
        if not success:
            return
        
        print("\n2. Testing projects query...")
        try:
            result = await client.get_projects(5)
            projects = result.get("data", {}).get("projects", {}).get("edges", [])
            print(f"   Found {len(projects)} projects")
            for edge in projects:
                project = edge["node"]
                print(f"   - {project['name']} (ID: {project['id']})")
        except Exception as e:
            print(f"   Projects query failed: {e}")
        
        print("\n3. Testing current session...")
        try:
            result = await client.get_current_session()
            session = result.get("data", {}).get("currentSession")
            if session:
                print(f"   Active session: {session.get('title', 'Untitled')} (Type: {session.get('type', 'Unknown')})")
            else:
                print("   No active session")
        except Exception as e:
            print(f"   Current session query failed: {e}")
        
        print("\n4. Testing simple session timer...")
        try:
            # 尝试最简单的输入
            query = """
            mutation {
                startSessionTimer(input: {}) {
                    session {
                        id
                        type
                    }
                    errors {
                        message
                    }
                }
            }
            """
            result = await client.execute_query(query)
            if "errors" in result.get("data", {}).get("startSessionTimer", {}):
                errors = result["data"]["startSessionTimer"]["errors"]
                print(f"   Start timer failed: {[err['message'] for err in errors]}")
            else:
                session = result.get("data", {}).get("startSessionTimer", {}).get("session")
                if session:
                    print(f"   Timer started: {session['id']} (Type: {session.get('type', 'Unknown')})")
        except Exception as e:
            print(f"   Session timer test failed: {e}")
            
    except Exception as e:
        print(f"Test failed: {e}")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    print("=== Basic Rize API Test ===")
    asyncio.run(test_basic_queries())