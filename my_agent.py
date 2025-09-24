from strands import Agent, tool
from strands_tools import file_read
from strands.models import BedrockModel
import logging
from contextlib import contextmanager
from strands.tools.mcp.mcp_client import MCPClient
from mcp import stdio_client, StdioServerParameters

# Configure the root strands logger
logging.getLogger("strands").setLevel(logging.DEBUG)

# Add a handler to see the logs
logging.basicConfig(
    format="%(levelname)s | %(name)s | %(message)s", 
    handlers=[logging.StreamHandler()]
)

model_id = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
bedrock_model = BedrockModel(max_tokens=4096, model_id=model_id)

system_prompt = """
당신은 Agent입니다. 사용자의 질문에 답하세요. 
"""


class MyAgent():
    def __init__(self):
        self.mcp_client = None
        self.agent = None

    def initialize_mcp(self):
        if self.mcp_client is None:
            try:
                self.mcp_client = MCPClient(lambda: stdio_client(
                    StdioServerParameters(
                        command='uvx',
                        args=['awslabs.aws-documentation-mcp-server@latest'],
                        disabled=False,
                        autoApprove=[]
                    )
                ))
                self.mcp_client.start()
                tools = self.mcp_client.list_tools_sync()
                self.agent = Agent(model=bedrock_model, system_prompt=system_prompt, tools=tools)
            except Exception as e:
                print(f"MCP 초기화 실패: {e}")
                # MCP 실패시 기본 agent 사용
                self.agent = Agent(model=bedrock_model, system_prompt=system_prompt)

        return self.agent

    def cleanup(self):
        if self.mcp_client:
            try:
                self.mcp_client.stop()
            except:
                pass