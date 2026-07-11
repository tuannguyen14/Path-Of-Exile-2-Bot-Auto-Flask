import pymem
import time
import random
import threading

# ============================================================
# CONFIG - Offsets & thresholds (shared by both bots)
# ============================================================

PROCESS_NAME        = "PathOfExile.exe"
BASE_OFFSET         = 0x0438CFE0

OFFSETS_HP          = [0x38, 0x18, 0xB8, 0x30, 0x28, 0x28, 0x3D0] # currentHP
OFFSETS_MAX_HP      = [0x38, 0x18, 0xB8, 0x30, 0x28, 0x28, 0x3D4] # maxHP
OFFSETS_MANA        = [0x38, 0x18, 0xB8, 0x30, 0x28, 0x28, 0x800] # currentMana
OFFSETS_MAX_MANA    = [0x38, 0x18, 0xB8, 0x30, 0x28, 0x28, 0x804] # maxMana
OFFSETS_ES          = [0x38, 0x18, 0xB8, 0x30, 0x28, 0x28, 0x3DC] # currentES
OFFSETS_MAX_ES      = [0x38, 0x18, 0xB8, 0x30, 0x28, 0x28, 0x3E0] # maxES

# --- HP/Mana thresholds (percentage-based) ---
HP_FLASK_THRESHOLD      = 0.60
HP_FLASK_COOLDOWN       = (1.0, 2.5)
HP_EMERGENCY_THRESHOLD  = 0.15
HP_EMERGENCY_COOLDOWN   = 0.5

MANA_FLASK_THRESHOLD       = 0.30
MANA_EMERGENCY_THRESHOLD   = 0.10
MANA_EMERGENCY_COOLDOWN    = 0.5
MANA_FLASK_COOLDOWN        = (1.0, 2.5)

HP_MANA_POLL_INTERVAL   = 0.1

# ============================================================
# MEMORY READER
# ============================================================

class MemoryReader:
    def __init__(self, process_name=PROCESS_NAME, base_offset=BASE_OFFSET):
        self.pm = pymem.Pymem(process_name)
        self.base_address = self.pm.base_address + base_offset
        print(f"✅ Connected to {process_name}")

    def _resolve_chain(self, offsets) -> int | None:
        try:
            address = self.pm.read_longlong(self.base_address)
            for offset in offsets[:-1]:
                address = self.pm.read_longlong(address + offset)
            return address
        except Exception:
            return None

    def read_hp_mana(self) -> dict:
        base = self._resolve_chain(OFFSETS_HP)
        if base is None:
            return {"hp": None, "mana": None, "max_hp": None, "max_mana": None}
        try:
            return {
                "hp":       self.pm.read_int(base + OFFSETS_HP[-1]),
                "max_hp":   self.pm.read_int(base + OFFSETS_MAX_HP[-1]),
                "mana":     self.pm.read_int(base + OFFSETS_MANA[-1]),
                "max_mana": self.pm.read_int(base + OFFSETS_MAX_MANA[-1]),
            }
        except Exception:
            return {"hp": None, "mana": None, "max_hp": None, "max_mana": None}

    def read_es(self) -> dict:
        base = self._resolve_chain(OFFSETS_ES)
        if base is None:
            return {"es": None, "max_es": None}
        try:
            return {
                "es":     self.pm.read_int(base + OFFSETS_ES[-1]),
                "max_es": self.pm.read_int(base + OFFSETS_MAX_ES[-1]),
            }
        except Exception:
            return {"es": None, "max_es": None}

# ============================================================
# AUTO MANAGER BASE
# ============================================================

class AutoManager:
    """
    Auto HP/Mana flask based on percentage with random cooldown.
    Subclasses must implement _send(key) to send input (keyboard or gamepad).
    """

    def __init__(self, mem: MemoryReader):
        self.mem = mem
        self._last: dict[str, float] = {"hp_flask": 0.0, "mana_flask": 0.0}
        self._cd: dict[str, float] = {"hp_flask": 0.0, "mana_flask": 0.0}
        self._cd_config: dict = {
            "hp_flask":   HP_FLASK_COOLDOWN,
            "mana_flask": MANA_FLASK_COOLDOWN,
        }
        self._running = False
        self._thread: threading.Thread | None = None
        self._on_fire = None  # callback(label: str) for GUI logging

    # ── Override in subclass ─────────────────────────────
    def _send(self, key: str):
        """Send input (keyboard key or gamepad button). Override in subclass."""
        raise NotImplementedError

    # ── Toggle ───────────────────────────────────────────────
    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        print("▶️  [Auto] ON")

    def stop(self):
        self._running = False
        print("⏸️  [Auto] OFF")

    def toggle(self):
        self.stop() if self._running else self.start()

    @property
    def is_running(self) -> bool:
        return self._running

    # ── Internal ─────────────────────────────────────────────
    def _ready(self, key: str) -> bool:
        return time.time() - self._last[key] >= self._cd[key]

    def _fire(self, key: str, label: str, emergency: bool = False):
        print(f"❤️  [Auto] {label}")
        if self._on_fire:
            self._on_fire(label)
        self._last[key] = time.time()
        if emergency and key in ("hp_flask", "mana_flask"):
            if key == "hp_flask":
                self._cd[key] = HP_EMERGENCY_COOLDOWN
            else:
                self._cd[key] = MANA_EMERGENCY_COOLDOWN
        else:
            cd = self._cd_config[key]
            self._cd[key] = random.uniform(*cd) if isinstance(cd, tuple) else cd
        self._send(key)

    def _loop(self):
        while self._running:
            self._tick()
            time.sleep(HP_MANA_POLL_INTERVAL)

    def _tick(self):
        stats    = self.mem.read_hp_mana()
        hp       = stats.get("hp")
        mana     = stats.get("mana")
        max_hp   = stats.get("max_hp")
        max_mana = stats.get("max_mana")

        # --- HP ---
        if hp is not None and max_hp:
            hp_pct = hp / max_hp

            if hp_pct < HP_EMERGENCY_THRESHOLD and self._ready("hp_flask"):
                self._fire("hp_flask", f"HP EMERGENCY! {hp}/{max_hp} ({hp_pct:.0%})", emergency=True)
            elif hp_pct < HP_FLASK_THRESHOLD and self._ready("hp_flask"):
                self._fire("hp_flask", f"HP flask ({hp}/{max_hp} = {hp_pct:.0%})")

        # --- Mana ---
        if mana is not None and max_mana and max_mana > 0:
            mana_pct = mana / max_mana

            if mana_pct < MANA_EMERGENCY_THRESHOLD and self._ready("mana_flask"):
                self._fire("mana_flask", f"Mana EMERGENCY! {mana}/{max_mana} ({mana_pct:.0%})", emergency=True)
            elif mana_pct < MANA_FLASK_THRESHOLD and self._ready("mana_flask"):
                self._fire("mana_flask", f"Mana flask ({mana}/{max_mana} = {mana_pct:.0%})")

# ============================================================
# Helper: print stats
# ============================================================

def print_stats(mem: MemoryReader):
    stats = mem.read_hp_mana()
    es = mem.read_es()
    print(f"📊 Stats: HP {stats['hp']}/{stats['max_hp']}  |  Mana {stats['mana']}/{stats['max_mana']}  |  ES {es['es']}/{es['max_es']}")
