"""
core/plugin_manager.py
Modular Plugin Architecture for V.O.I.D.
Provides dynamic plugin discovery, loading, lifecycle management,
and tool registration for external capabilities in the `plugins/` directory.
"""

import os
import sys
import json
import logging
import importlib.util
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple, Callable
from dataclasses import dataclass, field

from core.event_bus import event_bus, SystemEvent

logger = logging.getLogger("VOID.PluginManager")


@dataclass
class PluginMetadata:
    id: str
    name: str
    version: str
    description: str
    author: str = "V.O.I.D. Contributor"
    entrypoint: str = "plugin.py"
    class_name: str = "Plugin"
    enabled: bool = True
    triggers: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)
    config_file: str = "config.json"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PluginMetadata':
        return cls(
            id=data.get("id", "unknown_plugin"),
            name=data.get("name", "Unnamed Plugin"),
            version=data.get("version", "1.0.0"),
            description=data.get("description", ""),
            author=data.get("author", "V.O.I.D. Contributor"),
            entrypoint=data.get("entrypoint", "plugin.py"),
            class_name=data.get("class_name", "Plugin"),
            enabled=data.get("enabled", True),
            triggers=data.get("triggers", []),
            permissions=data.get("permissions", []),
            config_file=data.get("config_file", "config.json")
        )


