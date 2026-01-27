import os
import json
import logging
from typing import Dict, Any, List, Optional
from backend.utils.logger_setup import setup_logger
from backend.utils.path_config import path_manager

logger = setup_logger("metric_store", "metrics.log")

class MetricStore:
    """
    Manages standardized business metrics and calculated fields for a project.
    Loads definitions from projects/{project_id}/metrics.json.
    """
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.metrics_path = path_manager.get_project_path(project_id) / "metrics.json"
        self.metrics: Dict[str, Any] = {}
        self._load_metrics()

    def _load_metrics(self):
        """Loads metric definitions from the project directory."""
        if not os.path.exists(self.metrics_path):
            logger.info(f"No metrics.json found for project '{self.project_id}'. Initializing empty.")
            self._ensure_dir_exists()
            with open(self.metrics_path, 'w', encoding='utf-8') as f:
                json.dump({}, f, indent=2)
            return

        try:
            with open(self.metrics_path, 'r', encoding='utf-8') as f:
                self.metrics = json.load(f)
            logger.info(f"Loaded {len(self.metrics)} metrics for project '{self.project_id}'")
        except Exception as e:
            logger.error(f"Failed to load metrics for project '{self.project_id}': {e}")
            self.metrics = {}

    def _ensure_dir_exists(self):
        os.makedirs(os.path.dirname(self.metrics_path), exist_ok=True)

    def get_metric(self, metric_id: str) -> Optional[Dict[str, Any]]:
        return self.metrics.get(metric_id)

    def list_metrics(self) -> List[Dict[str, Any]]:
        """Returns a list of all metrics with their metadata."""
        return [{"id": mid, **mdata} for mid, mdata in self.metrics.items()]

    def get_metrics_for_table(self, table_name: str) -> List[Dict[str, Any]]:
        """Finds metrics that are defined for a specific table."""
        return [
            {"id": mid, **mdata} 
            for mid, mdata in self.metrics.items() 
            if mdata.get("table") == table_name
        ]

    def add_metric(self, metric_id: str, formula: str, table: str, description: str = ""):
        """Adds or updates a metric definition."""
        self.metrics[metric_id] = {
            "formula": formula,
            "table": table,
            "description": description
        }
        self._save_metrics()

    def import_metrics_from_project(self, source_project_id: str):
        """Imports metrics from another project."""
        source_path = path_manager.get_project_path(source_project_id) / "metrics.json"
        if not os.path.exists(source_path):
            logger.warning(f"Source project '{source_project_id}' metrics not found.")
            return False
            
        try:
            with open(source_path, 'r', encoding='utf-8') as f:
                source_metrics = json.load(f)
            
            # Merge (don't overwrite existing if IDs conflict, or prefix them)
            count = 0
            for mid, mdata in source_metrics.items():
                if mid not in self.metrics:
                    self.metrics[mid] = mdata
                    count += 1
            
            if count > 0:
                self._save_metrics()
                logger.info(f"Imported {count} metrics from '{source_project_id}'")
            return True
        except Exception as e:
            logger.error(f"Failed to import metrics: {e}")
            return False

    def _save_metrics(self):
        try:
            with open(self.metrics_path, 'w', encoding='utf-8') as f:
                json.dump(self.metrics, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save metrics: {e}")
