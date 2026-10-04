# core/mcp/protocol.py
"""
Model Context Protocol (MCP) 2024-11-05 Specification Implementation.
Provides JSON-RPC 2.0 structures, typed definitions for Tools, Resources, Prompts,
and message serialization for V.O.I.D.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Union
import json

# Protocol Version
LATEST_PROTOCOL_VERSION = "2024-11-05"

# JSON-RPC 2.0 Error Codes
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603


@dataclass
class JsonRpcRequest:
    jsonrpc: str
    method: str
    params: Optional[Dict[str, Any]] = None
    id: Optional[Union[str, int]] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'JsonRpcRequest':
        return cls(
            jsonrpc=data.get("jsonrpc", "2.0"),
            method=data.get("method", ""),
            params=data.get("params"),
            id=data.get("id")
        )


@dataclass
class JsonRpcResponse:
    jsonrpc: str = "2.0"
    id: Optional[Union[str, int]] = None
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"jsonrpc": self.jsonrpc, "id": self.id}
        if self.error is not None:
            d["error"] = self.error
        else:
            d["result"] = self.result
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


@dataclass
class MCPTool:
    name: str
    description: str
    inputSchema: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.inputSchema
        }


@dataclass
class MCPResource:
    uri: str
    name: str
    description: Optional[str] = None
    mimeType: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {"uri": self.uri, "name": self.name}
        if self.description:
            d["description"] = self.description
        if self.mimeType:
            d["mimeType"] = self.mimeType
        return d


@dataclass
class MCPPrompt:
    name: str
    description: Optional[str] = None
    arguments: Optional[List[Dict[str, Any]]] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {"name": self.name}
        if self.description:
            d["description"] = self.description
        if self.arguments:
            d["arguments"] = self.arguments
        return d
