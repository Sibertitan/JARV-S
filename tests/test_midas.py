import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import jarvis_claude as jarvis
import jarvis_midas as midas


class MidasSimulatorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def sim(self, **kw):
        return midas.MidasSimulator(self.dir / "state.json", self.dir / "audit.jsonl", **kw)

    def test_live_mode_is_refused_and_auto_execution_is_off(self):
        with self.assertRaisesRegex(midas.MidasError, "resmi"):
            self.sim(mode="LIVE")
        with self.assertRaises(midas.MidasError):
            self.sim(mode="WHATEVER")
        self.assertFalse(midas.AUTO_EXECUTION)
        self.assertFalse(self.sim().status()["auto_execution"])

    def test_account_portfolio_and_quotes_are_synthetic(self):
        s = self.sim()
        p = s.portfolio()
        self.assertTrue(p["simulated"])
        self.assertEqual(p["cash"]["TRY"], 100_000.0)
        self.assertEqual(p["positions"], [])
        q = s.quote("sim.thyao")
        self.assertEqual((q["symbol"], q["currency"], q["simulated"]), ("SIM.THYAO", "TRY", True))
        with self.assertRaises(midas.MidasError):
            s.quote("THYAO")  # gerçek semboller simülasyonda sunulmaz

    def test_order_waits_for_approval_then_fills_and_persists(self):
        s = self.sim()
        o = s.place_order("SIM.THYAO", "BUY", 10)
        self.assertEqual(o["status"], midas.PENDING)
        self.assertEqual(s.portfolio()["cash"]["TRY"], 100_000.0)  # onaysız işlem yok
        o = s.approve(o["id"], "Aliihsan")
        self.assertEqual(o["status"], midas.FILLED)
        self.assertEqual(o["fills"][0]["price"], 300.0)
        with self.assertRaises(midas.MidasError):
            s.approve(o["id"], "Aliihsan")  # iki kez gerçekleşmez
        sell = s.approve(s.place_order("SIM.THYAO", "SELL", 4)["id"], "Aliihsan")
        self.assertEqual(sell["status"], midas.FILLED)
        reopened = self.sim()  # yeniden başlatma: durum diskten gelir
        p = reopened.portfolio()
        self.assertEqual(p["cash"]["TRY"], 100_000.0 - 3000.0 + 1200.0)
        self.assertEqual(p["positions"][0]["quantity"], 6)

    def test_rejections(self):
        s = self.sim(max_order_value=200_000)
        cases = [
            (("SIM.THYAO", "BUY", 0), "pozitif"),
            (("SIM.THYAO", "SELL", 1), "açığa satış yok"),
            (("SIM.AAPL", "BUY", 30), "yetersiz USD"),
            (("SIM.THYAO", "BUY", 1, "LIMIT"), "limit_price"),
            (("SIM.THYAO", "BUY", 1, "MARKET", 10), "piyasa emrinde"),
            (("NOPE", "BUY", 1), "simülasyonda yok"),
            (("SIM.THYAO", "HOLD", 1), "BUY veya SELL"),
        ]
        for args, reason in cases:
            o = s.place_order(*args)
            self.assertEqual(o["status"], midas.REJECTED, args)
            self.assertTrue(any(reason in r for r in o["reasons"]), (args, o["reasons"]))
            with self.assertRaises(midas.MidasError):
                s.approve(o["id"], "Aliihsan")
        small = self.sim(max_order_value=1_000)
        self.assertIn("üst sınırı", small.place_order("SIM.THYAO", "BUY", 10)["reasons"][0])

    def test_read_only_mode_refuses_orders(self):
        o = self.sim(mode="READ_ONLY").place_order("SIM.THYAO", "BUY", 1)
        self.assertEqual(o["status"], midas.REJECTED)
        self.assertIn("READ_ONLY", o["reasons"][0])

    def test_limit_not_marketable_stays_open_and_can_be_cancelled(self):
        s = self.sim()
        o = s.approve(s.place_order("SIM.THYAO", "BUY", 1, "LIMIT", 250)["id"], "Aliihsan")
        self.assertEqual(o["status"], midas.OPEN)
        self.assertEqual(o["fills"], [])
        self.assertEqual(s.cancel(o["id"])["status"], midas.CANCELLED)

    def test_backend_failure_is_reported_and_causes_no_partial_execution(self):
        s = self.sim()
        o = s.place_order("SIM.THYAO", "BUY", 1)
        s.inject_failure()
        with self.assertRaises(midas.MidasBackendFailure):
            s.approve(o["id"], "Aliihsan")
        self.assertEqual(s.orders(midas.PENDING)[0]["id"], o["id"])
        self.assertEqual(s.portfolio()["cash"]["TRY"], 100_000.0)

    def test_approval_revalidates_after_price_move(self):
        s = midas.MidasSimulator(self.dir / "s2.json", mode="SIMULATION")
        s.state["cash"]["TRY"] = 3_500.0
        o = s.place_order("SIM.THYAO", "BUY", 10)
        self.assertEqual(o["status"], midas.PENDING)
        s.state["prices"]["SIM.THYAO"] = 400.0
        o = s.approve(o["id"], "Aliihsan")
        self.assertEqual(o["status"], midas.REJECTED)
        self.assertIn("yetersiz", o["reasons"][0])

    def test_audit_log_records_actions(self):
        s = self.sim()
        s.approve(s.place_order("SIM.ASELS", "BUY", 5)["id"], "Aliihsan")
        rows = [json.loads(line) for line in (self.dir / "audit.jsonl").read_text(encoding="utf-8").splitlines()]
        actions = [r["action"] for r in rows]
        self.assertIn("order.place", actions)
        self.assertIn("order.approve", actions)
        self.assertTrue(all(r["simulated"] for r in rows))


