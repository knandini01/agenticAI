from mcp import ClientSession
from contextlib import AsyncExitStack
from mcp.client.streamable_http import streamablehttp_client
import os

class MCPHTTPCLIENT:
    def __init__(self, url):
        self.mcp_server_url = url
        self.exit_stack = AsyncExitStack()
        self.session = None
        self._client = None
        
    async def connect(self):
        self._client = streamablehttp_client(self.mcp_server_url)
        self._receive, self._send, self._transport = await self.exit_stack.enter_async_context(self._client)
        self.session = await self.exit_stack.enter_async_context(ClientSession(self._receive, self._send))
        await self.session.initialize()

    async def list_tools(self):
        return await self.session.list_tools()

    async def call_tool(self, name: str, args: dict):
        return await self.session.call_tool(name, args)

    async def cleanup(self):
        await self.exit_stack.aclose()