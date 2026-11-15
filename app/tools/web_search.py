import httpx
import os
from urllib.parse import urlparse
from app.ai.cancellation import run_async


class WebSearchTool:

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8888",
    ):
        self.base_url = os.getenv("SEARXNG_URL", base_url).rstrip("/")

    def search(
        self,
        query: str,
        limit: int = 5,
    ) -> list[dict]:

        query = query.strip()

        if not query:
            return []

        limit = max(1, min(int(limit), 10))

        async def search():
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{self.base_url}/search", params={"q": query, "format": "json"})
                response.raise_for_status()
                return response.json()
        try:
            data = run_async(search)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 403:
                raise RuntimeError("SearXNG returned HTTP 403. Check that search.formats includes json in its settings.yml.") from exc
            raise RuntimeError(f"SearXNG returned HTTP {exc.response.status_code}. Check the local search service.") from exc
        except httpx.ConnectError as exc:
            raise RuntimeError(f"Cannot connect to SearXNG at {self.base_url}. Start the search service.") from exc
        except httpx.TimeoutException as exc:
            raise RuntimeError("SearXNG timed out. Check its network connection and enabled search engines.") from exc
        except ValueError as exc:
            raise RuntimeError("SearXNG did not return JSON. Check the search endpoint and JSON format setting.") from exc
        if not isinstance(data, dict) or not isinstance(data.get("results"), list):
            raise RuntimeError("SearXNG returned an invalid results payload.")

        raw_results = data.get("results", [])

        results = []

        for result in raw_results:
            if not isinstance(result, dict):
                continue

            title = str(
                result.get("title", "")
            ).strip()

            url = str(
                result.get("url", "")
            ).strip()

            content = str(
                result.get("content", "")
            ).strip()

            if urlparse(url).scheme not in {"http", "https"} or not urlparse(url).netloc:
                continue

            results.append(
                {
                    "title": title,
                    "url": url,
                    "content": content,
                }
            )
            if len(results) >= limit:
                break

        print(
            f"WEB SEARCH: {query!r} -> "
            f"{len(results)} results"
        )

        return results