class MidasToolTests(unittest.TestCase):
    def tools(self, tmp, confirm):
        t = jarvis.Tools.__new__(jarvis.Tools)
        calls = []

        def ask(title, text):
            calls.append((title, text))
            return confirm
        t.app = SimpleNamespace(ask_confirm=ask)
        t._midas = midas.MidasSimulator(Path(tmp) / "s.json")
        return t, calls

    def test_tool_is_registered_for_all_providers(self):
        self.assertIn("midas", {item.get("name") for item in jarvis.TOOLS})
        self.assertIn('"midas"', json.dumps(jarvis._gemini_tool_specs()))

    def test_order_requires_desktop_confirmation(self):
        with tempfile.TemporaryDirectory() as tmp:
            t, calls = self.tools(tmp, confirm=False)
            o = json.loads(t.t_midas("order", symbol="SIM.THYAO", side="BUY", quantity=2))
            self.assertEqual(o["status"], midas.PENDING)
            self.assertEqual(calls, [])  # emir oluşturmak onay penceresi açmaz, gerçekleştirmez
            out = t.t_midas("approve", order_id=o["id"])
            self.assertIn("onaylamadı", out)
            self.assertIn("SİMÜLASYON", calls[0][1])
            self.assertEqual(t._midas.orders(midas.PENDING)[0]["id"], o["id"])

            t2, _ = self.tools(tmp, confirm=True)
            t2._midas = t._midas
            filled = json.loads(t2.t_midas("approve", order_id=o["id"]))
            self.assertEqual(filled["status"], midas.FILLED)

    def test_tool_reports_errors_without_crashing(self):
        with tempfile.TemporaryDirectory() as tmp:
            t, _ = self.tools(tmp, confirm=True)
            self.assertIn("simülasyonda yok", t.t_midas("quote", symbol="THYAO"))
            self.assertIn("bulunamadı", t.t_midas("approve", order_id="x"))
            self.assertIn("action", t.t_midas("explode"))
            t.app = None
            o = json.loads(t.t_midas("order", symbol="SIM.SPY", side="BUY", quantity=1))
            self.assertIn("masaüstü onay", t.t_midas("approve", order_id=o["id"]))

    def test_live_mode_config_is_refused_via_tool(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = jarvis.Tools.__new__(jarvis.Tools)
            t.app = None
            with patch.object(jarvis, "load_json", return_value={"midas_mode": "LIVE"}), \
                    patch.object(jarvis, "BASE", Path(tmp)):
                self.assertIn("resmi", t.t_midas("status"))


if __name__ == "__main__":
    unittest.main()
