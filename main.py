import sys
import tkinter as tk
import threading
import time

import poe2_core as core
from poe2_ui import Poe2GUI


class Launcher:
    BG       = "#0f0f1e"
    PANEL    = "#16213e"
    ACCENT   = "#0f3460"
    TEXT     = "#e0e0e0"
    GREEN    = "#00e676"
    GREEN_H  = "#00c853"
    BLUE     = "#448aff"
    BLUE_H   = "#2962ff"
    GREY     = "#546e7a"
    RED      = "#ff5252"

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("PoE2 Bot — Launcher")
        self.root.configure(bg=self.BG)
        self.root.resizable(False, False)
        self.root.geometry("380x460")
        self.root.eval("tk::PlaceWindow . center")

        self.choice: str | None = None

        self._build()

    def _build(self):
        r = self.root

        # ── Header ──
        tk.Label(r, text="⚔  Path of Exile 2", bg=self.BG, fg=self.TEXT,
                 font=("Segoe UI", 20, "bold")).pack(pady=(28, 2))
        tk.Label(r, text="Auto Flask Manager", bg=self.BG, fg=self.GREY,
                 font=("Segoe UI", 10)).pack(pady=(0, 4))
        tk.Label(r, text="v1.1", bg=self.BG, fg=self.ACCENT,
                 font=("Segoe UI", 7)).pack(pady=(0, 16))

        # ── Separator ──
        self._sep(r)

        tk.Label(r, text="Select Input Mode", bg=self.BG, fg=self.TEXT,
                 font=("Segoe UI", 11, "bold")).pack(pady=(12, 16))

        # ── Keyboard button ──
        btn_kb = tk.Button(r, text="⌨   KEYBOARD",
                          bg=self.GREEN, fg="#000",
                          font=("Segoe UI", 13, "bold"),
                          relief="flat", cursor="hand2", bd=0,
                          activebackground=self.GREEN_H,
                          command=lambda: self._select("keyboard"))
        btn_kb.pack(fill="x", padx=50, pady=(0, 4), ipady=10)
        self._add_hover(btn_kb, self.GREEN, self.GREEN_H)

        tk.Label(r, text="Keys: 1 (HP) + 2 (Mana)  •  Toggle: Home",
                 bg=self.BG, fg=self.GREY, font=("Segoe UI", 8)).pack(pady=(0, 16))

        # ── Controller button ──
        btn_ctrl = tk.Button(r, text="🎮   CONTROLLER",
                            bg=self.BLUE, fg="#fff",
                            font=("Segoe UI", 13, "bold"),
                            relief="flat", cursor="hand2", bd=0,
                            activebackground=self.BLUE_H,
                            command=lambda: self._select("controller"))
        btn_ctrl.pack(fill="x", padx=50, pady=(0, 4), ipady=10)
        self._add_hover(btn_ctrl, self.BLUE, self.BLUE_H)

        tk.Label(r, text="DPAD ◄ (HP) + ► (Mana)  •  Toggle: LB",
                 bg=self.BG, fg=self.GREY, font=("Segoe UI", 8)).pack(pady=(0, 12))

        # ── Controller availability indicator ──
        self._controller_ok = self._check_controller()
        if self._controller_ok:
            tk.Label(r, text="● Controller ready", bg=self.BG, fg=self.GREEN,
                     font=("Segoe UI", 7)).pack(pady=(0, 4))
        else:
            tk.Label(r, text="● Controller libs not installed", bg=self.BG, fg=self.RED,
                     font=("Segoe UI", 7)).pack(pady=(0, 4))

        # ── Footer ──
        self._sep(r)
        tk.Label(r, text="github.com/tuannguyen14", bg=self.BG, fg=self.ACCENT,
                 font=("Segoe UI", 8, "bold")).pack(side="bottom", pady=(4, 2))
        tk.Label(r, text="For educational purposes only", bg=self.BG, fg=self.GREY,
                 font=("Segoe UI", 7)).pack(side="bottom", pady=(0, 8))

    def _sep(self, parent):
        tk.Frame(parent, bg=self.ACCENT, height=1).pack(fill="x", padx=30, pady=2)

    def _add_hover(self, btn, normal_bg, hover_bg):
        btn.bind("<Enter>", lambda e: btn.config(bg=hover_bg))
        btn.bind("<Leave>", lambda e: btn.config(bg=normal_bg))

    def _check_controller(self) -> bool:
        try:
            import vgamepad
            import pygame
            return True
        except ImportError:
            return False

    def _select(self, mode: str):
        if mode == "controller" and not self._controller_ok:
            self._show_error("Controller mode requires:\npip install pygame vgamepad")
            return

        self.choice = mode
        self.root.destroy()

    def _show_error(self, msg: str):
        win = tk.Toplevel(self.root)
        win.title("Error")
        win.configure(bg=self.PANEL)
        win.geometry("320x120")
        win.resizable(False, False)
        win.eval(f"tk::PlaceWindow {win._w} center")

        tk.Label(win, text="⚠  Warning", bg=self.PANEL, fg=self.RED,
                 font=("Segoe UI", 11, "bold")).pack(pady=(16, 4))
        tk.Label(win, text=msg, bg=self.PANEL, fg=self.TEXT,
                 font=("Segoe UI", 9), justify="center").pack(pady=(0, 8))
        tk.Button(win, text="OK", bg=self.ACCENT, fg="#fff",
                  font=("Segoe UI", 9, "bold"), relief="flat", cursor="hand2",
                  command=win.destroy).pack(pady=(0, 12), ipadx=20, ipady=4)

    def run(self):
        self.root.mainloop()
        return self.choice


