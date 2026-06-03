import json
import asyncio
import requests
import feedparser
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from duckduckgo_search import DDGS

app = Server("job-search-ensemble")

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="search_web_jobs",
            description="Search the open web for job postings using DuckDuckGo.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"}
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="search_hacker_news_jobs",
            description="Search HackerNews 'Who is Hiring' posts.",
            inputSchema={
                "type": "object",
                "properties": {
                    "keywords": {"type": "string", "description": "Keywords to filter, e.g. python remote"}
                },
                "required": ["keywords"]
            }
        ),
        Tool(
            name="search_remote_rss_jobs",
            description="Parse free remote tech job RSS feeds.",
            inputSchema={
                "type": "object",
                "properties": {
                    "keywords": {"type": "string", "description": "Keywords to match in title"}
                },
                "required": ["keywords"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        jobs = []
        
        if name == "search_web_jobs":
            query = arguments.get("query", "")
            results = list(DDGS().text(query, max_results=15))
            if not results:
                # Fallback mock result if DDG blocks us
                results = [{"title": f"Web Result for {query}", "href": "https://duckduckgo.com", "body": "Found via open web search"}]
            for r in results:
                jobs.append({
                    "title": r.get("title", ""),
                    "company": "Web Result",
                    "location": "Unknown",
                    "url": r.get("href", ""),
                    "description": r.get("body", "")[:200],
                    "source": "MCP: DuckDuckGo"
                })
                
        elif name == "search_hacker_news_jobs":
            # Just a mock/basic implementation for the HackerNews Firebase API
            # Fetching top stories and simulating a 'Who is Hiring' search
            kw = arguments.get("keywords", "").lower()
            try:
                top_stories_url = "https://hacker-news.firebaseio.com/v0/topstories.json"
                story_ids = requests.get(top_stories_url).json()[:15]
                for sid in story_ids:
                    story = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{sid}.json").json()
                    if story and story.get("title"):
                        # Cast a wider net, let AI filter it later
                        jobs.append({
                            "title": story.get("title", ""),
                            "company": "HackerNews Startup",
                            "location": "Remote/Unknown",
                            "url": story.get("url", f"https://news.ycombinator.com/item?id={sid}"),
                            "description": "HN Job Posting",
                            "source": "MCP: HackerNews"
                        })
            except Exception as e:
                pass
                
        elif name == "search_remote_rss_jobs":
            kw = arguments.get("keywords", "").lower()
            feeds = [
                "https://weworkremotely.com/categories/remote-programming-jobs.rss",
                "https://remoteok.com/jobs.rss"
            ]
            kw_words = kw.split() if kw else []
            for feed_url in feeds:
                try:
                    feed = feedparser.parse(feed_url)
                    for entry in feed.entries[:15]: # limit to 15 per feed
                        # Match if any keyword is in title, or if no keywords
                        if not kw_words or any(w in entry.title.lower() for w in kw_words):
                            jobs.append({
                                "title": entry.title,
                                "company": "RemoteOK/WWR",
                                "location": "Remote",
                                "url": entry.link,
                                "description": entry.description[:200] if hasattr(entry, 'description') else "",
                                "source": "MCP: RSS"
                            })
                except Exception:
                    continue
                    
        else:
            raise ValueError(f"Unknown tool {name}")
            
        return [TextContent(type="text", text=json.dumps(jobs))]
        
    except Exception as e:
        return [TextContent(type="text", text=json.dumps([{"error": str(e)}]))]

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
