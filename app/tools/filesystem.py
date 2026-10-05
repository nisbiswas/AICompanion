from pathlib import Path


class FileSystemTool:

    def __init__(self, project_root: str):

        self.project_root = Path(project_root).resolve()

    def _safe_path(self, relative_path: str) -> Path:

        path = (self.project_root / relative_path).resolve()

        if not path.is_relative_to(self.project_root):
            raise ValueError(
                "Access outside the project directory is not allowed."
            )

        return path

    def list_directory(self, relative_path: str = ".") -> list[str]:

        directory = self._safe_path(relative_path)

        if not directory.is_dir():
            raise ValueError(
                f"Not a directory: {relative_path}"
            )

        return [
            item.name
            for item in directory.iterdir()
        ]

    def read_file(self, relative_path: str) -> str:

        path = self._safe_path(relative_path)

        if not path.is_file():
            raise ValueError(
                f"Not a file: {relative_path}"
            )

        return path.read_text(
            encoding="utf-8"
        )