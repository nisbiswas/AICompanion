from .filesystem import FileSystemTool
from .web_search import WebSearchTool


class ToolRegistry:

    def __init__(self, project_root: str):

        self.filesystem = FileSystemTool(project_root)
        self.web_search = WebSearchTool()

    def list_directory(self, path: str = ".") -> list[str]:

        return self.filesystem.list_directory(path)

    def read_file(self, path: str) -> str:

        return self.filesystem.read_file(path)

    def search_web(self, query: str, limit: int = 5) -> list[dict]:

        return self.web_search.search(query, limit)