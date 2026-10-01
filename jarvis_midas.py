"""JARVIS Midas modülü — yalnızca SİMÜLASYON ve SALT OKUNUR.

Midas'ın resmi, herkese açık bir API'si yok (getmidas.com ve llms.txt'de geliştirici
API'si/programatik hesap erişimi belgelenmiyor). Bu yüzden JARVIS gerçek Midas hesabına
bağlanmaz, uygulamayı kazımaz, gizli uç noktaları taklit etmez ve MFA/CAPTCHA/anti-bot
korumalarını aşmaz. Buradaki her veri sentetiktir: semboller "SIM." önekiyle başlar ve her
yanıtta "simulated": True vardır.

Kurallar:
- AUTO_EXECUTION her zaman False; ayarlarla açılamaz.
- Her emir önce BEKLIYOR (onay bekliyor) olur; kullanıcı onayı olmadan gerçekleşmez.
- Onay anında emir yeniden doğrulanır (fiyat, nakit, pozisyon, limitler).
- Açığa satış yok; emir değeri/adet üst sınırı var.
"""

import json
import os
import random
import tempfile
import threading
import time
import uuid
from pathlib import Path

AUTO_EXECUTION = False  # sabit: otomatik emir yürütme yok

MODES = ("SIMULATION", "READ_ONLY")
LIVE_REFUSAL = (
    "Canlı Midas erişimi yok: Midas'ın resmi, herkese açık bir API'si bulunmuyor. JARVIS gerçek "
    "hesaba bağlanmaz, uygulamayı kazımaz ve MFA/CAPTCHA/anti-bot korumalarını aşmaz. Canlı kullanım "
    "ancak senin cihazında, senin girişinle ve her işlem için ayrı onayınla mümkün olabilir."
)

DEFAULT_PRICES = {"SIM.THYAO": 300.0, "SIM.ASELS": 60.0, "SIM.AAPL": 200.0, "SIM.SPY": 550.0}
CURRENCY = {"SIM.THYAO": "TRY", "SIM.ASELS": "TRY", "SIM.AAPL": "USD", "SIM.SPY": "USD"}
DEFAULT_CASH = {"TRY": 100_000.0, "USD": 5_000.0}

PENDING = "BEKLIYOR"      # kullanıcı onayı bekliyor
FILLED = "GERCEKLESTI"
REJECTED = "REDDEDILDI"
OPEN = "ACIK"             # limit fiyata gelmedi
CANCELLED = "IPTAL"


class MidasError(Exception):
    pass


class MidasBackendFailure(MidasError):
    """Simüle edilmiş ağ/sunucu hatası (testler için)."""


