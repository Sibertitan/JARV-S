"""Small stdio MCP client used to expose locally configured server tools."""

import asyncio
import hashlib
import json
import os
import re
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

MCP_DISCOVERY_TIMEOUT_SECONDS = 20
MCP_TOOL_TIMEOUT_SECONDS = 180
MCP_MAX_TOOLS = 256
MCP_SEARCH_MAX_RESULTS = 40


class MCPToolBridge:
    def __init__(self, config_path, on_error=None):
        self.config_path = Path(config_path)
        self.on_error = on_error or (lambda _message: None)
        self._definitions = None
        self._specs = None
        self._tool_map = {}

    def _servers(self):
        if self._definitions is None:
            try:
                config = json.loads(self.config_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                config = {}
            definitions = config.get("mcpServers", {}) if isinstance(config, dict) else {}
            self._definitions = {
                name: value for name, value in definitions.items()
                if isinstance(name, str) and isinstance(value, dict)
                and isinstance(value.get("command"), str) and value["command"].strip()
                and isinstance(value.get("args", []), list)
                and all(isinstance(arg, str) for arg in value.get("args", []))
            }
        return self._definitions

    def _params(self, name, definition):
        env = definition.get("env", {})
        env = {str(key): str(value) for key, value in env.items()} if isinstance(env, dict) else {}
        return StdioServerParameters(
            command=definition["command"],
            args=definition.get("args", []),
            env={**os.environ, **env},
            cwd=definition.get("cwd") or None,
        )

    async def _discover_server(self, name, definition):
        async with stdio_client(self._params(name, definition)) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.list_tools()
                return result.tools

    def tool_specs(self):
        if self._specs is not None:
            return list(self._specs)
        self._tool_map = {}
        specs = []
        for server_name, definition in self._servers().items():
            try:
                server_tools = asyncio.run(asyncio.wait_for(
                    self._discover_server(server_name, definition),
                    timeout=MCP_DISCOVERY_TIMEOUT_SECONDS,
                ))
            except Exception as error:
                self.on_error(f"MCP '{server_name}' başlatılamadı: {type(error).__name__}: {error}")
                continue
            for tool in server_tools:
                safe = re.sub(r"[^A-Za-z0-9_]", "_", f"mcp__{server_name}__{tool.name}")
                if len(safe) > 64:
                    suffix = hashlib.sha256(safe.encode("utf-8")).hexdigest()[:8]
                    safe = safe[:55] + "_" + suffix
                if safe in self._tool_map:
                    self.on_error(f"MCP araç adı çakıştı, atlandı: {safe}")
                    continue
                schema = getattr(tool, "inputSchema", None) or {"type": "object", "properties": {}}
                if not isinstance(schema, dict):
                    schema = {"type": "object", "properties": {}}
                self._tool_map[safe] = (server_name, definition, tool.name, tool.description or tool.name)
                specs.append({
                    "name": safe,
                    "description": f"[{server_name}] {tool.description or tool.name}"[:1000],
                    "input_schema": schema,
                })
        self._specs = specs[:MCP_MAX_TOOLS]
        self._tool_map = {spec["name"]: self._tool_map[spec["name"]] for spec in self._specs}
        return list(self._specs)

    def search_tools(self, query="", server="", limit=20):
        specs = self.tool_specs()
        query_terms = [term.casefold() for term in str(query).split() if len(term) > 1]
        server_filter = str(server).strip().casefold()
        matches = []
        for spec in specs:
            server_name = spec["name"].split("__", 2)[1]
            haystack = f"{server_name} {spec['name']} {spec['description']}".casefold()
            if server_filter and server_filter not in server_name.casefold():
                continue
            if query_terms and not all(term in haystack for term in query_terms):
                continue
            matches.append(spec)
        if not matches:
            configured = sorted(self._servers())
            suffix = "; yapılandırılmış sunucular: " + ", ".join(configured) if configured else "; yapılandırılmış MCP sunucusu yok"
            return "Eşleşen MCP aracı bulunamadı" + suffix + "."
        try:
            limit = max(1, min(int(limit), MCP_SEARCH_MAX_RESULTS))
        except (TypeError, ValueError):
            limit = 20
        shown = matches[:limit]
        lines = [f"MCP araçları: {len(matches)} eşleşme; {len(shown)} tanesi gösteriliyor."]
        lines.extend(f"- {item['name']}: {item['description']}" for item in shown)
        if len(matches) > len(shown):
            lines.append("Daha fazlası için aramayı daralt veya limit değerini artır.")
        return "\n".join(lines)

    def requires_confirmation(self, exposed_name):
        if exposed_name not in self._tool_map:
            self.tool_specs()
        entry = self._tool_map.get(exposed_name)
        if entry is None:
            return True
        tool_name = entry[2].casefold()
        if tool_name.startswith("omniroute_"):
            tool_name = tool_name[len("omniroute_"):]
        read_only_prefixes = (
            "get_", "list_", "search_", "find_", "read_", "query_", "describe_",
            "inspect_", "status_", "health_", "check_", "fetch_", "count_", "whoami",
        )
        return not tool_name.startswith(read_only_prefixes)

    async def _call_server(self, definition, tool_name, arguments):
        async with stdio_client(self._params("call", definition)) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments=arguments)
                chunks = []
                for item in result.content:
                    if getattr(item, "type", "") == "text":
                        chunks.append(item.text)
                if not chunks and result.structuredContent is not None:
                    chunks.append(json.dumps(result.structuredContent, ensure_ascii=False))
                text = "\n".join(chunks).strip() or "MCP sunucusu boş yanıt verdi."
                if result.isError:
                    return f"MCP araç hatası: {text}"
                if len(text) > 500_000:
                    text = text[:500_000] + "\n[Sonuç yerel olarak kısaltıldı.]"
                return text

    def call_tool(self, exposed_name, arguments):
        if exposed_name not in self._tool_map:
            self.tool_specs()
        entry = self._tool_map.get(exposed_name)
        if entry is None:
            return "Bu MCP aracı artık kullanılabilir değil; MCP yapılandırmasını kontrol edip JARVIS'i yeniden başlat."
        _server_name, definition, tool_name, _description = entry
        try:
            return asyncio.run(asyncio.wait_for(
                self._call_server(definition, tool_name, arguments or {}),
                timeout=MCP_TOOL_TIMEOUT_SECONDS,
            ))
        except Exception as error:
            self.on_error(f"MCP aracı {exposed_name} başarısız: {type(error).__name__}: {error}")
            return f"MCP aracı çalıştırılamadı ({type(error).__name__}); Resolve'ın açık ve MCP ayarlarının doğru olduğunu kontrol et."
