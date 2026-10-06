import httpx


class WebSearchTool:

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8888",
    ):
        self.base_url = base_url.rstrip("/")

    def search(
        self,
        query: str,
        limit: int = 5,
    ) -> list[dict]:

        query = query.strip()

        if not query:
            return []

        limit = max(1, min(int(limit), 10))

        response = httpx.get(
            f"{self.base_url}/search",
            params={
                "q": query,
                "format": "json",
            },
            timeout=30.0,
        )

        response.raise_for_status()

        data = response.json()

        raw_results = data.get("results", [])

        results = []

        for result in raw_results[:limit]:

            title = str(
                result.get("title", "")
            ).strip()

            url = str(
                result.get("url", "")
            ).strip()

            content = str(
                result.get("content", "")
            ).strip()

            if not title and not url:
                continue

            results.append(
                {
                    "title": title,
                    "url": url,
                    "content": content,
                }
            )

        print(
            f"WEB SEARCH: {query!r} -> "
            f"{len(results)} results"
        )

        return results