def run_keyboard(mem: core.MemoryReader):
    import keyboard
    from bot import KeyboardAutoManager, KEY_HP_FLASK, KEY_MANA_FLASK, KEY_TOGGLE

    auto = KeyboardAutoManager(mem)

    gui = Poe2GUI(mem=mem)
    gui.set_auto_manager(auto)

    _alive = [True]

    def _key_watcher():
        while _alive[0]:
            if keyboard.is_pressed(KEY_TOGGLE) and gui.hotkey_enabled.get():
                auto.toggle()
                gui.root.after(0, gui._sync_toggle_ui)
                time.sleep(0.5)
            time.sleep(0.05)

    def _on_close():
        _alive[0] = False
        auto.stop()
        gui._save_settings()
        gui._running = False
        gui.root.destroy()

    gui._on_close = _on_close
    gui.root.protocol("WM_DELETE_WINDOW", _on_close)

    threading.Thread(target=_key_watcher, daemon=True).start()
    gui.run()


def run_controller(mem: core.MemoryReader):
    import pygame
    from bot_controller import VirtualController, ControllerAutoManager, BTN_TOGGLE_HP_AUTO

    pygame.init()
    pygame.joystick.init()
    if pygame.joystick.get_count() == 0:
        print("❌ No physical controller found!")
        return
    real_ctrl = pygame.joystick.Joystick(0)
    real_ctrl.init()
    print(f"✅ Physical controller: {real_ctrl.get_name()}")

    vctrl = VirtualController()
    auto = ControllerAutoManager(vctrl, mem)

    gui = Poe2GUI(mem=mem)
    gui.set_auto_manager(auto)

    _alive = [True]
    btn_hp_held = False

    def _controller_loop():
        nonlocal btn_hp_held
        while _alive[0]:
            pygame.event.pump()
            lb = real_ctrl.get_button(BTN_TOGGLE_HP_AUTO)
            if lb and not btn_hp_held and gui.hotkey_enabled.get():
                auto.toggle()
                gui.root.after(0, gui._sync_toggle_ui)
                btn_hp_held = True
            elif not lb:
                btn_hp_held = False
            vctrl.sync_from_physical(real_ctrl)
            vctrl.apply_pending_buttons(auto._pending_buttons, auto._lock)
            time.sleep(0.05)

    def _on_close():
        _alive[0] = False
        auto.stop()
        gui._save_settings()
        pygame.quit()
        gui._running = False
        gui.root.destroy()

    gui._on_close = _on_close
    gui.root.protocol("WM_DELETE_WINDOW", _on_close)

    threading.Thread(target=_controller_loop, daemon=True).start()
    gui.run()


def main():
    launcher = Launcher()
    choice = launcher.run()

    if not choice:
        return

    try:
        mem = core.MemoryReader()
    except Exception as e:
        print(f"❌ Failed to connect to process: {e}")
        return

    core.print_stats(mem)

    print(f"\n📋 Mode: {choice.upper()}")
    print("─" * 40)

    if choice == "keyboard":
        run_keyboard(mem)
    elif choice == "controller":
        run_controller(mem)


if __name__ == "__main__":
    main()
