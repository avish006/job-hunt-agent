import asyncio
import json
import os
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def async_mcp_search(query: str) -> list:
    """Connects to the local MCP server and executes the search tool."""
    
    # Path to our new MCP server script
    script_path = os.path.join(os.path.dirname(__file__), "mcp_server.py")
    
    # We must use the exact python executable from venv2
    python_exe = os.path.join(os.path.dirname(__file__), "venv2", "Scripts", "python.exe")
    if not os.path.exists(python_exe):
        python_exe = "python" # fallback
        
    server_params = StdioServerParameters(
        command=python_exe,
        args=[script_path],
        env=None
    )

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # Execute all three tools in parallel
                results = await asyncio.gather(
                    session.call_tool("search_web_jobs", arguments={"query": query}),
                    session.call_tool("search_hacker_news_jobs", arguments={"keywords": query}),
                    session.call_tool("search_remote_rss_jobs", arguments={"keywords": query}),
                    return_exceptions=True
                )
                
                all_jobs = []
                for idx, res in enumerate(results):
                    if isinstance(res, Exception):
                        import logging
                        logging.error(f"MCP Tool Error {idx}: {res}")
                    elif res and res.content:
                        try:
                            jobs = json.loads(res.content[0].text)
                            all_jobs.extend(jobs)
                        except json.JSONDecodeError as e:
                            import logging
                            logging.error(f"MCP JSON Error: {e}")
                return all_jobs
    except Exception as e:
        import logging
        logging.error(f"MCP Client Error: {e}")
        return []

def run_mcp_search(query: str) -> list:
    """Synchronous wrapper to be used in our JobAggregator"""
    return asyncio.run(async_mcp_search(query))
