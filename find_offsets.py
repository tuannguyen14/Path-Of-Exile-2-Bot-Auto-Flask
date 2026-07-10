"""
Helper script: Tìm BASE_OFFSET tự động bằng AOB pattern scanning.

Cách dùng:
  python find_offsets.py

Script sẽ:
  1. Kết nối PathOfExile.exe
  2. Scan AOB pattern (nếu có) để tìm BASE_OFFSET mới
  3. Test đọc HP/Mana để xác nhận offset đúng
  4. In ra BASE_OFFSET mới để copy vào botXbox.py

Nếu chưa có AOB_PATTERN, script sẽ dùng BASE_OFFSET hiện tại để test.
"""

import pymem
import pymem.process
import re
import struct
import sys

# ============================================================
# CONFIG - Copy từ botXbox.py
# ============================================================
PROCESS_NAME    = "PathOfExile.exe"
AOB_PATTERN     = None  # ← Paste AOB pattern ở đây, vd: "45 8B F8 45 2B F9 40 38"
BASE_OFFSET     = 0x0438CFE0  # ← Mới từ ảnh Cheat Engine user gửi

# Offsets mới tìm bằng CE MCP (Max = Cur + 4)
OFFSETS_HP       = [0x38, 0x18, 0xB8, 0x30, 0x28, 0x28, 0x3D0]
OFFSETS_MAX_HP   = [0x38, 0x18, 0xB8, 0x30, 0x28, 0x28, 0x3D4]
OFFSETS_MANA     = [0x38, 0x18, 0xB8, 0x30, 0x28, 0x28, 0x800]
OFFSETS_MAX_MANA = [0x38, 0x18, 0xB8, 0x30, 0x28, 0x28, 0x804]
OFFSETS_ES       = [0x38, 0x18, 0xB8, 0x30, 0x28, 0x28, 0x3DC]
OFFSETS_MAX_ES   = [0x38, 0x18, 0xB8, 0x30, 0x28, 0x28, 0x3E0]


def scan_aob(pm, pattern_str, module_name="PathOfExile.exe"):
    """Scan module memory để tìm AOB pattern, trả về offset từ module base."""
    module = pymem.process.module_from_name(pm.process_handle, module_name)
    if not module:
        print(f"❌ Không tìm thấy module '{module_name}'")
        return None

    module_base = module.lpBaseOfDll
    module_size = module.SizeOfImage
    print(f"📦 Module: {module_name} @ 0x{module_base:X}, size: 0x{module_size:X} ({module_size // 1024 // 1024} MB)")

    print(f"🔍 Đang scan AOB pattern: {pattern_str}")
    module_bytes = pm.read_bytes(module_base, module_size)

    parts = pattern_str.strip().split()
    regex_parts = []
    for p in parts:
        if p == "??" or p == "?":
            regex_parts.append(b".")
        else:
            regex_parts.append(re.escape(bytes([int(p, 16)])))
    regex = b"".join(regex_parts)

    matches = list(re.finditer(regex, module_bytes, re.DOTALL))
    if not matches:
        print("❌ Không tìm thấy pattern!")
        return None

    print(f"✅ Tìm thấy {len(matches)} match(es):")
    for i, m in enumerate(matches[:5]):
        offset = m.start()
        abs_addr = module_base + offset
        print(f"   [{i}] Offset: 0x{offset:X}  |  Absolute: 0x{abs_addr:X}")

    if len(matches) > 1:
        print(f"⚠️  Có nhiều match — chọn match đầu tiên. Hãy thu hẹp pattern để unique!")

    return matches[0].start()


def read_pointer_chain(pm, base_address, offsets):
    """Đọc giá trị int từ pointer chain."""
    address = pm.read_longlong(base_address)
    for offset in offsets[:-1]:
        address = pm.read_longlong(address + offset)
    return pm.read_int(address + offsets[-1])


def test_offsets(pm, base_address, label=""):
    """Test đọc HP/Mana để xác nhận offset đúng."""
    print(f"\n🧪 Test đọc giá trị {label}...")
    results = {}
    try:
        if OFFSETS_HP:
            results["CurHP"] = read_pointer_chain(pm, base_address, OFFSETS_HP)
        if OFFSETS_MAX_HP:
            results["MaxHP"] = read_pointer_chain(pm, base_address, OFFSETS_MAX_HP)
        if OFFSETS_MANA:
            results["CurMana"] = read_pointer_chain(pm, base_address, OFFSETS_MANA)
        if OFFSETS_MAX_MANA:
            results["MaxMana"] = read_pointer_chain(pm, base_address, OFFSETS_MAX_MANA)
        if OFFSETS_ES:
            results["CurES"] = read_pointer_chain(pm, base_address, OFFSETS_ES)
        if OFFSETS_MAX_ES:
            results["MaxES"] = read_pointer_chain(pm, base_address, OFFSETS_MAX_ES)

        for k, v in results.items():
            print(f"   {k}: {v}")

        # Sanity check: Mana nên là số dương hợp lý
        values = [v for v in results.values() if isinstance(v, int)]
        valid = all(0 < v < 100000 for v in values)
        if valid and ("CurMana" in results or "MaxMana" in results):
            print("   ✅ Mana offset đúng!")
        elif results:
            print("   ❌ Giá trị bất thường — OFFSET SAI, cần tìm lại!")
        return valid
    except Exception as e:
        print(f"   ❌ Lỗi đọc: {e}")
        return False