class MidasSimulator:
    def __init__(self, state_path, audit_path=None, mode="SIMULATION", max_order_value=10_000.0,
                 max_quantity=10_000.0, seed=7):
        mode = str(mode or "SIMULATION").upper()
        if mode == "LIVE":
            raise MidasError(LIVE_REFUSAL)
        if mode not in MODES:
            raise MidasError(f"Bilinmeyen Midas modu: {mode}. Geçerli: {', '.join(MODES)}")
        self.mode = mode
        self.state_path = Path(state_path)
        self.audit_path = Path(audit_path) if audit_path else None
        self.max_order_value = float(max_order_value)
        self.max_quantity = float(max_quantity)
        self._rng = random.Random(seed)  # simülasyon; kriptografik değil
        self._lock = threading.Lock()
        self.fail_next = []  # test için hata enjeksiyonu
        self.state = self._load()

    # ── kalıcılık ──
    def _load(self):
        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and "cash" in data:
                return data
        except (OSError, ValueError):
            pass
        return {"account_id": "SIM-HESAP", "cash": dict(DEFAULT_CASH), "positions": {},
                "orders": {}, "prices": dict(DEFAULT_PRICES)}

    def _save(self):
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self.state_path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(self.state, f, ensure_ascii=False, indent=1)
            os.replace(tmp, self.state_path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    def _audit(self, action, **details):
        if self.audit_path is None:
            return
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "action": action, "simulated": True, **details}
        with self.audit_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def _maybe_fail(self):
        if self.fail_next:
            raise self.fail_next.pop(0)

    def inject_failure(self, exc=None):
        self.fail_next.append(exc or MidasBackendFailure("simüle ağ hatası"))

    # ── okuma ──
    def quote(self, symbol):
        self._maybe_fail()
        symbol = str(symbol or "").upper()
        if symbol not in self.state["prices"]:
            raise MidasError(f"'{symbol}' simülasyonda yok. Simüle semboller: "
                             + ", ".join(sorted(self.state["prices"])))
        return {"symbol": symbol, "price": self.state["prices"][symbol],
                "currency": CURRENCY.get(symbol, "TRY"), "simulated": True}

    def portfolio(self):
        self._maybe_fail()
        rows = []
        for sym, p in sorted(self.state["positions"].items()):
            if p["quantity"] <= 0:
                continue
            price = self.state["prices"][sym]
            mv = price * p["quantity"]
            rows.append({"symbol": sym, "quantity": p["quantity"], "avg_cost": p["avg_cost"],
                         "price": price, "currency": CURRENCY.get(sym, "TRY"),
                         "market_value": round(mv, 4),
                         "unrealized_pnl": round(mv - p["avg_cost"] * p["quantity"], 4)})
        self._audit("read.portfolio")
        return {"account_id": self.state["account_id"], "mode": self.mode,
                "cash": dict(self.state["cash"]), "positions": rows, "simulated": True}

    def tick(self):
        """Fiyatları ±%1 rastgele yürütür (yalnızca demo)."""
        for s, p in self.state["prices"].items():
            self.state["prices"][s] = round(p * (1 + self._rng.uniform(-0.01, 0.01)), 4)
        self._save()

    # ── emir ──
    def _validate(self, o):
        reasons = []
        qty, sym = o["quantity"], o["symbol"]
        if qty <= 0:
            reasons.append("adet pozitif olmalı")
        if qty > self.max_quantity:
            reasons.append(f"adet üst sınırı aşıyor ({self.max_quantity:g})")
        if o["side"] not in ("BUY", "SELL"):
            reasons.append("side BUY veya SELL olmalı")
        if o["order_type"] not in ("MARKET", "LIMIT"):
            reasons.append("order_type MARKET veya LIMIT olmalı")
        if o["order_type"] == "LIMIT" and not (o["limit_price"] or 0) > 0:
            reasons.append("limit emir pozitif limit_price ister")
        if o["order_type"] == "MARKET" and o["limit_price"] is not None:
            reasons.append("piyasa emrinde limit_price olmaz")
        if sym not in self.state["prices"]:
            reasons.append(f"'{sym}' simülasyonda yok")
            return reasons
        ccy = CURRENCY.get(sym, "TRY")
        ref = o["limit_price"] if o["order_type"] == "LIMIT" and o["limit_price"] else self.state["prices"][sym]
        value = ref * max(qty, 0)
        if value > self.max_order_value:
            reasons.append(f"emir değeri {value:.2f} üst sınırı aşıyor ({self.max_order_value:.2f})")
        if o["side"] == "BUY":
            cash = self.state["cash"].get(ccy, 0.0)
            if value > cash:
                reasons.append(f"yetersiz {ccy} nakit ({cash:.2f} < {value:.2f})")
        elif o["side"] == "SELL":
            held = self.state["positions"].get(sym, {}).get("quantity", 0.0)
            if qty > held:
                reasons.append(f"yetersiz pozisyon ({held:g} < {qty:g}); açığa satış yok")
        return reasons

    def place_order(self, symbol, side, quantity, order_type="MARKET", limit_price=None):
        """Emri doğrular ve onay kuyruğuna alır. ASLA burada gerçekleştirmez."""
        with self._lock:
            o = {"id": "simord_" + uuid.uuid4().hex[:10], "symbol": str(symbol or "").upper(),
                 "side": str(side or "").upper(), "quantity": float(quantity or 0),
                 "order_type": str(order_type or "MARKET").upper(),
                 "limit_price": None if limit_price in (None, "") else float(limit_price),
                 "status": PENDING, "reasons": [], "fills": [], "approved_by": None,
                 "created": time.strftime("%Y-%m-%dT%H:%M:%S"), "simulated": True}
            if self.mode == "READ_ONLY":
                o["status"], o["reasons"] = REJECTED, ["READ_ONLY modunda emir kapalı"]
            else:
                self._maybe_fail()
                reasons = self._validate(o)
                if reasons:
                    o["status"], o["reasons"] = REJECTED, reasons
            self.state["orders"][o["id"]] = o
            self._save()
            self._audit("order.place", order_id=o["id"], symbol=o["symbol"], side=o["side"],
                        quantity=o["quantity"], status=o["status"], reasons=o["reasons"])
            return dict(o)

    def approve(self, order_id, approved_by):
        """Kullanıcının açık onayından SONRA çağrılır: yeniden doğrular, simüle gerçekleştirir."""
        if not str(approved_by or "").strip():
            raise MidasError("onay için onaylayan kişi gerekli")
        with self._lock:
            o = self.state["orders"].get(order_id)
            if o is None:
                raise MidasError(f"emir bulunamadı: {order_id}")
            if o["status"] != PENDING:
                raise MidasError(f"emir {o['status']} durumunda, onaylanamaz")
            self._maybe_fail()  # hata olursa emir BEKLIYOR kalır, kısmi işlem olmaz
            reasons = self._validate(o)
            o["approved_by"] = approved_by
            if reasons:
                o["status"], o["reasons"] = REJECTED, reasons
            else:
                price = self.state["prices"][o["symbol"]]
                lp = o["limit_price"]
                if o["order_type"] == "LIMIT" and ((o["side"] == "BUY" and price > lp)
                                                   or (o["side"] == "SELL" and price < lp)):
                    o["status"] = OPEN
                else:
                    self._fill(o, price)
                    o["status"] = FILLED
            self._save()
            self._audit("order.approve", order_id=o["id"], approved_by=approved_by,
                        status=o["status"], reasons=o["reasons"])
            return dict(o)

    def _fill(self, o, price):
        sym, qty = o["symbol"], o["quantity"]
        ccy = CURRENCY.get(sym, "TRY")
        value = price * qty
        pos = self.state["positions"].setdefault(sym, {"quantity": 0.0, "avg_cost": 0.0})
        if o["side"] == "BUY":
            self.state["cash"][ccy] = round(self.state["cash"].get(ccy, 0.0) - value, 4)
            total = pos["quantity"] + qty
            pos["avg_cost"] = round((pos["avg_cost"] * pos["quantity"] + value) / total, 4)
            pos["quantity"] = total
        else:
            self.state["cash"][ccy] = round(self.state["cash"].get(ccy, 0.0) + value, 4)
            pos["quantity"] -= qty
        o["fills"].append({"price": price, "quantity": qty,
                           "ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "simulated": True})

    def cancel(self, order_id):
        with self._lock:
            o = self.state["orders"].get(order_id)
            if o is None:
                raise MidasError(f"emir bulunamadı: {order_id}")
            if o["status"] not in (PENDING, OPEN):
                raise MidasError(f"{o['status']} durumundaki emir iptal edilemez")
            o["status"] = CANCELLED
            self._save()
            self._audit("order.cancel", order_id=order_id)
            return dict(o)

    def orders(self, status=None):
        return [dict(o) for o in self.state["orders"].values() if status is None or o["status"] == status]

    def status(self):
        return {"mode": self.mode, "auto_execution": AUTO_EXECUTION, "simulated": True,
                "live": "YOK — resmi Midas API'si bulunmuyor",
                "max_order_value": self.max_order_value,
                "pending_orders": len(self.orders(PENDING)),
                "symbols": sorted(self.state["prices"])}
