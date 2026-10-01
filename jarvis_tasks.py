"""Görev günlüğü (checkpoint): JARVIS kapanırsa yarım kalan işi kaldığı yerden sürdürmek için.

Her kullanıcı isteği bir görevdir. Görev başlarken, her araç adımından sonra ve bitince durumu
memory/tasks/<id>.json dosyasına atomik olarak yazılır. JARVIS yeniden açıldığında hâlâ RUNNING
görünen görevler önceki oturumda yarıda kalmıştır; bunlar INTERRUPTED olarak işaretlenir ve
kullanıcıya devam etmesi önerilir. Devam ederken model, tamamlanan adımların özetini alır ve
yalnızca kalan işi yapar.

Gizli bilgiler (parola, API anahtarı, token, çerez, MFA kodu, özel anahtar) diske yazılmadan önce
gizlenir.
"""

import json
import os
import re
import tempfile
import threading
import time
import uuid
from pathlib import Path

RUNNING, COMPLETED, FAILED, INTERRUPTED, RESUMED, CANCELLED = (
    "RUNNING", "COMPLETED", "FAILED", "INTERRUPTED", "RESUMED", "CANCELLED")
MAX_STEPS_KEPT = 60     # görev başına saklanan en fazla adım
MAX_TASKS_KEPT = 50     # diskte tutulan en fazla görev
SUMMARY_CHARS = 300

_SECRET_KEY = re.compile(
    r"(?:^|[_.-])(?:password|passwd|parola|sifre|şifre|secret|api[_-]?key|apikey|token|cookie|"
    r"session[_-]?id|authorization|mfa|otp|private[_-]?key|credential)s?(?:$|[_.-])", re.I)
_SECRET_VALUE = [
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S),
    re.compile(r"(?i)\b[\w-]*(?:password|parola|şifre|sifre|secret|api[_-]?key|token|cookie|mfa|otp)"
               r"[\w-]*\s*[:=]\s*\S+"),
    re.compile(r"(?i)\b(?:bearer|basic)\s+[A-Za-z0-9._~+/=-]{8,}"),
    re.compile(r"\b(?:sk-|sk-ant-|gh[pousr]_|AIza|xox[abposr]-)[A-Za-z0-9_-]{12,}"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}"),
]


def redact(value):
    """Sözlük/liste/metin içindeki gizli bilgileri '[gizlendi]' ile değiştirir."""
    if isinstance(value, str):
        for pattern in _SECRET_VALUE:
            value = pattern.sub("[gizlendi]", value)
        return value
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            snake = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", str(k))
            out[k] = "[gizlendi]" if _SECRET_KEY.search(snake) and v not in (None, "") else redact(v)
        return out
    if isinstance(value, (list, tuple)):
        return [redact(v) for v in value]
    return value


def _short(value, limit=SUMMARY_CHARS):
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)
    text = redact(text)
    return text if len(text) <= limit else text[:limit] + "…"


class TaskJournal:
    def __init__(self, root):
        self.root = Path(root)
        self._lock = threading.Lock()

    def _path(self, task_id):
        if not re.fullmatch(r"task_[0-9a-f]{12}", str(task_id)):
            raise ValueError(f"geçersiz görev kimliği: {task_id}")
        return self.root / f"{task_id}.json"

    def _write(self, task):
        self.root.mkdir(parents=True, exist_ok=True)
        task["updated"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        fd, tmp = tempfile.mkstemp(dir=self.root, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(task, f, ensure_ascii=False, indent=1)
            os.replace(tmp, self._path(task["id"]))
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    def get(self, task_id):
        path = self._path(task_id)  # geçersiz kimlik ValueError verir (yol dışına çıkış yok)
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None

    def all(self):
        tasks = []
        if self.root.is_dir():
            for p in self.root.glob("task_*.json"):
                try:
                    tasks.append(json.loads(p.read_text(encoding="utf-8")))
                except (OSError, ValueError):
                    continue
        return sorted(tasks, key=lambda t: t.get("created", ""), reverse=True)

    def start(self, text, provider="", source="masaüstü", resumed_from=None):
        with self._lock:
            task = {"id": "task_" + uuid.uuid4().hex[:12], "text": redact(str(text))[:2000],
                    "provider": provider, "source": source, "status": RUNNING,
                    "created": time.strftime("%Y-%m-%dT%H:%M:%S"), "steps": [],
                    "result": None, "resumed_from": resumed_from}
            self._write(task)
            self._prune()
            return task["id"]

    def record_step(self, task_id, tool, args, ok, result):
        with self._lock:
            task = self.get(task_id)
            if task is None or task["status"] != RUNNING:
                return
            task["steps"].append({"tool": str(tool), "args": _short(redact(args or {})), "ok": bool(ok),
                                  "result": _short(result), "ts": time.strftime("%H:%M:%S")})
            task["steps"] = task["steps"][-MAX_STEPS_KEPT:]
            self._write(task)

    def finish(self, task_id, status=COMPLETED, result=None):
        with self._lock:
            task = self.get(task_id)
            if task is None or task["status"] != RUNNING:
                return
            task["status"] = status
            task["result"] = _short(result or "", 1000)
            self._write(task)

    def set_status(self, task_id, status):
        with self._lock:
            task = self.get(task_id)
            if task is None:
                return None
            task["status"] = status
            self._write(task)
            return task

    def recover_interrupted(self):
        """Önceki oturumda RUNNING kalmış görevleri INTERRUPTED yapar ve döndürür (açılışta bir kez)."""
        found = []
        for task in self.all():
            if task.get("status") == RUNNING:
                found.append(self.set_status(task["id"], INTERRUPTED))
        return found

    def resume_prompt(self, task):
        done = [s for s in task.get("steps", []) if s.get("ok")]
        lines = [f"- {s['tool']}({s['args']}) → {s['result']}" for s in done[-20:]]
        older = len(done) - len(lines)
        steps = ("\n".join(lines) if lines else "(kaydedilmiş başarılı adım yok)")
        if older > 0:
            steps = f"(daha önce {older} adım daha tamamlandı)\n" + steps
        return ("Bu görev önceki oturumda yarıda kaldı; kaldığın yerden devam et. Tamamlanmış adımları "
                "tekrarlama, sonucu belirsiz olanı önce kontrol et.\n\n"
                f"Asıl istek: {task.get('text', '')}\n\nTamamlanan adımlar:\n{steps}")

    def _prune(self):
        tasks = self.all()
        for task in tasks[MAX_TASKS_KEPT:]:
            if task.get("status") != RUNNING:
                try:
                    self._path(task["id"]).unlink()
                except OSError:
                    pass