def resolve_pointer_chain_to_base(pm, base_address, offsets_without_last):
    """Follow pointer chain đến địa chỉ struct cuối (chưa + offset cuối)."""
    address = pm.read_longlong(base_address)
    for offset in offsets_without_last:
        address = pm.read_longlong(address + offset)
    return address


def scan_stats_near_mana(pm, base_address, expected_hp=None, expected_es=None):
    """
    Scan vùng nhớ quanh Mana struct để tìm HP/ES.
    expected_hp/es: giá trị hiện tại trong game (để match).
    """
    if not expected_hp and not expected_es:
        print("\nℹ️  Không có expected HP/ES → bỏ qua scan")
        return

    try:
        # Resolve chain đến struct base (bỏ 2 offset cuối: 0x40, 0x824)
        struct_base = resolve_pointer_chain_to_base(pm, base_address, [0x38, 0x0, 0x38, 0x30, 0x4C])
        print(f"\n🔍 Scan vùng struct quanh 0x{struct_base:X}")

        # Đọc 4096 bytes xung quanh struct
        data = pm.read_bytes(struct_base - 0x400, 0x1000)
        ints = struct.unpack(f"<{len(data) // 4}I", data)

        for i, val in enumerate(ints):
            offset = i * 4 - 0x400
            if expected_hp and val == expected_hp:
                print(f"   ✅ Tìm thấy HP = {val} tại offset 0x{offset & 0xFFFFFFFF:X}")
            if expected_es and val == expected_es:
                print(f"   ✅ Tìm thấy ES = {val} tại offset 0x{offset & 0xFFFFFFFF:X}")
    except Exception as e:
        print(f"   ❌ Lỗi scan: {e}")


def main():
    print("=" * 60)
    print("  POE2 Offset Finder")
    print("=" * 60)

    try:
        pm = pymem.Pymem(PROCESS_NAME)
        print(f"✅ Đã kết nối {PROCESS_NAME} @ base 0x{pm.base_address:X}")
    except Exception as e:
        print(f"❌ Không thể kết nối: {e}")
        sys.exit(1)

    found_offset = None

    # --- Cách 1: AOB Pattern Scan (tự động) ---
    if AOB_PATTERN:
        found_offset = scan_aob(pm, AOB_PATTERN)
        if found_offset is not None:
            base_address = pm.base_address + found_offset
            print(f"\n🎯 BASE_OFFSET mới = 0x{found_offset:X}")
            test_offsets(pm, base_address, "(AOB auto)")
    else:
        print("\n⚠️  Chưa có AOB_PATTERN — dùng BASE_OFFSET fallback để test")

    # --- Cách 2: Fallback manual offset ---
    if found_offset is None:
        base_address = pm.base_address + BASE_OFFSET
        print(f"\n📍 Dùng BASE_OFFSET fallback: 0x{BASE_OFFSET:X}")
        test_offsets(pm, base_address, "(fallback)")

    # --- Scan tìm HP/ES nếu đã có Mana offset ---
    # Sửa số dưới đây thành HP/ES hiện tại trong game, rồi chạy lại
    scan_stats_near_mana(pm, base_address, expected_hp=1644, expected_es=None)

    # --- Hướng dẫn ---
    print("\n" + "=" * 60)
    print("  HƯỚNG DẪN TÌM AOB PATTERN (chỉ làm 1 lần):")
    print("=" * 60)
    print("""
1. Mở Cheat Engine → attach PathOfExile.exe
2. Tìm địa chỉ HP (currentHP) như bình thường
3. Right-click địa chỉ HP → "Find out what accesses this address"
4. Vào game, để HP thay đổi → CE sẽ bắt lệnh truy cập
5. Chọn lệnh → right-click → "Show disassembly"
6. Tại dòng lệnh, copy khoảng 15-20 bytes xung quanh
7. Thay các byte có thể đổi (địa chỉ relative) bằng ??
   vd: 48 8B 05 ?? ?? ?? ?? 48 85 C0 74 ?? 48 8B 80
8. Paste vào AOB_PATTERN trong file này và botXbox.py
9. Chạy lại script để verify

Sau đó mỗi lần game update, AOB scanner sẽ tự tìm BASE_OFFSET mới!
""")


if __name__ == "__main__":
    main()
