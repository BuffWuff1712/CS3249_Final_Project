"""Inspect Shopify Global Catalog directly, without running Beany's servers."""
import asyncio
import json
from pathlib import Path

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.types import (
    CallToolRequest,
    CallToolRequestParams,
    CallToolResult,
    ClientRequest,
    ContentBlock,
    PaginatedRequestParams,
)
from pydantic import Field


ENDPOINT = "https://catalog.shopify.com/api/ucp/mcp"
PROFILE = (
    "https://shopify.dev/ucp/agent-profiles/examples/"
    "2026-08-25/valid-with-capabilities.json"
)
QUERY = "wireless headphones"
OUTPUT = Path(__file__).with_name("shopify_response.json")


class CatalogResult(CallToolResult):
    # Accommodates responses containing structuredContent without content.
    content: list[ContentBlock] = Field(default_factory=list)


async def main():
    metadata = {"ucp-agent": {"profile": PROFILE}}

    async with asyncio.timeout(60):
        async with streamablehttp_client(
            ENDPOINT, timeout=30, sse_read_timeout=30
        ) as (read, write, _):
            async with ClientSession(read, write) as client:
                await client.initialize()
                tools = await client.list_tools(
                    params=PaginatedRequestParams(_meta=metadata)
                )
                print("Available tools:", [tool.name for tool in tools.tools])

                request = ClientRequest(
                    CallToolRequest(
                        params=CallToolRequestParams(
                            name="search_catalog",
                            arguments={
                                "meta": metadata,
                                "catalog": {
                                    "query": QUERY,
                                    "context": {
                                        "address_country": "SG",
                                        "currency": "SGD",
                                    },
                                    "filters": {
                                        "available": True,
                                        "ships_to": {"country": "SG"},
                                    },
                                    "pagination": {"limit": 5},
                                },
                            },
                        )
                    )
                )
                result = await client.send_request(request, CatalogResult)

                # Save the complete decoded MCP result, including any tool error.
                output = result.model_dump(mode="json", exclude_none=True)
                formatted = json.dumps(output, indent=2, ensure_ascii=False)
                OUTPUT.write_text(formatted, encoding="utf-8")
                print(formatted)
                print(f"\nSaved response to: {OUTPUT}")
                if result.isError:
                    print("Shopify returned a tool error; inspect the saved response.")


if __name__ == "__main__":
    asyncio.run(main())
