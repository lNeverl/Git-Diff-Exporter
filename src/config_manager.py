"""
配置管理模块 (ConfigManager)
负责保存和读取应用程序的配置信息
"""

import json
import os
from typing import Dict, Any


class ConfigManager:
    """配置管理器，用于保存和加载用户配置"""

    def __init__(self, config_file: str = "settings.json"):
        self.config_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), config_file)
        self.default_config = {
            "repo_path": "",
            "old_sha": "",
            "new_sha": "",
            "output_path": "",
            "output_folder_name": "",
            "window_geometry": "",
            "portable_git_path": ""
        }

    def load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # 合并默认配置和加载的配置
                    merged_config = self.default_config.copy()
                    merged_config.update(config)
                    return merged_config
            else:
                return self.default_config.copy()
        except Exception as e:
            print(f"加载配置文件失败: {e}")
            return self.default_config.copy()

    def save_config(self, config: Dict[str, Any]) -> bool:
        """保存配置文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存配置文件失败: {e}")
            return False

    def update_config(self, updates: Dict[str, Any]) -> bool:
        """更新配置文件"""
        current_config = self.load_config()
        current_config.update(updates)
        return self.save_config(current_config)

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项"""
        config = self.load_config()
        return config.get(key, default)

    def set(self, key: str, value: Any) -> bool:
        """设置配置项"""
        return self.update_config({key: value})