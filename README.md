# PoE2 0.5.4 Bot — Auto Flask Manager

Automatically triggers HP/Mana flasks in Path of Exile 2 by reading HP/Mana/ES values directly from game memory.

## Project Structure

```
main.py               Launcher — select Keyboard or Controller from GUI, starts bot + UI
poe2_core.py          Shared logic: MemoryReader, AutoManager, config (offsets, thresholds)
poe2_ui.py            Tkinter GUI: real-time HP/Mana/ES bars, toggle, sliders, log
├── bot.py            Keyboard mode — flasks on keys 1 (HP) and 2 (Mana)
└── bot_controller.py Controller mode — flasks via virtual gamepad (DPAD)
```

## Requirements

```
pip install pymem keyboard
```

Controller mode additionally requires:

```
pip install pygame vgamepad
```

## Usage

### Launcher (recommended)

```bash
python main.py
```

Shows a mode selection window → click **KEYBOARD** or **CONTROLLER** → auto-connects to game and opens GUI.

### Direct Execution

#### Keyboard mode

```bash
# CLI (terminal only)
python bot.py

# With GUI
python bot.py --gui
```

#### Controller mode

```bash
# CLI (terminal only)
python bot_controller.py

# With GUI
python bot_controller.py --gui
```

## Controls

| Mode | Toggle Auto | HP Flask | Mana Flask |
|------|-------------|----------|------------|
| Keyboard | `Home` | `1` | `2` |
| Controller | `LB` | DPAD LEFT | DPAD RIGHT |

- `Ctrl+C` to quit (CLI mode)
- Close GUI window to quit (GUI mode)

## Features

### Auto Flask Logic

- **HP flask** — triggers when HP drops below threshold (default 60%)
- **HP emergency** — triggers when HP drops below 15% with a shorter 0.5s cooldown
- **Mana flask** — triggers when Mana drops below threshold (default 30%)
- **Hysteresis** — after firing, won't re-trigger until HP/Mana recovers above the re-arm threshold (85% / 60%), preventing flask spam
- **Random cooldown** — each flask use has a randomized cooldown (1.0–2.5s) to mimic human-like behavior
- **Skip zero max mana** — won't trigger mana flask if max_mana is 0

### GUI

- Real-time HP/Mana/ES bars (updated every 200ms)
- Bar color changes by status: green (safe) → orange (low) → red (emergency)
- START/STOP toggle button
- Adjustable HP/Mana threshold sliders
- Log panel showing flask trigger history
- Auto-reconnect if game connection is lost

### Controller Mode

- Syncs physical gamepad → virtual gamepad (buttons, sticks, triggers, dpad)
- Auto flask overrides physical input via pending button system (avoids race conditions)
- Separate thread for auto flask logic, doesn't block controller sync

## Configuration

All config is in `poe2_core.py`:

```python
# Memory offsets
BASE_OFFSET         = 0x0438CFE0
OFFSETS_HP          = [0x38, 0x18, 0xB8, 0x30, 0x28, 0x28, 0x3D0]
OFFSETS_MAX_HP      = [0x38, 0x18, 0xB8, 0x30, 0x28, 0x28, 0x3D4]
OFFSETS_MANA        = [0x38, 0x18, 0xB8, 0x30, 0x28, 0x28, 0x800]
OFFSETS_MAX_MANA    = [0x38, 0x18, 0xB8, 0x30, 0x28, 0x28, 0x804]
OFFSETS_ES          = [0x38, 0x18, 0xB8, 0x30, 0x28, 0x28, 0x3DC]
OFFSETS_MAX_ES      = [0x38, 0x18, 0xB8, 0x30, 0x28, 0x28, 0x3E0]

# Thresholds
HP_FLASK_THRESHOLD      = 0.60    # trigger HP flask below 60%
HP_FLASK_RECOVERED      = 0.85    # re-arm when HP recovers above 85%
HP_EMERGENCY_THRESHOLD  = 0.15    # emergency below 15%
HP_EMERGENCY_COOLDOWN   = 0.5     # emergency cooldown (seconds)
MANA_FLASK_THRESHOLD    = 0.30    # trigger Mana flask below 30%
MANA_FLASK_RECOVERED    = 0.60    # re-arm when Mana recovers above 60%

# Cooldown (seconds, randomized within range)
HP_FLASK_COOLDOWN       = (1.0, 2.5)
MANA_FLASK_COOLDOWN     = (1.0, 2.5)
```

Key bindings are in each bot file:

- `bot.py`: `KEY_HP_FLASK`, `KEY_MANA_FLASK`, `KEY_TOGGLE`
- `bot_controller.py`: `BTN_HP_FLASK`, `BTN_MANA_FLASK`, `BTN_TOGGLE_HP_AUTO`

## Updating Offsets After Game Patches

1. Open Cheat Engine, find new HP/Mana/ES offsets (see `find_offsets.py`)
2. Update offsets in `poe2_core.py`
3. Both bots automatically use the new offsets

## Disclaimer

This project is for **educational purposes only**. It reads game memory and simulates inputs, which may violate the Path of Exile 2 Terms of Service. Using this tool carries a risk of account suspension or ban. Use at your own risk. The authors are not responsible for any consequences.

## Notes

- Run the game as administrator if the bot can't read memory
- `keyboard` library may require admin privileges on some systems
- Controller mode requires `vgamepad` (Windows only)
- GUI mode requires Tkinter (bundled with Python on Windows)
