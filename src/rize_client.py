import httpx
import os
import sys
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class RizeClient:
    """Rize.io GraphQL API 客户端"""
    
    def __init__(self, api_token: Optional[str] = None):
        """初始化Rize客户端
        
        Args:
            api_token: Rize API token，如果不提供会从环境变量中读取
        """
        self.api_token = api_token or os.getenv("RIZE_API_TOKEN")
        self.base_url = os.getenv("RIZE_API_URL", "https://api.rize.io/api/v1/graphql")
        
        if not self.api_token:
            raise ValueError(
                "❌ Rize API Token 未设置\n"
                "请在.env文件中设置: RIZE_API_TOKEN=your_token_here\n"
                "或在Rize应用中生成: Settings > API > Generate new token"
            )
        
        # 设置请求头
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
            "User-Agent": "Rize-AI-Scheduler/1.0"
        }
        
        # 设置超时
        self.timeout = httpx.Timeout(30.0, connect=10.0)
    
    async def execute_query(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """执行GraphQL查询
        
        Args:
            query: GraphQL查询字符串
            variables: 查询变量
            
        Returns:
            API响应数据
            
        Raises:
            ConnectionError: 网络连接错误
            ValueError: API返回错误
        """
        # 准备请求数据
        request_data = {
            "query": query,
            "variables": variables or {}
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    self.base_url,
                    json=request_data,
                    headers=self.headers
                )
                
                # 检查HTTP状态码
                response.raise_for_status()
                
                # 解析JSON响应
                result = response.json()
                
                # 检查GraphQL错误
                if "errors" in result:
                    error_msg = "GraphQL错误: "
                    for error in result["errors"]:
                        error_msg += error.get("message", "未知错误") + "; "
                    raise ValueError(error_msg.rstrip("; "))
                
                return result
                
            except httpx.ConnectTimeout:
                raise ConnectionError("🔌 连接Rize API超时，请检查网络连接")
            
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 401:
                    raise ValueError(
                        "🔐 API认证失败，请检查token是否正确\n"
                        f"当前token: {self.api_token[:8]}...{self.api_token[-4:]}"
                    )
                elif e.response.status_code == 429:
                    raise ValueError("⏱️ API请求频率超限，请稍后重试")
                elif e.response.status_code >= 500:
                    raise ConnectionError(f"🔥 Rize服务器错误 ({e.response.status_code})")
                else:
                    raise ValueError(f"❌ HTTP错误 {e.response.status_code}: {e.response.text}")
            
            except httpx.RequestError as e:
                raise ConnectionError(f"🚫 网络请求失败: {str(e)}")
            
            except Exception as e:
                raise ValueError(f"❌ 未知错误: {str(e)}")
    
    async def test_connection(self) -> tuple[bool, str]:
        """测试API连接
        
        Returns:
            (是否成功, 消息)
        """
        try:
            # 简单的用户查询
            query = """
            query TestConnection {
                currentUser {
                    email
                }
            }
            """
            
            result = await self.execute_query(query)
            
            user_email = result.get("data", {}).get("currentUser", {}).get("email", "Unknown")
            return True, f"[OK] Connection successful! User: {user_email}"
            
        except Exception as e:
            return False, f"[ERROR] Connection failed: {str(e)}"
    
    async def get_current_user(self) -> Dict[str, Any]:
        """获取当前用户信息"""
        query = """
        query GetCurrentUser {
            currentUser {
                email
                id
            }
        }
        """
        return await self.execute_query(query)
    
    # =============== PROJECT CRUD OPERATIONS ===============
    
    async def get_projects(self, limit: int = 50) -> Dict[str, Any]:
        """获取项目列表"""
        query = """
        query GetProjects($first: Int) {
            projects(first: $first) {
                edges {
                    node {
                        id
                        name
                        color
                        emoji
                        status
                        defaultFlag
                        timeBudget
                        timeBudgetInterval
                        lastUsedAt
                        createdAt
                        updatedAt
                        client {
                            id
                            name
                        }
                        team {
                            id
                            name
                        }
                    }
                }
                pageInfo {
                    hasNextPage
                    endCursor
                }
            }
        }
        """
        variables = {"first": limit}
        return await self.execute_query(query, variables)
    
    async def get_project(self, project_id: str) -> Dict[str, Any]:
        """获取单个项目详情"""
        query = """
        query GetProject($id: ID!) {
            project(id: $id) {
                id
                name
                color
                emoji
                status
                defaultFlag
                timeSpent
                timeBudget
                timeBudgetInterval
                lastUsedAt
                createdAt
                updatedAt
                keywords
                client {
                    id
                    name
                    color
                }
                team {
                    id
                    name
                }
                currentTimeBudget {
                    timeBudget
                    timeSpent
                    budgetIntervalStartTime
                    budgetIntervalEndTime
                }
            }
        }
        """
        variables = {"id": project_id}
        return await self.execute_query(query, variables)
    
    async def create_project(self, name: str, client_id: Optional[str] = None, 
                           color: Optional[str] = None, emoji: Optional[str] = None,
                           time_budget: Optional[int] = None, 
                           time_budget_interval: Optional[str] = None) -> Dict[str, Any]:
        """创建新项目"""
        query = """
        mutation CreateProject($input: CreateProjectInput!) {
            createProject(input: $input) {
                project {
                    id
                    name
                    color
                    emoji
                    status
                    timeSpent
                    timeBudget
                    timeBudgetInterval
                    createdAt
                    client {
                        id
                        name
                    }
                }
                errors {
                    message
                    path
                }
            }
        }
        """
        
        project_input = {"name": name}
        if client_id:
            project_input["clientId"] = client_id
        if color:
            project_input["color"] = color
        if emoji:
            project_input["emoji"] = emoji
        if time_budget:
            project_input["timeBudget"] = time_budget
        if time_budget_interval:
            project_input["timeBudgetInterval"] = time_budget_interval
            
        variables = {"input": project_input}
        return await self.execute_query(query, variables)
    
    async def update_project(self, project_id: str, name: Optional[str] = None,
                           color: Optional[str] = None, emoji: Optional[str] = None,
                           time_budget: Optional[int] = None,
                           time_budget_interval: Optional[str] = None) -> Dict[str, Any]:
        """更新项目"""
        query = """
        mutation UpdateProject($input: UpdateProjectInput!) {
            updateProject(input: $input) {
                project {
                    id
                    name
                    color
                    emoji
                    timeSpent
                    timeBudget
                    timeBudgetInterval
                    updatedAt
                }
                errors {
                    message
                    path
                }
            }
        }
        """
        
        project_input = {"id": project_id}
        if name is not None:
            project_input["name"] = name
        if color is not None:
            project_input["color"] = color
        if emoji is not None:
            project_input["emoji"] = emoji
        if time_budget is not None:
            project_input["timeBudget"] = time_budget
        if time_budget_interval is not None:
            project_input["timeBudgetInterval"] = time_budget_interval
            
        variables = {"input": project_input}
        return await self.execute_query(query, variables)
    
    async def delete_project(self, project_id: str) -> Dict[str, Any]:
        """删除项目"""
        query = """
        mutation DeleteProject($input: DeleteProjectInput!) {
            deleteProject(input: $input) {
                project {
                    id
                    name
                }
                errors {
                    message
                    path
                }
            }
        }
        """
        variables = {"input": {"id": project_id}}
        return await self.execute_query(query, variables)
    
    # =============== TASK CRUD OPERATIONS ===============
    
    async def get_tasks(self, limit: int = 50, project_id: Optional[str] = None) -> Dict[str, Any]:
        """获取任务列表"""
        query = """
        query GetTasks($first: Int, $projectId: ID) {
            tasks(first: $first, project: $projectId) {
                edges {
                    node {
                        id
                        name
                        color
                        emoji
                        status
                        defaultFlag
                        timeSpent
                        timeBudget
                        timeBudgetInterval
                        lastUsedAt
                        createdAt
                        updatedAt
                        project {
                            id
                            name
                        }
                        assignee {
                            id
                            name
                            email
                        }
                        team {
                            id
                            name
                        }
                    }
                }
                pageInfo {
                    hasNextPage
                    endCursor
                }
            }
        }
        """
        variables = {"first": limit}
        if project_id:
            variables["projectId"] = project_id
        return await self.execute_query(query, variables)
    
    async def get_task(self, task_id: str) -> Dict[str, Any]:
        """获取单个任务详情"""
        query = """
        query GetTask($id: ID!) {
            task(id: $id) {
                id
                name
                color
                emoji
                status
                defaultFlag
                timeSpent
                timeBudget
                timeBudgetInterval
                lastUsedAt
                createdAt
                updatedAt
                keywords
                project {
                    id
                    name
                    color
                    client {
                        id
                        name
                    }
                }
                assignee {
                    id
                    name
                    email
                }
                team {
                    id
                    name
                }
                currentTimeBudget {
                    timeBudget
                    timeSpent
                    budgetIntervalStartTime
                    budgetIntervalEndTime
                }
            }
        }
        """
        variables = {"id": task_id}
        return await self.execute_query(query, variables)
    
    async def create_task(self, name: str, project_id: Optional[str] = None,
                         assignee_id: Optional[str] = None, color: Optional[str] = None,
                         emoji: Optional[str] = None, time_budget: Optional[int] = None,
                         time_budget_interval: Optional[str] = None) -> Dict[str, Any]:
        """创建新任务"""
        query = """
        mutation CreateTask($input: CreateTaskInput!) {
            createTask(input: $input) {
                task {
                    id
                    name
                    color
                    emoji
                    status
                    timeSpent
                    timeBudget
                    timeBudgetInterval
                    createdAt
                    project {
                        id
                        name
                    }
                    assignee {
                        id
                        name
                    }
                }
                errors {
                    message
                    path
                }
            }
        }
        """
        
        task_input = {"name": name}
        if project_id:
            task_input["projectId"] = project_id
        if assignee_id:
            task_input["assigneeId"] = assignee_id
        if color:
            task_input["color"] = color
        if emoji:
            task_input["emoji"] = emoji
        if time_budget:
            task_input["timeBudget"] = time_budget
        if time_budget_interval:
            task_input["timeBudgetInterval"] = time_budget_interval
            
        variables = {"input": task_input}
        return await self.execute_query(query, variables)
    
    async def update_task(self, task_id: str, name: Optional[str] = None,
                         project_id: Optional[str] = None, assignee_id: Optional[str] = None,
                         color: Optional[str] = None, emoji: Optional[str] = None,
                         time_budget: Optional[int] = None,
                         time_budget_interval: Optional[str] = None) -> Dict[str, Any]:
        """更新任务"""
        query = """
        mutation UpdateTask($input: UpdateTaskInput!) {
            updateTask(input: $input) {
                task {
                    id
                    name
                    color
                    emoji
                    timeSpent
                    timeBudget
                    timeBudgetInterval
                    updatedAt
                    project {
                        id
                        name
                    }
                    assignee {
                        id
                        name
                    }
                }
                errors {
                    message
                    path
                }
            }
        }
        """
        
        task_input = {"id": task_id}
        if name is not None:
            task_input["name"] = name
        if project_id is not None:
            task_input["projectId"] = project_id
        if assignee_id is not None:
            task_input["assigneeId"] = assignee_id
        if color is not None:
            task_input["color"] = color
        if emoji is not None:
            task_input["emoji"] = emoji
        if time_budget is not None:
            task_input["timeBudget"] = time_budget
        if time_budget_interval is not None:
            task_input["timeBudgetInterval"] = time_budget_interval
            
        variables = {"input": task_input}
        return await self.execute_query(query, variables)
    
    async def delete_task(self, task_id: str) -> Dict[str, Any]:
        """删除任务"""
        query = """
        mutation DeleteTask($input: DeleteTaskInput!) {
            deleteTask(input: $input) {
                task {
                    id
                    name
                }
                errors {
                    message
                    path
                }
            }
        }
        """
        variables = {"input": {"id": task_id}}
        return await self.execute_query(query, variables)
    
    # =============== SESSION CRUD OPERATIONS ===============
    
    async def get_sessions(self, limit: int = 50) -> Dict[str, Any]:
        """获取会话列表"""
        query = """
        query GetSessions($first: Int) {
            sessions(first: $first) {
                edges {
                    node {
                        id
                        title
                        description
                        type
                        source
                        startTime
                        endTime
                        createdAt
                        updatedAt
                        clients {
                            id
                            name
                        }
                        projects {
                            id
                            name
                        }
                        tasks {
                            id
                            name
                        }
                    }
                }
                pageInfo {
                    hasNextPage
                    endCursor
                }
            }
        }
        """
        variables = {"first": limit}
        return await self.execute_query(query, variables)
    
    async def get_current_session(self) -> Dict[str, Any]:
        """获取当前活动会话"""
        query = """
        query GetCurrentSession {
            currentSession {
                id
                title
                description
                type
                source
                startTime
                endTime
                createdAt
                updatedAt
                clients {
                    id
                    name
                }
                projects {
                    id
                    name
                }
                tasks {
                    id
                    name
                }
            }
        }
        """
        return await self.execute_query(query)
    
    async def create_session(self, session_type: str = "focus", title: Optional[str] = None,
                           description: Optional[str] = None, duration_minutes: int = 90,
                           start_time: Optional[str] = None, end_time: Optional[str] = None) -> Dict[str, Any]:
        """创建新会话"""
        query = """
        mutation CreateSession($input: CreateSessionInput!) {
            createSession(input: $input) {
                session {
                    id
                    title
                    description
                    type
                    startTime
                    endTime
                    createdAt
                }
            }
        }
        """
        
        # 处理时间设置的不同情况
        from datetime import datetime, timedelta
        
        def parse_time_string(time_str: str) -> datetime:
            """解析时间字符串，支持多种格式"""
            # 尝试常见的时间格式
            formats = [
                "%Y-%m-%dT%H:%M:%S",      # 2024-07-21T09:00:00
                "%Y-%m-%d %H:%M:%S",      # 2024-07-21 09:00:00
                "%Y-%m-%dT%H:%M",         # 2024-07-21T09:00
                "%Y-%m-%d %H:%M",         # 2024-07-21 09:00
                "%Y-%m-%dT%H:%M:%SZ",     # 2024-07-21T09:00:00Z
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(time_str.replace('Z', ''), fmt)
                except ValueError:
                    continue
            
            # 如果都失败，尝试使用fromisoformat (Python 3.7+)
            try:
                return datetime.fromisoformat(time_str.replace('Z', ''))
            except ValueError:
                raise ValueError(f"Cannot parse time string: {time_str}")
        
        if start_time and end_time:
            # 情况1: 开始和结束时间都指定了
            start_dt = parse_time_string(start_time)
            end_dt = parse_time_string(end_time)
        elif start_time:
            # 情况2: 只指定开始时间，用duration计算结束时间
            start_dt = parse_time_string(start_time)
            end_dt = start_dt + timedelta(minutes=duration_minutes)
        elif end_time:
            # 情况3: 只指定结束时间，用duration计算开始时间
            end_dt = parse_time_string(end_time)
            start_dt = end_dt - timedelta(minutes=duration_minutes)
        else:
            # 情况4: 都没指定，使用当前时间+duration（默认行为）
            start_dt = datetime.now()
            end_dt = start_dt + timedelta(minutes=duration_minutes)
        
        # 根据成功示例，正确的结构应该是 input: { args: { ... } }
        session_args = {
            "startTime": start_dt.isoformat() + "Z",
            "endTime": end_dt.isoformat() + "Z"
        }
        
        # 可选字段
        if title:
            session_args["title"] = title
        if description:
            session_args["description"] = description
            
        variables = {
            "input": {
                "args": session_args
            }
        }
        return await self.execute_query(query, variables)
    
    async def update_session(self, session_id: str, title: Optional[str] = None,
                           description: Optional[str] = None) -> Dict[str, Any]:
        """更新会话"""
        query = """
        mutation UpdateSession($input: UpdateSessionInput!) {
            updateSession(input: $input) {
                session {
                    id
                    title
                    description
                    type
                    startTime
                    endTime
                    updatedAt
                }
                errors {
                    message
                    path
                }
            }
        }
        """
        
        session_input = {"id": session_id}
        if title is not None:
            session_input["title"] = title
        if description is not None:
            session_input["description"] = description
            
        variables = {"input": session_input}
        return await self.execute_query(query, variables)
    
    async def delete_session(self, session_id: str) -> Dict[str, Any]:
        """删除会话"""
        query = """
        mutation DeleteSession($input: DeleteSessionInput!) {
            deleteSession(input: $input) {
                session {
                    id
                    title
                }
                errors {
                    message
                    path
                }
            }
        }
        """
        variables = {"input": {"id": session_id}}
        return await self.execute_query(query, variables)
    
    async def start_session_timer(self, session_type: str = "FOCUS") -> Dict[str, Any]:
        """启动会话计时器"""
        query = """
        mutation StartSessionTimer($input: StartSessionTimerInput!) {
            startSessionTimer(input: $input) {
                session {
                    id
                    type
                    startTime
                }
                errors {
                    message
                    path
                }
            }
        }
        """
        # 根据实际API测试，先试试只传clientMutationId
        variables = {
            "input": {
                "clientMutationId": "start_timer_" + str(int(__import__('time').time()))
            }
        }
        return await self.execute_query(query, variables)
    
    async def stop_session_timer(self) -> Dict[str, Any]:
        """停止会话计时器"""
        query = """
        mutation StopSessionTimer($input: StopSessionTimerInput!) {
            stopSessionTimer(input: $input) {
                session {
                    id
                    type
                    startTime
                    endTime
                }
                errors {
                    message
                    path
                }
            }
        }
        """
        # StopSessionTimerInput 可能只需要一个空对象，但确保不是null
        variables = {"input": {}}
        return await self.execute_query(query, variables)
    
    async def extend_current_session(self, minutes: int = 30) -> Dict[str, Any]:
        """延长当前会话"""
        query = """
        mutation ExtendCurrentSession($input: ExtendCurrentSessionInput!) {
            extendCurrentSession(input: $input) {
                session {
                    id
                    type
                    startTime
                    endTime
                }
                errors {
                    message
                    path
                }
            }
        }
        """
        variables = {"input": {"minutes": minutes}}
        return await self.execute_query(query, variables)

# 测试函数
async def test_rize_client():
    """测试Rize客户端连接"""
    try:
        client = RizeClient()
        success, message = await client.test_connection()
        # 移除emoji避免编码问题
        clean_message = message.replace("✅", "[OK]").replace("❌", "[ERROR]").replace("🔗", "").replace("⚡", "").replace("📧", "").replace("🎉", "")
        print(clean_message)
        
        if success:
            # 测试获取项目
            projects = await client.get_projects(5)
            project_count = len(projects.get('data', {}).get('projects', {}).get('edges', []))
            print(f"Projects found: {project_count}")
        
    except Exception as e:
        print(f"[ERROR] Test failed: {e}")

if __name__ == "__main__":
    # 如果直接运行此文件，执行测试
    import asyncio
    import os
    
    # Windows控制台UTF-8编码支持
    if sys.platform == "win32":
        os.environ['PYTHONIOENCODING'] = 'utf-8'
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    # 简化输出避免编码问题
    print("Testing Rize API connection...")
    asyncio.run(test_rize_client())