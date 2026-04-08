import json
import os
import logging
from typing import Dict, Any

logger = logging.getLogger('APEX-PERSISTENCE')

class ThermalPersistenceManager:
    """Manages long-term storage of historical thermal signatures."""

    def __init__(self, base_dir: str = '.shadow/cortex'):
        self.base_dir = base_dir
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir, exist_ok=True)

    def save_signature(self, node_id: str, data: Dict[str, Any]):
        file_path = os.path.join(self.base_dir, f"{node_id}_signature.json")
        try:
            with open(file_path, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            logger.error(f"Failed to save signature for {node_id}: {e}")

    def load_signature(self, node_id: str) -> Dict[str, Any]:
        file_path = os.path.join(self.base_dir, f"{node_id}_signature.json")
        if not os.path.exists(file_path):
            return {}
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load signature for {node_id}: {e}")
            return {}
