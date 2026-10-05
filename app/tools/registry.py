from .filesystem import FileSystemTool


class ToolRegistry:

    def __init__(self, project_root: str):

        self.filesystem = FileSystemTool(project_root)

    def list_directory(self, path: str = ".") -> list[str]:

        return self.filesystem.list_directory(path)

    def read_file(self, path: str) -> str:

        return self.filesystem.read_file(path)



