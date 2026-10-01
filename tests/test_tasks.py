import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import jarvis_claude as jarvis
import jarvis_tasks as jt


class TaskJournalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "tasks"

    def tearDown(self):
        self.tmp.cleanup()

    def test_lifecycle_and_persistence(self):
        j = jt.TaskJournal(self.root)
        tid = j.start("sunum hazırla", "gemini", "masaüstü")
        j.record_step(tid, "create_presentation", {"file_name": "x"}, True, "Kaydedildi")
        j.finish(tid, jt.COMPLETED, "Hazır")
        task = jt.TaskJournal(self.root).get(tid)
        self.assertEqual(task["status"], jt.COMPLETED)
        self.assertEqual(task["steps"][0]["tool"], "create_presentation")
        self.assertEqual(task["result"], "Hazır")
        j.record_step(tid, "late", {}, True, "x")  # bitmiş göreve adım eklenmez
        self.assertEqual(len(j.get(tid)["steps"]), 1)
        self.assertFalse(list(self.root.glob("*.tmp")))

    def test_crash_leaves_task_resumable_after_restart(self):
        j = jt.TaskJournal(self.root)
        tid = j.start("oyunu yaz ve çalıştır", "claude")
        j.record_step(tid, "write_project_file", {"filename": "main.py"}, True, "Yazıldı")
        j.record_step(tid, "run_project", {"entry": "main.py"}, False, "Hata: SyntaxError")
        # süreç burada ölür: finish çağrılmaz
        restarted = jt.TaskJournal(self.root)
        found = restarted.recover_interrupted()
        self.assertEqual([t["id"] for t in found], [tid])
        self.assertEqual(restarted.get(tid)["status"], jt.INTERRUPTED)
        self.assertEqual(restarted.recover_interrupted(), [])  # yalnızca bir kez
        prompt = restarted.resume_prompt(restarted.get(tid))
        self.assertIn("oyunu yaz ve çalıştır", prompt)
        self.assertIn("write_project_file", prompt)
        self.assertNotIn("SyntaxError", prompt)  # yalnızca başarılı adımlar "tamamlandı" sayılır

    def test_secrets_never_reach_disk(self):
        j = jt.TaskJournal(self.root)
        tid = j.start("api_key=sk-abcdefghijklmnopqrstuv ile bağlan")
        j.record_step(tid, "login", {"password": "hunter2", "user": "ali", "accessToken": "zzz"}, True,
                      "token=abcdef1234567890 tamam")
        raw = "".join(p.read_text(encoding="utf-8") for p in self.root.glob("*.json"))
        for secret in ("sk-abcdefghijklmnop", "hunter2", "zzz", "abcdef1234567890"):
            self.assertNotIn(secret, raw)
        self.assertIn("ali", raw)

    def test_rejects_bad_ids_and_prunes_old_tasks(self):
        j = jt.TaskJournal(self.root)
        with self.assertRaises(ValueError):
            j.get("../../etc/passwd")
        ids = []
        for i in range(jt.MAX_TASKS_KEPT + 5):
            ids.append(j.start(f"t{i}"))
            j.finish(ids[-1])
        self.assertLessEqual(len(list(self.root.glob("task_*.json"))), jt.MAX_TASKS_KEPT)


class TaskIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.journal = jt.TaskJournal(Path(self.tmp.name))
        self.tools = jarvis.Tools.__new__(jarvis.Tools)
        self.tools.app = None
        self.tools.journal = self.journal
        self.tools.t_echo = lambda text="": f"echo {text}"

    def tearDown(self):
        self.tmp.cleanup()

    def test_tool_calls_are_recorded_only_inside_a_task(self):
        self.tools.current_task = None
        self.tools.run("echo", {"text": "a"})
        tid = self.journal.start("x")
        self.tools.current_task = tid
        self.assertEqual(self.tools.run("echo", {"text": "b"}), ("echo b", False))
        self.assertEqual(self.tools.run("nope", {})[1], True)
        steps = self.journal.get(tid)["steps"]
        self.assertEqual([(s["tool"], s["ok"]) for s in steps], [("echo", True), ("nope", False)])

    def test_app_tracked_marks_completed_or_failed(self):
        app = jarvis.App.__new__(jarvis.App)
        app.tools = self.tools
        app.provider = "gemini"
        self.assertEqual(app._tracked("selam", "telefon", lambda: "merhaba"), "merhaba")

        def boom():
            raise RuntimeError("çöktü")
        with self.assertRaises(RuntimeError):
            app._tracked("bozuk", "masaüstü", boom)
        statuses = {t["text"]: (t["status"], t["source"]) for t in self.journal.all()}
        self.assertEqual(statuses["selam"], (jt.COMPLETED, "telefon"))
        self.assertEqual(statuses["bozuk"], (jt.FAILED, "masaüstü"))
        self.assertIsNone(self.tools.current_task)

    def test_tasks_tool_lists_resumes_and_cancels(self):
        tid = self.journal.start("rapor hazırla")
        self.journal.record_step(tid, "echo", {}, True, "ilk bölüm")
        self.journal.recover_interrupted()
        self.assertIn("INTERRUPTED", self.tools.t_tasks("list"))
        prompt = self.tools.t_tasks("resume")
        self.assertIn("rapor hazırla", prompt)
        self.assertEqual(self.journal.get(tid)["status"], jt.RESUMED)
        self.assertIn("bulunamadı", self.tools.t_tasks("resume"))
        other = self.journal.start("ikinci")
        self.journal.recover_interrupted()
        self.assertIn("kapatıldı", self.tools.t_tasks("cancel", other))
        self.assertIn("durumu", self.tools.t_tasks("resume", other))
        self.assertIn("geçersiz", self.tools.t_tasks("resume", "../x"))
        self.assertIn("tasks", {t.get("name") for t in jarvis.TOOLS})
        self.assertIn('"tasks"', json.dumps(jarvis._gemini_tool_specs()))


if __name__ == "__main__":
    unittest.main()
