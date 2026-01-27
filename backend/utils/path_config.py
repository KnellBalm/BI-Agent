import os
from pathlib import Path

class PathManager:
    """
    Manages all file system paths for BI-Agent.
    Ensures data is stored in ~/.bi-agent/ when installed as a package.
    """
    def __init__(self):
        self.base_dir = Path.home() / ".bi-agent"
        self._ensure_dirs()

    def _ensure_dirs(self):
        """Creates necessary directories if they don't exist."""
        dirs = [
            self.base_dir,
            self.base_dir / "projects",
            self.base_dir / "logs",
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

    @property
    def projects_dir(self) -> Path:
        return self.base_dir / "projects"

    @property
    def logs_dir(self) -> Path:
        return self.base_dir / "logs"

    @property
    def credentials_path(self) -> Path:
        # For AuthManager
        return self.base_dir / "credentials.json"

    @property
    def env_path(self) -> Path:
        return self.base_dir / ".env"

    def get_project_path(self, project_id: str) -> Path:
        proj_path = self.projects_dir / project_id
        proj_path.mkdir(exist_ok=True)
        return proj_path

    def get_output_path(self, project_id: str) -> Path:
        out_path = self.get_project_path(project_id) / "outputs"
        out_path.mkdir(exist_ok=True)
        return out_path

# Global instance
path_manager = PathManager()
