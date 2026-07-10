import sys
import tkinter as tk
import threading
import time

import poe2_core as core
from poe2_ui import Poe2GUI


class Launcher:
    BG    = "#1a1a2e"
    PANEL = "#16213e"
    TEXT  = "#e0e0e0"
    GREEN = "#00e676"
    BLUE  = "#448aff"
    GREY  = "#546e7a"

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("PoE2 Bot — Launcher")
        self.root.configure(bg=self.BG)
        self.root.resizable(False, False)
        self.root.geometry("340x280")
        self.root.eval("tk::PlaceWindow . center")

        self.choice: str | None = None

        self._build()

    def _build(self):
        r = self.root

        tk.Label(r, text="Path of Exile 2", bg=self.BG, fg=self.TEXT,
                 font=("Segoe UI", 18, "bold")).pack(pady=(24, 2))
        tk.Label(r, text="Select Input Mode", bg=self.BG, fg=self.GREY,
                 font=("Segoe UI", 10)).pack(pady=(0, 20))

        # Keyboard button
        btn_kb = tk.Button(r, text="⌨  KEYBOARD",
                           bg=self.GREEN, fg="#000",
                           font=("Segoe UI", 13, "bold"),
                           relief="flat", cursor="hand2",
                           activebackground="#00c853",
                           command=lambda: self._select("keyboard"))
        btn_kb.pack(fill="x", padx=40, pady=(0, 8), ipady=8)

        tk.Label(r, text="Flask: keys 1 (HP) + 2 (Mana)  •  Toggle: Home",
                 bg=self.BG, fg=self.GREY, font=("Segoe UI", 8)).pack(pady=(0, 12))

        # Controller button
        btn_ctrl = tk.Button(r, text="🎮  CONTROLLER",
                             bg=self.BLUE, fg="#fff",
                             font=("Segoe UI", 13, "bold"),
                             relief="flat", cursor="hand2",
                             activebackground="#2962ff",
                             command=lambda: self._select("controller"))
        btn_ctrl.pack(fill="x", padx=40, pady=(0, 8), ipady=8)

        tk.Label(r, text="Flask: DPAD ◄ (HP) + ► (Mana)  •  Toggle: LB",
                 bg=self.BG, fg=self.GREY, font=("Segoe UI", 8)).pack(pady=(0, 12))

        # Check controller availability
        self._controller_ok = self._check_controller()

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
        win.geometry("300x100")
        win.eval(f"tk::PlaceWindow {win._w} center")

        tk.Label(win, text=msg, bg=self.PANEL, fg="#ff5252",
                 font=("Segoe UI", 9), justify="center").pack(pady=20)
        tk.Button(win, text="OK", bg=self.GREY, fg="#fff",
                  font=("Segoe UI", 9), relief="flat",
                  command=win.destroy).pack(pady=(0, 10))

    def run(self):
        self.root.mainloop()
        return self.choice


def run_keyboard(mem: core.MemoryReader):
    import keyboard
    from bot import KeyboardAutoManager, KEY_HP_FLASK, KEY_MANA_FLASK, KEY_TOGGLE

    auto = KeyboardAutoManager(mem)
    auto.start()

    gui = Poe2GUI(mem=mem)
    gui.set_auto_manager(auto)

    _alive = [True]

    def _key_watcher():
        while _alive[0]:
            if keyboard.is_pressed(KEY_TOGGLE):
                auto.toggle()
                time.sleep(0.5)
            time.sleep(0.05)

    def _on_close():
        _alive[0] = False
        auto.stop()
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
    auto.start()

    gui = Poe2GUI(mem=mem)
    gui.set_auto_manager(auto)

    _alive = [True]
    btn_hp_held = False

    def _controller_loop():
        nonlocal btn_hp_held
        while _alive[0]:
            pygame.event.pump()
            lb = real_ctrl.get_button(BTN_TOGGLE_HP_AUTO)
            if lb and not btn_hp_held:
                auto.toggle()
                btn_hp_held = True
            elif not lb:
                btn_hp_held = False
            vctrl.sync_from_physical(real_ctrl)
            vctrl.apply_pending_buttons(auto._pending_buttons, auto._lock)
            time.sleep(0.05)

    def _on_close():
        _alive[0] = False
        auto.stop()
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
