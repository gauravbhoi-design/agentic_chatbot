import httpx
import json
import time
import asyncio
from typing import Optional
from config import MONDAY_API_KEY, MONDAY_API_URL


class MondayClient:
    """Robust Monday.com GraphQL API client with pagination and error handling."""

    def __init__(self):
        self.headers = {
            "Authorization": MONDAY_API_KEY,
            "Content-Type": "application/json",
            "API-Version": "2024-10",
        }
        self._rate_limit_remaining = None
        self._rate_limit_reset = None

    async def execute_query(self, query: str, variables: Optional[dict] = None) -> dict:
        """Execute a GraphQL query against Monday.com API with retry logic."""
        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        MONDAY_API_URL,
                        headers=self.headers,
                        json=payload,
                        timeout=30.0,
                    )

                    # Track rate limits
                    self._rate_limit_remaining = response.headers.get(
                        "x-ratelimit-remaining"
                    )

                    if response.status_code == 429:
                        retry_after = int(response.headers.get("Retry-After", 5))
                        await asyncio.sleep(retry_after)
                        continue

                    response.raise_for_status()
                    result = response.json()

                    if "errors" in result:
                        error_msg = result["errors"][0].get("message", "Unknown GraphQL error")
                        raise Exception(f"Monday.com GraphQL error: {error_msg}")

                    return result

            except httpx.TimeoutException:
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise Exception("Monday.com API timeout after 3 retries")
            except httpx.HTTPStatusError as e:
                if attempt < max_retries - 1 and e.response.status_code >= 500:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise Exception(f"Monday.com API error: {e.response.status_code}")

        raise Exception("Monday.com API: max retries exceeded")

    async def get_board_items(self, board_id: str, limit: int = 500) -> list:
        """Fetch all items from a board with cursor-based pagination."""
        all_items = []
        cursor = None
        start_time = time.time()

        # First page query
        query = """
        {
            boards(ids: %s) {
                name
                items_page(limit: %d) {
                    cursor
                    items {
                        id
                        name
                        column_values {
                            id
                            text
                            value
                            column {
                                title
                            }
                        }
                    }
                }
            }
        }
        """ % (board_id, limit)

        result = await self.execute_query(query)
        board_data = result["data"]["boards"][0]
        items_page = board_data["items_page"]
        all_items.extend(items_page["items"])
        cursor = items_page.get("cursor")

        # Paginate through remaining items
        while cursor:
            next_query = """
            {
                next_items_page(cursor: "%s", limit: %d) {
                    cursor
                    items {
                        id
                        name
                        column_values {
                            id
                            text
                            value
                            column {
                                title
                            }
                        }
                    }
                }
            }
            """ % (cursor, limit)

            result = await self.execute_query(next_query)
            next_page = result["data"]["next_items_page"]
            all_items.extend(next_page["items"])
            cursor = next_page.get("cursor")

        elapsed = round((time.time() - start_time) * 1000)
        return all_items, elapsed

    async def get_board_columns(self, board_id: str) -> list:
        """Fetch column definitions for a board."""
        query = """
        {
            boards(ids: %s) {
                name
                columns {
                    id
                    title
                    type
                    settings_str
                }
            }
        }
        """ % board_id

        result = await self.execute_query(query)
        board = result["data"]["boards"][0]
        return {
            "board_name": board["name"],
            "columns": board["columns"],
        }

    async def check_connection(self, board_id: str) -> dict:
        """Verify connection to a Monday.com board."""
        try:
            query = """
            {
                boards(ids: %s) {
                    name
                    items_count
                }
            }
            """ % board_id
            result = await self.execute_query(query)
            board = result["data"]["boards"][0]
            return {
                "connected": True,
                "board_name": board["name"],
                "item_count": board["items_count"],
            }
        except Exception as e:
            return {
                "connected": False,
                "error": str(e),
            }

    def parse_items_to_records(self, items: list) -> list[dict]:
        """Convert Monday.com item format to flat dictionaries."""
        records = []
        for item in items:
            record = {"item_id": item["id"], "name": item["name"]}
            for col in item["column_values"]:
                col_title = col["column"]["title"]
                text_val = col.get("text")
                raw_val = col.get("value")

                # Use text for display, but keep raw value for structured data
                record[col_title] = text_val if text_val else None

                # Parse JSON value for structured column types if needed
                if raw_val and not text_val:
                    try:
                        parsed = json.loads(raw_val)
                        if isinstance(parsed, dict):
                            record[col_title] = parsed.get("text") or parsed.get("label")
                    except (json.JSONDecodeError, TypeError):
                        pass

            records.append(record)
        return records


# Singleton instance
monday_client = MondayClient()
