import sys
import pygame
import vgamepad as vg
import time
import threading
from poe2_core import MemoryReader, AutoManager, print_stats

# ============================================================
# CONFIG - Controller-specific
# ============================================================

# --- Buttons (gamepad buttons) ---
BTN_HP_FLASK        = vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT
BTN_MANA_FLASK      = vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT
BTN_TOGGLE_HP_AUTO  = 4   # LB

# --- Button mapping: physical gamepad -> virtual ---
XBOX_BUTTON_MAP = {
    0:  vg.XUSB_BUTTON.XUSB_GAMEPAD_A,
    1:  vg.XUSB_BUTTON.XUSB_GAMEPAD_B,
    2:  vg.XUSB_BUTTON.XUSB_GAMEPAD_X,
    3:  vg.XUSB_BUTTON.XUSB_GAMEPAD_Y,
    4:  vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER,
    5:  vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER,
    6:  vg.XUSB_BUTTON.XUSB_GAMEPAD_BACK,
    7:  vg.XUSB_BUTTON.XUSB_GAMEPAD_START,
    8:  vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_THUMB,
    9:  vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_THUMB,
    10: vg.XUSB_BUTTON.XUSB_GAMEPAD_GUIDE,
}

# ============================================================
# VIRTUAL CONTROLLER
# ============================================================

class VirtualController:
    def __init__(self):
        self.vc = vg.VX360Gamepad()
        print("✅ Virtual gamepad created.")

    def press_button(self, button, hold=0.1):
        self.vc.press_button(button)
        self.vc.update()
        time.sleep(hold)
        self.vc.release_button(button)
        self.vc.update()

    def sync_from_physical(self, joystick: pygame.joystick.JoystickType):
        for btn_id, vbtn in XBOX_BUTTON_MAP.items():
            if joystick.get_button(btn_id):
                self.vc.press_button(vbtn)
            else:
                self.vc.release_button(vbtn)

        dx, dy = joystick.get_hat(0)
        self._sync_dpad(dx, dy)

        lx = joystick.get_axis(0)
        ly = joystick.get_axis(1)
        self.vc.left_joystick_float(lx, -ly)

        if joystick.get_numaxes() >= 4:
            rx = joystick.get_axis(2)
            ry = joystick.get_axis(3)
            self.vc.right_joystick_float(rx, -ry)

        if joystick.get_numaxes() >= 6:
            lt = max(0.0, joystick.get_axis(4))
            rt = max(0.0, joystick.get_axis(5))
            self.vc.left_trigger_float(lt)
            self.vc.right_trigger_float(rt)

        self.vc.update()

    def _sync_dpad(self, dx, dy):
        _map = {
            vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT:  dx == -1,
            vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT: dx ==  1,
            vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP:    dy ==  1,
            vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN:  dy == -1,
        }
        for btn, pressed in _map.items():
            if pressed:
                self.vc.press_button(btn)
            else:
                self.vc.release_button(btn)

    def apply_pending_buttons(self, pending: dict, lock: threading.Lock = None):
        if lock:
            with lock:
                self._apply_pending(pending)
        else:
            self._apply_pending(pending)

    def _apply_pending(self, pending: dict):
        now = time.time()
        expired = [btn for btn, release_at in pending.items() if now >= release_at]
        for btn in pending:
            if btn not in expired:
                self.vc.press_button(btn)
        for btn in expired:
            self.vc.release_button(btn)
            del pending[btn]
        if pending or expired:
            self.vc.update()

# ============================================================
# CONTROLLER AUTO MANAGER
# ============================================================

class ControllerAutoManager(AutoManager):
    def __init__(self, virtual_ctrl: VirtualController, mem: MemoryReader):
        super().__init__(mem)
        self.vc = virtual_ctrl
        self._pending_buttons: dict = {}
        self._lock = threading.Lock()

    def _send(self, key: str):
        btn = BTN_HP_FLASK if key == "hp_flask" else BTN_MANA_FLASK
        with self._lock:
            self._pending_buttons[btn] = time.time() + 0.1

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

    pygame.init()
    pygame.joystick.init()
    if pygame.joystick.get_count() == 0:
        print("❌ No physical controller found!")
        return
    real_ctrl = pygame.joystick.Joystick(0)
    real_ctrl.init()
    print(f"✅ Physical controller: {real_ctrl.get_name()}")

    vctrl = VirtualController()
    hp_mana_auto = ControllerAutoManager(vctrl, mem)

    btn_hp_held = False

    print(f"\n📋 Instructions:")
    print(f"   LB (btn {BTN_TOGGLE_HP_AUTO})  → toggle Auto HP/Mana")
    if use_gui:
        print(f"   GUI: ON  (close window to quit)")
    print("─" * 40)

    hp_mana_auto.start()

    def _controller_loop():
        nonlocal btn_hp_held
        while _alive[0]:
            pygame.event.pump()

            lb = real_ctrl.get_button(BTN_TOGGLE_HP_AUTO)
            if lb and not btn_hp_held:
                hp_mana_auto.toggle()
                btn_hp_held = True
            elif not lb:
                btn_hp_held = False

            vctrl.sync_from_physical(real_ctrl)
            vctrl.apply_pending_buttons(hp_mana_auto._pending_buttons, hp_mana_auto._lock)

            time.sleep(0.05)

    _alive = [True]

    if use_gui:
        import poe2_ui

        def _on_gui_close():
            _alive[0] = False
            hp_mana_auto.stop()
            pygame.quit()
            gui.root.destroy()

        ctrl_thread = threading.Thread(target=_controller_loop, daemon=True)
        ctrl_thread.start()

        gui = poe2_ui.Poe2GUI(mem=mem)
        gui.set_auto_manager(hp_mana_auto)
        gui._on_close = _on_gui_close
        gui.root.protocol("WM_DELETE_WINDOW", _on_gui_close)
        gui.run()
    else:
        try:
            _controller_loop()
        except KeyboardInterrupt:
            pass

        print("\n🛑 Shutting down...")
        hp_mana_auto.stop()
        pygame.quit()

if __name__ == "__main__":
    main()