import sys
import time
import threading
import keyboard
from poe2_core import MemoryReader, AutoManager, print_stats

# ============================================================
# CONFIG - Key bindings (keyboard-specific)
# ============================================================

KEY_HP_FLASK    = '1'
KEY_MANA_FLASK  = '2'
KEY_TOGGLE      = 'home'

# ============================================================
# KEYBOARD AUTO MANAGER
# ============================================================

class KeyboardAutoManager(AutoManager):
    def _send(self, key: str):
        if key == "hp_flask":
            keyboard.send(KEY_HP_FLASK)
        elif key == "mana_flask":
            keyboard.send(KEY_MANA_FLASK)

# ============================================================
# MAIN
# ============================================================

def main():
    use_gui = "--gui" in sys.argv

    try:
        mem = MemoryReader()
    except Exception as e:
        print(f"❌ Failed to connect to process: {e}")
        return

    print_stats(mem)

    auto = KeyboardAutoManager(mem)

    print(f"\n📋 Instructions:")
    print(f"   {KEY_TOGGLE.upper()}  → toggle Auto HP/Mana")
    print(f"   HP flask = key {KEY_HP_FLASK}")
    print(f"   Mana flask = key {KEY_MANA_FLASK}")
    if use_gui:
        print(f"   GUI: ON  (close window to quit)")
    print("─" * 40)

    if use_gui:
        # GUI mode: launch Tkinter, keyboard toggle still works in background
        _gui_alive = [True]

        def _key_watcher():
            while _gui_alive[0]:
                if keyboard.is_pressed(KEY_TOGGLE) and gui.hotkey_enabled.get():
                    auto.toggle()
                    gui.root.after(0, gui._sync_toggle_ui)
                    time.sleep(0.5)
                time.sleep(0.05)

        def _on_gui_close():
            _gui_alive[0] = False
            auto.stop()
            gui._save_settings()
            gui.root.destroy()

        import poe2_ui
        gui = poe2_ui.Poe2GUI(mem=mem)
        gui.set_auto_manager(auto)
        gui._on_close = _on_gui_close
        gui.root.protocol("WM_DELETE_WINDOW", _on_gui_close)

        watcher = threading.Thread(target=_key_watcher, daemon=True)
        watcher.start()

        gui.run()
    else:
        # CLI mode: keyboard toggle only
        auto.start()
        try:
            while True:
                if keyboard.is_pressed(KEY_TOGGLE):
                    auto.toggle()
                    time.sleep(0.5)
                time.sleep(0.05)
        except KeyboardInterrupt:
            pass

        print("\n🛑 Shutting down...")
        auto.stop()

if __name__ == "__main__":
    main()