class PluginBase(ABC):
    """
    Abstract Base Class for all V.O.I.D. Plugins.
    """
    def __init__(self, metadata: PluginMetadata, plugin_dir: str):
        self.metadata = metadata
        self.plugin_dir = plugin_dir
        self.config: Dict[str, Any] = self._load_config()
        self.is_initialized = False

    def _load_config(self) -> Dict[str, Any]:
        cfg_path = os.path.join(self.plugin_dir, self.metadata.config_file)
        if os.path.exists(cfg_path):
            try:
                with open(cfg_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️ [PluginManager] Error loading config for {self.metadata.id}: {e}")
        return {}

    def save_config(self, new_config: Dict[str, Any]) -> bool:
        cfg_path = os.path.join(self.plugin_dir, self.metadata.config_file)
        try:
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump(new_config, f, indent=2)
            self.config = new_config
            return True
        except Exception as e:
            print(f"⚠️ [PluginManager] Error saving config for {self.metadata.id}: {e}")
            return False

    @abstractmethod
    def initialize(self, context: Dict[str, Any]) -> bool:
        """Initialize plugin state, connections, or models."""
        pass

    @abstractmethod
    def can_handle(self, query: str) -> bool:
        """Returns True if this plugin can handle the user query."""
        pass

    @abstractmethod
    def handle(self, query: str, **kwargs) -> Tuple[Optional[str], str]:
        """
        Executes query handling.
        Returns: (response_text, skill_tag)
        """
        pass

    def get_tools(self) -> List[Any]:
        """Returns a list of Tool instances to register into ToolRegistry."""
        return []

    def get_status(self) -> Dict[str, Any]:
        """Returns operational health & status metadata."""
        return {
            "id": self.metadata.id,
            "name": self.metadata.name,
            "version": self.metadata.version,
            "status": "ONLINE" if self.is_initialized else "IDLE",
            "enabled": self.metadata.enabled,
        }

    def shutdown(self):
        """Cleanup resources on system shutdown."""
        pass


class PluginManager:
    """
    Central Manager for discovering, loading, managing, and dispatching plugins.
    """
    _instance: Optional['PluginManager'] = None

    def __init__(self, plugins_dir: Optional[str] = None):
        if plugins_dir is None:
            # Default to <project_root>/plugins
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            plugins_dir = os.path.join(project_root, "plugins")
        
        self.plugins_dir = plugins_dir
        self.plugins: Dict[str, PluginBase] = {}
        os.makedirs(self.plugins_dir, exist_ok=True)

    @classmethod
    def get_instance(cls) -> 'PluginManager':
        if cls._instance is None:
            cls._instance = PluginManager()
            cls._instance.discover_and_load_plugins()
        return cls._instance

    def discover_and_load_plugins(self, context: Optional[Dict[str, Any]] = None) -> Dict[str, bool]:
        """
        Scans `plugins/` directory and loads all valid plugins.
        """
        if context is None:
            context = {}

        results = {}
        if not os.path.isdir(self.plugins_dir):
            return results

        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)

        for entry in os.listdir(self.plugins_dir):
            plugin_path = os.path.join(self.plugins_dir, entry)
            if not os.path.isdir(plugin_path) or entry.startswith("__"):
                continue

            manifest_path = os.path.join(plugin_path, "plugin.json")
            if not os.path.exists(manifest_path):
                continue

            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    manifest_data = json.load(f)

                metadata = PluginMetadata.from_dict(manifest_data)
                if not metadata.enabled:
                    print(f"[PluginManager] Plugin '{metadata.id}' is disabled. Skipping.")
                    results[metadata.id] = False
                    continue

                plugin_entry_path = os.path.join(plugin_path, metadata.entrypoint)
                if not os.path.exists(plugin_entry_path):
                    print(f"[PluginManager] Entrypoint '{metadata.entrypoint}' not found in {entry}")
                    results[metadata.id] = False
                    continue

                # Standard Clean Import
                module_name = f"plugins.{entry}.{metadata.entrypoint[:-3]}"
                module = importlib.import_module(module_name)

                # Instantiate Plugin Class
                plugin_cls = getattr(module, metadata.class_name, None)
                is_plugin_subclass = (
                    plugin_cls is not None and isinstance(plugin_cls, type) and (
                        issubclass(plugin_cls, PluginBase) or
                        any(base.__name__ == "PluginBase" for base in getattr(plugin_cls, "__mro__", []))
                    )
                )
                if not is_plugin_subclass:
                    logger.warning(f"[PluginManager] Class '{metadata.class_name}' not found or doesn't inherit PluginBase in {entry}")
                    results[metadata.id] = False
                    continue

                plugin_instance: PluginBase = plugin_cls(metadata=metadata, plugin_dir=plugin_path)
                initialized = plugin_instance.initialize(context)
                plugin_instance.is_initialized = initialized

                self.plugins[metadata.id] = plugin_instance
                results[metadata.id] = True
                logger.info(f"[PluginManager] Loaded & Initialized Plugin: {metadata.name} v{metadata.version} [{metadata.id}]")

            except Exception as e:
                logger.error(f"[PluginManager] Failed to load plugin from '{entry}': {e}")
                results[entry] = False

        return results

    def get_plugin(self, plugin_id: str) -> Optional[PluginBase]:
        return self.plugins.get(plugin_id)

    def list_plugins(self) -> List[Dict[str, Any]]:
        return [p.get_status() for p in self.plugins.values()]

    def can_handle(self, query: str) -> Optional[PluginBase]:
        """
        Checks if any active plugin can handle the incoming query.
        """
        for plugin in self.plugins.values():
            if not plugin.metadata.enabled:
                continue
            try:
                if plugin.can_handle(query):
                    return plugin
            except Exception as e:
                print(f"⚠️ [PluginManager] can_handle error in {plugin.metadata.id}: {e}")
        return None

    def dispatch(self, query: str, **kwargs) -> Optional[Tuple[str, str]]:
        """
        Dispatches query to matching plugin if any.
        Returns (response, skill_tag) or None.
        """
        plugin = self.can_handle(query)
        if plugin:
            try:
                event_bus.publish(SystemEvent.TOOL_STARTED, {
                    "tool": f"plugin_{plugin.metadata.id}",
                    "query": query[:100]
                })
                res, skill_tag = plugin.handle(query, **kwargs)
                event_bus.publish(SystemEvent.TOOL_FINISHED, {
                    "tool": f"plugin_{plugin.metadata.id}",
                    "status": "SUCCESS"
                })
                return res, skill_tag
            except Exception as e:
                event_bus.publish(SystemEvent.TOOL_FAILED, {
                    "tool": f"plugin_{plugin.metadata.id}",
                    "error": str(e)
                })
                return f"❌ Plugin '{plugin.metadata.name}' error: {str(e)}", f"plugin_{plugin.metadata.id}"
        return None

    def register_tools_to_registry(self, tool_registry_instance):
        """
        Registers all tools exposed by active plugins into V.O.I.D.'s ToolRegistry.
        """
        for plugin in self.plugins.values():
            tools = plugin.get_tools()
            for tool in tools:
                tool_registry_instance.register_tool(tool)
                logger.info(f"  └─ Registered Plugin Tool: '{tool.name}' from {plugin.metadata.id}")
