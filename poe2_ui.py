import tkinter as tk
import threading
import time
import json
import os

import poe2_core as core

SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")


class Poe2GUI:
    BG         = "#0f0f1e"
    PANEL      = "#16213e"
    ACCENT     = "#0f3460"
    TEXT       = "#e0e0e0"
    GREEN      = "#00e676"
    GREEN_H    = "#00c853"
    RED        = "#ff5252"
    RED_H      = "#d32f2f"
    BLUE       = "#448aff"
    ORANGE     = "#ffab40"
    GREY       = "#546e7a"
    DARK       = "#0d1117"

    def __init__(self, mem: core.MemoryReader | None = None):
        self.root = tk.Tk()
        self.root.title("PoE2 Bot — Auto Flask Manager")
        self.root.configure(bg=self.BG)
        self.root.resizable(True, True)
        self.root.geometry("440x680")
        self.root.minsize(400, 600)
        self.root.eval("tk::PlaceWindow . center")

        self.mem: core.MemoryReader | None = mem
        self.auto: core.AutoManager | None = None
        self._stats = {"hp": 0, "max_hp": 0, "mana": 0, "max_mana": 0, "es": 0, "max_es": 0}
        self._log_lines: list[str] = []
        self._running = False
        self._last_toggle_state: bool | None = None
        self.hotkey_enabled = tk.BooleanVar(value=True)

        self._load_settings()
        self._build_ui()
        if self.mem:
            self._on_connected()
        else:
            self._try_connect()

    # ── Build UI ─────────────────────────────────────────────

    def _sep(self, parent, padx=16):
        tk.Frame(parent, bg=self.ACCENT, height=1).pack(fill="x", padx=padx, pady=2)

    def _build_ui(self):
        root = self.root
        pad = {"padx": 14}

        # ── Header ──
        header = tk.Frame(root, bg=self.BG)
        header.pack(fill="x", pady=(12, 0))
        tk.Label(header, text="⚔  PoE2 Bot", bg=self.BG, fg=self.TEXT,
                 font=("Segoe UI", 16, "bold")).pack(side="left", padx=(14, 0))
        tk.Label(header, text="v1.1", bg=self.BG, fg=self.ACCENT,
                 font=("Segoe UI", 7)).pack(side="left", padx=(4, 0), pady=(6, 0))

        # ── Status panel ──
        panel = tk.Frame(root, bg=self.PANEL, relief="flat", bd=1)
        panel.pack(fill="x", **pad, pady=(8, 4))

        # Connection status + Auto status
        status_row = tk.Frame(panel, bg=self.PANEL)
        status_row.pack(fill="x", padx=12, pady=(8, 4))

        self.lbl_status = tk.Label(status_row, text="● Connecting...",
                                   bg=self.PANEL, fg=self.ORANGE,
                                   font=("Consolas", 9, "bold"))
        self.lbl_status.pack(side="left")

        self.lbl_auto = tk.Label(status_row, text="Auto: OFF",
                                 bg=self.PANEL, fg=self.GREY,
                                 font=("Consolas", 9, "bold"))
        self.lbl_auto.pack(side="right")

        self._sep(panel, padx=12)

        # HP bar
        hp_row = tk.Frame(panel, bg=self.PANEL)
        hp_row.pack(fill="x", padx=12, pady=(4, 0))
        tk.Label(hp_row, text="❤ HP", bg=self.PANEL, fg=self.RED,
                 font=("Segoe UI", 9, "bold"), width=6).pack(side="left")
        self.hp_val = tk.Label(hp_row, text="0 / 0", bg=self.PANEL, fg=self.TEXT,
                               font=("Consolas", 8))
        self.hp_val.pack(side="right")
        self.hp_bar = self._make_bar(panel, self.RED)

        # Mana bar
        mana_row = tk.Frame(panel, bg=self.PANEL)
        mana_row.pack(fill="x", padx=12, pady=(6, 0))
        tk.Label(mana_row, text="🔷 Mana", bg=self.PANEL, fg=self.BLUE,
                 font=("Segoe UI", 9, "bold"), width=6).pack(side="left")
        self.mana_val = tk.Label(mana_row, text="0 / 0", bg=self.PANEL, fg=self.TEXT,
                                 font=("Consolas", 8))
        self.mana_val.pack(side="right")
        self.mana_bar = self._make_bar(panel, self.BLUE)

        # ES bar
        es_row = tk.Frame(panel, bg=self.PANEL)
        es_row.pack(fill="x", padx=12, pady=(6, 8))
        tk.Label(es_row, text="🛡 ES", bg=self.PANEL, fg=self.GREY,
                 font=("Segoe UI", 9, "bold"), width=6).pack(side="left")
        self.es_val = tk.Label(es_row, text="0 / 0", bg=self.PANEL, fg=self.TEXT,
                               font=("Consolas", 8))
        self.es_val.pack(side="right")
        self.es_bar = self._make_bar(panel, self.GREY)

        # ── Toggle button ──
        self.btn_toggle = tk.Button(root, text="▶  START AUTO",
                                    bg=self.GREEN, fg="#000",
                                    font=("Segoe UI", 12, "bold"),
                                    relief="flat", cursor="hand2", bd=0,
                                    activebackground=self.GREEN_H,
                                    command=self._on_toggle)
        self.btn_toggle.pack(fill="x", **pad, pady=(8, 4), ipady=8)
        self._add_hover(self.btn_toggle, self.GREEN, self.GREEN_H, "#000", "#000")

        # ── Config panel ──
        cfg = tk.LabelFrame(root, text="⚙  Settings", bg=self.PANEL, fg=self.TEXT,
                            font=("Segoe UI", 9, "bold"), relief="flat", bd=1)
        cfg.pack(fill="x", **pad, pady=4)

        self._build_slider(cfg, "HP Threshold", core.HP_FLASK_THRESHOLD, 0.1, 0.95,
                           self._on_hp_thresh)
        self._build_slider(cfg, "Mana Threshold", core.MANA_FLASK_THRESHOLD, 0.05, 0.90,
                           self._on_mana_thresh)

        chk_hotkey = tk.Checkbutton(cfg, text="Enable hotkey toggle (Home / LB)",
                                    variable=self.hotkey_enabled,
                                    bg=self.PANEL, fg=self.TEXT,
                                    selectcolor=self.ACCENT,
                                    activebackground=self.PANEL, activeforeground=self.TEXT,
                                    font=("Segoe UI", 8),
                                    command=self._on_hotkey_toggle)
        chk_hotkey.pack(anchor="w", padx=12, pady=(4, 8))

        # ── Log ──
        log_frame = tk.Frame(root, bg=self.PANEL, relief="flat", bd=1)
        log_frame.pack(fill="both", expand=True, **pad, pady=(4, 8))

        log_header = tk.Frame(log_frame, bg=self.PANEL)
        log_header.pack(fill="x", padx=8, pady=(4, 0))
        tk.Label(log_header, text="📜 Log", bg=self.PANEL, fg=self.GREY,
                 font=("Segoe UI", 8, "bold")).pack(side="left")
        self.lbl_log_count = tk.Label(log_header, text="0 events", bg=self.PANEL, fg=self.GREY,
                                      font=("Segoe UI", 7))
        self.lbl_log_count.pack(side="right")

        self.log_text = tk.Text(log_frame, bg=self.DARK, fg=self.TEXT,
                                font=("Consolas", 8), relief="flat",
                                height=7, state="disabled", wrap="word",
                                borderwidth=0)
        self.log_text.pack(fill="both", expand=True, padx=8, pady=(2, 8))

        # ── Footer ──
        self._sep(root, padx=14)
        tk.Label(root, text="github.com/tuannguyen14", bg=self.BG, fg=self.ACCENT,
                 font=("Segoe UI", 7, "bold")).pack(side="bottom", pady=(2, 2))
        tk.Label(root, text="Close window to quit  •  For educational purposes only",
                 bg=self.BG, fg=self.GREY,
                 font=("Segoe UI", 7)).pack(side="bottom", pady=(0, 6))

    def _add_hover(self, btn, normal_bg, hover_bg, normal_fg="#fff", hover_fg="#fff"):
        btn.bind("<Enter>", lambda e: btn.config(bg=hover_bg, fg=hover_fg))
        btn.bind("<Leave>", lambda e: btn.config(bg=normal_bg, fg=normal_fg))

    def _make_bar(self, parent, color) -> tk.Canvas:
        bar = tk.Canvas(parent, bg=self.PANEL, height=20, highlightthickness=0)
        bar.pack(fill="x", padx=12, pady=(2, 0))
        bar._color = color
        bar._pct = 0
        bar.bind("<Configure>", lambda e: self._draw_bar(bar))
        return bar

    def _draw_bar(self, bar: tk.Canvas):
        w = bar.winfo_width()
        h = bar.winfo_height()
        bar.delete("all")
        # Background track
        bar.create_rectangle(0, 0, w, h, fill="#1e272e", outline="")
        # Fill
        fill_w = int(w * bar._pct)
        if fill_w > 2:
            bar.create_rectangle(1, 1, fill_w, h - 1, fill=bar._color, outline="")
        # Percentage text
        pct_txt = f"{bar._pct:.0%}"
        bar.create_text(w // 2, h // 2, text=pct_txt,
                        fill="#fff", font=("Consolas", 8, "bold"))

    def _build_slider(self, parent, label, init_val, lo, hi, callback):
        row = tk.Frame(parent, bg=self.PANEL)
        row.pack(fill="x", padx=12, pady=4)

        info = tk.Frame(row, bg=self.PANEL)
        info.pack(fill="x")
        tk.Label(info, text=label, bg=self.PANEL, fg=self.TEXT,
                 font=("Segoe UI", 8), anchor="w").pack(side="left")
        val_lbl = tk.Label(info, text=f"{init_val:.0%}", bg=self.PANEL, fg=self.ORANGE,
                          font=("Consolas", 8, "bold"))
        val_lbl.pack(side="right")

        var = tk.DoubleVar(value=init_val)
        slider = tk.Scale(row, from_=lo, to=hi, resolution=0.05,
                          orient="horizontal", variable=var,
                          bg=self.PANEL, fg=self.TEXT,
                          font=("Consolas", 7), length=200,
                          highlightthickness=0, relief="flat",
                          command=callback, sliderlength=14,
                          troughcolor="#1e272e")
        slider.pack(fill="x", pady=(0, 2))
        slider._val_lbl = val_lbl
        slider._callback = callback
        slider._orig_callback = callback
        # Wrap callback to update value label
        def _wrapped(val, _cb=callback, _lbl=val_lbl):
            _cb(val)
            _lbl.config(text=f"{float(val):.0%}")
        slider.config(command=_wrapped)

    # ── Callbacks ────────────────────────────────────────────

    _toggle_debounce = 0

    def _on_toggle(self):
        now = int(time.time() * 1000)
        if now - self._toggle_debounce < 500:
            return
        self._toggle_debounce = now
        if self.auto:
            self.auto.toggle()
            self._sync_toggle_ui()

    def _sync_toggle_ui(self, log: bool = True):
        if not self.auto:
            return
        running = self.auto.is_running
        if running == self._last_toggle_state:
            return
        self._last_toggle_state = running
        if running:
            self.btn_toggle.config(text="⏸  STOP AUTO", bg=self.RED,
                                   activebackground=self.RED_H)
            self._add_hover(self.btn_toggle, self.RED, self.RED_H, "#000", "#000")
            self.lbl_auto.config(text="Auto: ON", fg=self.GREEN)
            if log:
                self._log("Auto flask started")
        else:
            self.btn_toggle.config(text="▶  START AUTO", bg=self.GREEN,
                                   activebackground=self.GREEN_H)
            self._add_hover(self.btn_toggle, self.GREEN, self.GREEN_H, "#000", "#000")
            self.lbl_auto.config(text="Auto: OFF", fg=self.GREY)
            if log:
                self._log("Auto flask stopped")

    def _on_hp_thresh(self, val):
        core.HP_FLASK_THRESHOLD = float(val)
        self._save_settings()

    def _on_mana_thresh(self, val):
        core.MANA_FLASK_THRESHOLD = float(val)
        self._save_settings()

    def _on_hotkey_toggle(self):
        self._save_settings()

    def _load_settings(self):
        try:
            with open(SETTINGS_FILE, "r") as f:
                data = json.load(f)
            core.HP_FLASK_THRESHOLD = data.get("hp_threshold", core.HP_FLASK_THRESHOLD)
            core.MANA_FLASK_THRESHOLD = data.get("mana_threshold", core.MANA_FLASK_THRESHOLD)
            self.hotkey_enabled.set(data.get("hotkey_enabled", True))
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    def _save_settings(self):
        try:
            with open(SETTINGS_FILE, "w") as f:
                json.dump({
                    "hp_threshold": core.HP_FLASK_THRESHOLD,
                    "mana_threshold": core.MANA_FLASK_THRESHOLD,
                    "hotkey_enabled": bool(self.hotkey_enabled.get()),
                }, f)
        except Exception:
            pass

    # ── Connection ───────────────────────────────────────────

    def _try_connect(self):
        def _connect():
            try:
                self.mem = core.MemoryReader()
                self.root.after(0, self._on_connected)
            except Exception as e:
                self.root.after(0, lambda: self._on_connect_fail(str(e)))

        threading.Thread(target=_connect, daemon=True).start()

    def _on_connected(self):
        self.lbl_status.config(text="● Connected", fg=self.GREEN)
        self._log("Connected to PathOfExile.exe")
        self._running = True
        self._poll_stats()

    def _on_connect_fail(self, err):
        self.lbl_status.config(text="● Failed", fg=self.RED)
        self._log(f"Connection failed: {err}")
        self.root.after(3000, self._try_connect)

    # ── Polling ──────────────────────────────────────────────

    def _poll_stats(self):
        if not self._running or not self.mem:
            return

        def _read():
            stats = self.mem.read_hp_mana()
            es = self.mem.read_es()
            self._stats = {
                "hp": stats.get("hp") or 0,
                "max_hp": stats.get("max_hp") or 0,
                "mana": stats.get("mana") or 0,
                "max_mana": stats.get("max_mana") or 0,
                "es": es.get("es") or 0,
                "max_es": es.get("max_es") or 0,
            }
            self.root.after(0, self._update_ui)

        threading.Thread(target=_read, daemon=True).start()
        self.root.after(200, self._poll_stats)

    def _update_ui(self):
        s = self._stats

        # HP
        hp_pct = s["hp"] / s["max_hp"] if s["max_hp"] > 0 else 0
        self.hp_bar._pct = hp_pct
        self.hp_bar._color = self.RED if hp_pct < core.HP_EMERGENCY_THRESHOLD else self.GREEN if hp_pct >= core.HP_FLASK_THRESHOLD else self.ORANGE
        self._draw_bar(self.hp_bar)
        self.hp_val.config(text=f"{s['hp']} / {s['max_hp']}")

        # Mana
        mana_pct = s["mana"] / s["max_mana"] if s["max_mana"] > 0 else 0
        self.mana_bar._pct = mana_pct
        self.mana_bar._color = self.RED if mana_pct < core.MANA_EMERGENCY_THRESHOLD else self.BLUE if mana_pct >= core.MANA_FLASK_THRESHOLD else self.ORANGE
        self._draw_bar(self.mana_bar)
        self.mana_val.config(text=f"{s['mana']} / {s['max_mana']}")

        # ES
        es_pct = s["es"] / s["max_es"] if s["max_es"] > 0 else 0
        self.es_bar._pct = es_pct
        self.es_bar._color = self.GREY
        self._draw_bar(self.es_bar)
        self.es_val.config(text=f"{s['es']} / {s['max_es']}")

    # ── Log ──────────────────────────────────────────────────

    def _log(self, msg: str):
        ts = time.strftime("%H:%M:%S")
        line = f"[{ts}] {msg}"
        self._log_lines.append(line)
        if len(self._log_lines) > 50:
            self._log_lines.pop(0)

        self.lbl_log_count.config(text=f"{len(self._log_lines)} events")

        self.log_text.config(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.insert("1.0", "\n".join(self._log_lines[-20:]))
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    # ── Set auto manager (called from bot.py / bot_controller.py) ──

    def set_auto_manager(self, auto: core.AutoManager):
        self.auto = auto
        auto._on_fire = lambda label: self.root.after(0, lambda: self._log(label))

    # ── Run ──────────────────────────────────────────────────

    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.mainloop()

    def _on_close(self):
        self._running = False
        self._save_settings()
        if self.auto:
            self.auto.stop()
        self.root.destroy()
