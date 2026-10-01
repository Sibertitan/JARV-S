import unittest
import http.server
import json
import tempfile
import threading
import urllib.request
import urllib.error
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import patch

import jarvis_claude as jarvis
from jarvis_mcp import MCPToolBridge


class RuntimeTests(unittest.TestCase):
    def _echo_mcp_config(self):
        config_path = Path(__file__).parent.parent / "work" / "mcp_test_config.json"
        config_path.parent.mkdir(exist_ok=True)
        config_path.write_text(json.dumps({"mcpServers": {
            "echo": {
                "command": sys.executable,
                "args": [str(Path(__file__).with_name("mcp_echo_server.py"))],
                "cwd": str(Path(__file__).resolve().parents[1]),
            }
        }}), encoding="utf-8")
        return config_path

    def test_history_is_bounded_and_keeps_recent_turns(self):
        history = [
            {"role": "user", "content": "x" * 5000},
            {"role": "assistant", "content": "older"},
            {"role": "user", "content": "latest"},
        ]
        bounded = jarvis._bounded_chat_history(history)
        self.assertEqual(bounded[-1]["content"], "latest")
        self.assertLessEqual(len(bounded), jarvis.CHAT_HISTORY_MAX_MESSAGES)
        self.assertLessEqual(sum(len(item["content"]) for item in bounded),
                             jarvis.CHAT_HISTORY_MAX_CHARS)

    def test_gemini_tool_schema_exposes_kali_search(self):
        tool = next(item for item in jarvis.TOOLS if item.get("name") == "kali_tool")
        self.assertIn("tool_search", tool["input_schema"]["properties"]["action"]["enum"])
        self.assertIn("search_history", {item.get("name") for item in jarvis.TOOLS})
        switch = next(item for item in jarvis.TOOLS if item.get("name") == "switch_brain")
        self.assertIn("omniroute", switch["input_schema"]["properties"]["provider"]["enum"])
        self.assertFalse({"lab_session", "lab_test", "sec_orchestrate"} & {item.get("name") for item in jarvis.TOOLS})

    def test_kali_installer_blocks_offensive_packages(self):
        tools = jarvis.Tools.__new__(jarvis.Tools)
        with patch.object(jarvis.sys, "platform", "linux"):
            result = tools.t_kali_tool("install", "metasploit-framework")
        self.assertIn("kurulmayacak", result)

    def test_openai_compatible_agent_uses_local_gateway_without_key(self):
        with patch.object(jarvis, "_post_json", return_value={
            "choices": [{"message": {"content": "routed locally"}}]
        }) as post:
            result = jarvis.gpt_agent(
                "", [], "ctx", object(), base_url="http://127.0.0.1:20128/v1", model="auto"
            )
        self.assertEqual(result, "routed locally")
        url, headers, payload = post.call_args.args
        self.assertEqual(url, "http://127.0.0.1:20128/v1/chat/completions")
        self.assertEqual(headers, {})
        self.assertEqual(payload["model"], "auto")

    def test_omniroute_endpoint_defaults_to_loopback_and_rejects_remote_hosts(self):
        self.assertEqual(jarvis._omniroute_url({}), "http://127.0.0.1:20128/v1")
        with self.assertRaises(ValueError):
            jarvis._omniroute_url({"omniroute_url": "https://example.com/v1"})

    def test_omniroute_gateway_autostart_uses_package_cli_not_mcp_wrapper(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package_root = root / "node_modules" / "omniroute"
            cli_entry = package_root / "bin" / "omniroute.mjs"
            cli_entry.parent.mkdir(parents=True)
            cli_entry.touch()
            mcp_path = root / "config" / "mcp_servers.json"
            mcp_path.parent.mkdir()
            mcp_path.write_text(json.dumps({"mcpServers": {"omniroute": {
                "command": "node",
                "args": [str(root / "omniroute_mcp_stdio.mjs")],
                "env": {"OMNIROUTE_PACKAGE_ROOT": str(package_root)},
            }}}), encoding="utf-8")
            with patch.object(jarvis, "CONFIG_FILE", root / "config" / "api_keys.json"):
                self.assertEqual(
                    jarvis._omniroute_launch_spec({}),
                    ("node", [str(cli_entry)], str(package_root)),
                )

    def test_gemini_quota_falls_back_to_configured_omniroute(self):
        class Queue:
            def put(self, _item):
                pass

        app = jarvis.App.__new__(jarvis.App)
        app.chat_history = []
        app.provider = "gemini"
        app.tools = object()
        app.q = Queue()
        app._provider_fallback = lambda _text, _reason: "offline fallback"
        error = urllib.error.HTTPError("https://example.invalid", 429, "quota", {}, None)
        with patch.object(jarvis, "load_json", return_value={
            "gemini_api_key": "unit-test-key",
            "omniroute_url": "http://127.0.0.1:20128/v1",
        }), patch.object(jarvis, "dynamic_context", return_value="ctx"), \
             patch.object(jarvis, "gemini_agent", side_effect=error), \
             patch.object(jarvis, "omniroute_agent", return_value="via local route"), \
             patch.object(jarvis, "log"):
            self.assertEqual(app._alt_chat("test quota"), "via local route")
        self.assertEqual([item["role"] for item in app.chat_history], ["user", "assistant"])

    def test_gemini_schema_flattens_optional_union_and_local_ref(self):
        schema = {
            "$defs": {"Options": {
                "type": "object",
                "properties": {"limit": {"anyOf": [{"type": "integer"}, {"type": "null"}], "default": None}},
            }},
            "type": "object",
            "properties": {"params": {"anyOf": [{"$ref": "#/$defs/Options"}, {"type": "null"}]}},
            "additionalProperties": False,
        }
        clean = jarvis._gemini_clean(schema)
        self.assertEqual(clean["properties"]["params"]["properties"]["limit"]["type"], "integer")
        self.assertNotIn("anyOf", json.dumps(clean))
        self.assertNotIn("$ref", json.dumps(clean))
        self.assertNotIn("additionalProperties", json.dumps(clean))

    def test_gemini_function_response_preserves_call_id(self):
        class Tools:
            def run(self, _name, _args):
                return "done", False

        responses = [
            {"candidates": [{"content": {"role": "model", "parts": [
                {"functionCall": {"name": "sample_tool", "id": "call-123", "args": {"x": 1}}}
            ]}}]},
            {"candidates": [{"content": {"role": "model", "parts": [{"text": "ok"}]}}]},
        ]
        with patch.object(jarvis, "_post_json", side_effect=responses) as post:
            self.assertEqual(jarvis.gemini_agent("key", [], "ctx", Tools()), "ok")
        second_payload = post.call_args_list[1].args[2]
        function_response = next(
            part["functionResponse"]
            for message in second_payload["contents"]
            for part in message.get("parts", [])
            if "functionResponse" in part
        )
        self.assertEqual(function_response["id"], "call-123")

    def test_history_search_reads_local_conversation_log(self):
        log_path = Path(__file__).parent / "fixtures" / "history.log"
        tools = jarvis.Tools.__new__(jarvis.Tools)
        with patch.object(jarvis, "LOG_FILE", log_path):
            result = tools.t_search_history("mesh local")
        self.assertIn("mesh code uses local network", result)
        self.assertNotIn("unrelated note", result)

    def test_mcp_stdio_discovery_and_tool_call(self):
        config_path = self._echo_mcp_config()
        bridge = MCPToolBridge(config_path)
        specs = bridge.tool_specs()
        self.assertEqual(len(specs), 1)
        self.assertEqual(specs[0]["name"], "mcp__echo__echo")
        self.assertIn("mcp__echo__echo", bridge.search_tools("echo"))
        self.assertTrue(bridge.requires_confirmation(specs[0]["name"]))
        self.assertEqual(bridge.call_tool(specs[0]["name"], {"text": "hello"}), "echo: hello")

    def test_omniroute_read_only_tools_skip_mutation_confirmation(self):
        bridge = MCPToolBridge(Path(__file__).parent / "missing.json")
        bridge._tool_map = {
            "health": ("omniroute", {}, "omniroute_get_health", "health"),
            "route": ("omniroute", {}, "omniroute_route_request", "route"),
        }
        self.assertFalse(bridge.requires_confirmation("health"))
        self.assertTrue(bridge.requires_confirmation("route"))

    def test_mcp_call_wrapper_requires_local_confirmation_for_mutations(self):
        config_path = self._echo_mcp_config()
        bridge = MCPToolBridge(config_path)
        approved = []
        tools = jarvis.Tools.__new__(jarvis.Tools)
        tools.mcp = bridge
        tools.app = SimpleNamespace(ask_confirm=lambda title, body: approved.append((title, body)) or True)
        result = tools.t_mcp_call_tool("mcp__echo__echo", '{"text":"hello"}')
        self.assertEqual(result, "echo: hello")
        self.assertEqual(len(approved), 1)

    def test_mcp_tools_are_discovered_on_demand_not_sent_as_bulk_schemas(self):
        names = {item.get("name") for item in jarvis.TOOLS}
        self.assertIn("mcp_list_tools", names)
        self.assertIn("mcp_call_tool", names)
        self.assertNotIn("mcp__", json.dumps(jarvis._gemini_tool_specs()))
        self.assertFalse({"lab_session", "lab_test", "sec_orchestrate"} & names)

    def test_headroom_compresses_large_tool_output_without_provider_calls(self):
        if jarvis._headroom_compress is None:
            self.skipTest("Headroom is an optional runtime dependency")
        text = json.dumps({"rows": [
            {"id": i, "status": "ok", "message": "routine operation completed successfully"}
            for i in range(300)
        ]})
        compact = jarvis._compress_tool_output(text, "gemini-2.5-flash")
        self.assertLess(len(compact), len(text))
        self.assertIn("routine operation completed successfully", compact)

    def test_headroom_failure_fails_open(self):
        text = "x" * 7000
        with patch.object(jarvis, "_headroom_compress", side_effect=RuntimeError):
            self.assertEqual(jarvis._compress_tool_output(text, "gemini-2.5-flash"), text)

    def test_session_memory_and_observations_roundtrip(self):
        names = {item.get("name") for item in jarvis.TOOLS}
        self.assertTrue({"remember_session", "recall_sessions",
                         "observe_self", "review_observations"} <= names)
        with tempfile.TemporaryDirectory() as tmp:
            session_file = Path(tmp) / "session_memory.jsonl"
            obs_file = Path(tmp) / "observations.jsonl"
            with patch.object(jarvis, "SESSION_MEMORY_FILE", session_file), \
                 patch.object(jarvis, "OBSERVATIONS_FILE", obs_file):
                tools = jarvis.Tools(None)
                tools.t_remember_session("OmniRoute yapılandırıldı ve testler geçti.",
                                         tags="omniroute,test")
                tools.t_observe_self("preference", "Kullanıcı tam çözüm ister",
                                     suggestion="Kısa özetten kaçın")
                self.assertIn("omniroute", tools.t_recall_sessions("omniroute").lower())
                self.assertEqual("Bu sözcüklerle eşleşen oturum özeti bulunamadı.",
                                 tools.t_recall_sessions("bulunmayansozcuk"))
                self.assertIn("tam çözüm", tools.t_review_observations("preference"))
                # Oturum özetleri yeni oturumun bağlamına geri yüklenir
                self.assertIn("OmniRoute yapılandırıldı", jarvis.dynamic_context())

    def test_code_run_writes_and_executes_and_captures_output(self):
        names = {item.get("name") for item in jarvis.TOOLS}
        self.assertIn("code_run", names)
        with tempfile.TemporaryDirectory() as tmp:
            app = SimpleNamespace(ask_confirm=lambda *a, **k: True)
            tools = jarvis.Tools.__new__(jarvis.Tools)
            tools.app = app
            with patch.object(jarvis.Tools, "_projects_dir", staticmethod(lambda: Path(tmp))):
                out = tools.t_code_run("print('codex hazir', 2 + 2)", language="python")
        self.assertIn("codex hazir 4", out)
        self.assertIn("çıkış kodu 0", out)

    def test_code_run_respects_execution_denial(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = SimpleNamespace(ask_confirm=lambda *a, **k: False)
            tools = jarvis.Tools.__new__(jarvis.Tools)
            tools.app = app
            with patch.object(jarvis.Tools, "_projects_dir", staticmethod(lambda: Path(tmp))):
                out = tools.t_code_run("print('calismamali')", language="python")
            self.assertIn("onaylamadı", out)
            # Kod yine de dosyaya yazılmış olmalı (yaz→sonra çalıştır ayrımı)
            self.assertTrue(any(p.suffix == ".py" for p in Path(tmp).rglob("*.py")))

    def test_recommend_setup_is_read_only_and_prioritized(self):
        names = {item.get("name") for item in jarvis.TOOLS}
        self.assertIn("recommend_setup", names)
        with tempfile.TemporaryDirectory() as tmp:
            missing_cfg = Path(tmp) / "api_keys.json"
            with patch.object(jarvis, "CONFIG_FILE", missing_cfg), \
                 patch.object(jarvis, "SESSION_MEMORY_FILE", Path(tmp) / "s.jsonl"):
                out = jarvis.Tools(None).t_recommend_setup()
        # Anahtar yoksa yüksek öncelikli sağlayıcı önerisi görünmeli
        self.assertIn("Gemini API anahtarı yok", out)
        self.assertIn("[yüksek]", out)
        # Salt okunur olduğunu açıkça bildirmeli
        self.assertIn("değiştirmedim", out)

    def test_headless_self_test_skips_unconfigured_mcp(self):
        missing_config = Path(__file__).parent.parent / "work" / "missing-mcp-config.json"
        with patch.object(jarvis, "CONFIG_FILE", missing_config):
            self.assertEqual(jarvis._run_self_test(), 0)

    def test_headless_self_test_failure_reports_cause(self):
        import io
        logged = []
        stderr = io.StringIO()
        with patch.object(jarvis, "_compress_tool_output", side_effect=RuntimeError("headroom bozuk")), \
                patch.object(jarvis, "log", logged.append), patch.object(jarvis.sys, "stderr", stderr):
            self.assertEqual(jarvis._run_self_test(), 1)
        self.assertIn("headroom bozuk", stderr.getvalue())
        self.assertTrue(any("headroom bozuk" in line for line in logged))

    def test_gemini_429_fallback_keeps_chat_turn_alternating(self):
        class Queue:
            def put(self, _item):
                pass

        app = jarvis.App.__new__(jarvis.App)
        app.chat_history = []
        app.provider = "gemini"
        app.tools = object()
        app.q = Queue()
        app._provider_fallback = lambda _text, reason: f"fallback: {reason}"
        error = urllib.error.HTTPError("https://example.invalid", 429, "quota", {}, None)
        with patch.object(jarvis, "gemini_agent", side_effect=error), \
             patch.object(jarvis, "_omniroute_launch_spec", return_value=None), \
             patch.object(jarvis, "log") as logger:
            response = app._alt_chat("test quota fallback")
        self.assertIn("fallback", response)
        self.assertEqual([item["role"] for item in app.chat_history], ["user", "assistant"])
        self.assertTrue(any("kullanıcı: test quota fallback" in str(call) for call in logger.call_args_list))
        self.assertTrue(any("jarvis: fallback" in str(call) for call in logger.call_args_list))

    def test_phone_server_ping_and_ask_contract(self):
        class Queue:
            def put(self, _item):
                pass

        servers = []
        base_server = http.server.ThreadingHTTPServer

        class EphemeralServer(base_server):
            def __init__(self, address, handler):
                super().__init__((address[0], 0), handler)
                servers.append(self)

        app = jarvis.App.__new__(jarvis.App)
        app._write = lambda *_args: None
        app.machine_name = "Test JARVIS"
        app.provider = "gemini"
        app.busy = False
        app.stop_event = threading.Event()
        app.q = Queue()
        app._restore = lambda: None
        app.on_ui = lambda callback: callback()
        app._alt_chat = lambda text: f"echo: {text}"

        with patch.object(http.server, "ThreadingHTTPServer", EphemeralServer):
            app._start_phone_server({"phone_token": "t" * 40, "web_remote_access": False})
        server = servers[0]
        try:
            endpoint = f"http://127.0.0.1:{server.server_port}"

            def post(path, token, **fields):
                payload = json.dumps({"token": token, **fields}).encode("utf-8")
                request = urllib.request.Request(endpoint + path, payload,
                                                 {"Content-Type": "application/json"})
                try:
                    response = urllib.request.urlopen(request, timeout=3)
                except urllib.error.HTTPError as error:
                    return error.code, json.loads(error.read())
                with response:
                    return response.status, json.loads(response.read())

            self.assertEqual(post("/ping", "t" * 40)[0], 200)
            self.assertEqual(post("/ask", "t" * 40, text="hello")[1]["reply"], "echo: hello")
            self.assertEqual(post("/ping", "wrong")[0], 403)
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
