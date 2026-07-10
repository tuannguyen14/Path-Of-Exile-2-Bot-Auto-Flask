import tkinter as tk
import threading
import time

import poe2_core as core


class Poe2GUI:
    BG         = "#1a1a2e"
    PANEL      = "#16213e"
    ACCENT     = "#0f3460"
    TEXT       = "#e0e0e0"
    GREEN      = "#00e676"
    RED        = "#ff5252"
    BLUE       = "#448aff"
    ORANGE     = "#ffab40"
    GREY       = "#546e7a"

    def __init__(self, mem: core.MemoryReader | None = None):
        self.root = tk.Tk()
        self.root.title("PoE2 Bot")
        self.root.configure(bg=self.BG)
        self.root.resizable(True, True)
        self.root.geometry("420x620")
        self.root.minsize(380, 560)

        self.mem: core.MemoryReader | None = mem
        self.auto: core.AutoManager | None = None
        self._stats = {"hp": 0, "max_hp": 0, "mana": 0, "max_mana": 0, "es": 0, "max_es": 0}
        self._log_lines: list[str] = []
        self._running = False

        self._build_ui()
        if self.mem:
            self._on_connected()
        else:
            self._try_connect()

    # ── Build UI ─────────────────────────────────────────────

    def _build_ui(self):
        root = self.root
        pad = {"padx": 12}

        # ── Title ──
        tk.Label(root, text="Path of Exile 2 — Bot",
                 bg=self.BG, fg=self.TEXT,
                 font=("Segoe UI", 16, "bold")).pack(pady=(14, 2))
        tk.Label(root, text="Auto Flask Manager",
                 bg=self.BG, fg=self.GREY,
                 font=("Segoe UI", 9)).pack(pady=(0, 8))

        # ── Status panel ──
        panel = tk.Frame(root, bg=self.PANEL, relief="flat", bd=1)
        panel.pack(fill="x", **pad, pady=4)

        # Connection status
        self.lbl_status = tk.Label(panel, text="● Connecting...",
                                   bg=self.PANEL, fg=self.ORANGE,
                                   font=("Consolas", 10, "bold"))
        self.lbl_status.pack(anchor="w", padx=12, pady=(8, 4))

        # HP bar
        tk.Label(panel, text="HP", bg=self.PANEL, fg=self.TEXT,
                 font=("Segoe UI", 9, "bold"), width=4).pack(anchor="w", padx=12)
        self.hp_bar = self._make_bar(panel, self.RED)
        self.hp_val = tk.Label(panel, text="0 / 0", bg=self.PANEL, fg=self.TEXT,
                               font=("Consolas", 9))
        self.hp_val.pack(anchor="w", padx=12, pady=(0, 4))

        # Mana bar
        tk.Label(panel, text="Mana", bg=self.PANEL, fg=self.TEXT,
                 font=("Segoe UI", 9, "bold"), width=4).pack(anchor="w", padx=12)
        self.mana_bar = self._make_bar(panel, self.BLUE)
        self.mana_val = tk.Label(panel, text="0 / 0", bg=self.PANEL, fg=self.TEXT,
                                 font=("Consolas", 9))
        self.mana_val.pack(anchor="w", padx=12, pady=(0, 4))

        # ES bar
        tk.Label(panel, text="ES", bg=self.PANEL, fg=self.TEXT,
                 font=("Segoe UI", 9, "bold"), width=4).pack(anchor="w", padx=12)
        self.es_bar = self._make_bar(panel, self.GREY)
        self.es_val = tk.Label(panel, text="0 / 0", bg=self.PANEL, fg=self.TEXT,
                               font=("Consolas", 9))
        self.es_val.pack(anchor="w", padx=12, pady=(0, 8))

        # ── Toggle button ──
        self.btn_toggle = tk.Button(root, text="▶  START AUTO",
                                    bg=self.GREEN, fg="#000",
                                    font=("Segoe UI", 12, "bold"),
                                    relief="flat", cursor="hand2",
                                    activebackground="#00c853",
                                    command=self._on_toggle)
        self.btn_toggle.pack(fill="x", **pad, pady=(8, 4))
        self.btn_toggle.config(height=2)

        # ── Config panel ──
        cfg = tk.LabelFrame(root, text="Settings", bg=self.PANEL, fg=self.TEXT,
                            font=("Segoe UI", 9, "bold"), relief="flat", bd=1)
        cfg.pack(fill="x", **pad, pady=4)

        self._build_slider(cfg, "HP Threshold", core.HP_FLASK_THRESHOLD, 0.1, 0.95,
                           self._on_hp_thresh)
        self._build_slider(cfg, "Mana Threshold", core.MANA_FLASK_THRESHOLD, 0.05, 0.90,
                           self._on_mana_thresh)

        # ── Log ──
        log_frame = tk.Frame(root, bg=self.PANEL, relief="flat", bd=1)
        log_frame.pack(fill="both", expand=True, **pad, pady=(4, 12))

        tk.Label(log_frame, text="Log", bg=self.PANEL, fg=self.GREY,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=8, pady=(4, 0))

        self.log_text = tk.Text(log_frame, bg="#0d1117", fg=self.TEXT,
                                font=("Consolas", 8), relief="flat",
                                height=6, state="disabled", wrap="word")
        self.log_text.pack(fill="both", expand=True, padx=8, pady=(2, 8))

        # ── Footer ──
        tk.Label(root, text="Ctrl+C to quit", bg=self.BG, fg=self.GREY,
                 font=("Segoe UI", 7)).pack(side="bottom", pady=(0, 6))

    def _make_bar(self, parent, color) -> tk.Canvas:
        bar = tk.Canvas(parent, bg=self.PANEL, height=18, highlightthickness=0)
        bar.pack(fill="x", padx=12, pady=(2, 0))
        bar._color = color
        bar._pct = 0
        bar.bind("<Configure>", lambda e: self._draw_bar(bar))
        return bar

    def _draw_bar(self, bar: tk.Canvas):
        w = bar.winfo_width()
        h = bar.winfo_height()
        bar.delete("all")
        bar.create_rectangle(0, 0, w, h, fill="#263238", outline="")
        fill_w = int(w * bar._pct)
        if fill_w > 0:
            bar.create_rectangle(0, 0, fill_w, h, fill=bar._color, outline="")
        pct_txt = f"{bar._pct:.0%}"
        bar.create_text(w // 2, h // 2, text=pct_txt,
                        fill="#fff", font=("Consolas", 8, "bold"))

    def _build_slider(self, parent, label, init_val, lo, hi, callback):
        row = tk.Frame(parent, bg=self.PANEL)
        row.pack(fill="x", padx=12, pady=4)

        tk.Label(row, text=label, bg=self.PANEL, fg=self.TEXT,
                 font=("Segoe UI", 8), width=14, anchor="w").pack(side="left")

        var = tk.DoubleVar(value=init_val)
        slider = tk.Scale(row, from_=lo, to=hi, resolution=0.05,
                          orient="horizontal", variable=var,
                          bg=self.PANEL, fg=self.TEXT,
                          font=("Consolas", 7), length=150,
                          highlightthickness=0, relief="flat",
                          command=callback, sliderlength=12,
                          troughcolor="#263238")
        slider.pack(side="left", padx=(4, 0))

    # ── Callbacks ────────────────────────────────────────────

    def _on_toggle(self):
        if self.auto:
            self.auto.toggle()
            if self.auto.is_running:
                self.btn_toggle.config(text="⏸  STOP AUTO", bg=self.RED,
                                       activebackground="#d32f2f")
            else:
                self.btn_toggle.config(text="▶  START AUTO", bg=self.GREEN,
                                       activebackground="#00c853")

    def _on_hp_thresh(self, val):
        core.HP_FLASK_THRESHOLD = float(val)

    def _on_mana_thresh(self, val):
        core.MANA_FLASK_THRESHOLD = float(val)

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
        self.mana_bar._color = self.BLUE if mana_pct >= core.MANA_FLASK_THRESHOLD else self.ORANGE
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

        self.log_text.config(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.insert("1.0", "\n".join(self._log_lines[-20:]))
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    # ── Set auto manager (called from bot.py / bot_controller.py) ──

    def set_auto_manager(self, auto: core.AutoManager):
        self.auto = auto

    # ── Run ──────────────────────────────────────────────────

    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.mainloop()

    def _on_close(self):
        self._running = False
        if self.auto:
            self.auto.stop()
        self.root.destroy()


def launch(auto_manager: core.AutoManager | None = None):
    """Launch GUI. If auto_manager is provided, binds it for toggle/control."""
    gui = Poe2GUI()
    if auto_manager:
        gui.set_auto_manager(auto_manager)
    gui.run()
