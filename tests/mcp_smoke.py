"""Spawn `oddsky mcp` over stdio, list tools, call one. Run: python tests/mcp_smoke.py"""
import asyncio
import sys

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


async def main(case: str = "OS-0001"):
    params = StdioServerParameters(command=sys.executable, args=["-m", "oddsky.cli", "mcp", "--author", "mcp-smoke"])
    async with stdio_client(params) as (r, w), ClientSession(r, w) as s:
        await s.initialize()
        tools = await s.list_tools()
        print(len(tools.tools), "tools:", ", ".join(t.name for t in tools.tools))
        res = await s.call_tool("describe_series", {"case": case, "series": "NEOWISE:W2"})
        print(res.content[0].text[:300])


if __name__ == "__main__":
    asyncio.run(main(*sys.argv[1:]))
