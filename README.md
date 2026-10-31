# HORI Wireless Controller Light (PS4-133) → Steam Deck, wirelessly

Make the **HORI Wireless Controller Light (PS4-133 / PS4-133A)** work over
**Bluetooth on a Steam Deck (SteamOS)** — menus, games, everything.

> Out of the box this controller **cannot** connect to a Steam Deck over
> Bluetooth. It speaks a PS4-only variant of the SDP handshake, and the
> Steam Deck's BlueZ rejects it (`sdp_process: Protocol error: transaction
> id does not match`). This project fixes that.

Wired USB has always worked. **This makes it work wirelessly.**

---

## TL;DR — one‑touch install

In **Desktop Mode** on the Steam Deck:

```bash
git clone https://github.com/momomorin/hori-ps4-133-steamdeck.git
cd hori-ps4-133-steamdeck
bash install.sh
```

Wait ~10–30 min (it builds a patched `bluetoothd`), **reboot**, then:

1. Put the controller in pairing mode: hold **SHARE + PS** for ~5 s until the lightbar blinks.
2. Run `bash ~/hori-connect.sh`.

After the first pairing, just press **PS** to reconnect. The controller shows
up in Steam (Game Mode menus and games) as a normal gamepad.

---

## Why it doesn't work by default

When the host asks the controller for its services (SDP), the PS4-133 does
**not** answer — instead it sends its *own* SDP request back on the same
channel (asking "are you a PS4? give me your PnP info"), and it treats the
host's request as the reply. A real PS4 plays along; desktop BlueZ sees a
mismatched transaction id and drops the link.

## What the fix does

1. **Patches BlueZ `sdp_process()`** so that when the controller sends an SDP
   request on the client channel, the host answers as a **Sony PS4 host**
   (PnP record, VendorID `0x054C`) and re-sends its own request once. The
   controller then returns its HID record and the connection completes.
   (`patch.py` applies this to the matching BlueZ source automatically.)
2. `ClassicBondedOnly=false` in `input.conf` so HID is allowed before bonding.
3. Loads the `hidp` kernel module.
4. Extends the Bluetooth page timeout (the controller drops fast right after
   pairing; the longer timeout lets the HID link establish).
5. Sets `SDL_JOYSTICK_HIDAPI_PS4=0` so Steam uses the kernel input instead of
   mis-parsing this clone as a genuine DualShock 4 (otherwise the left
   trigger sticks and buttons do nothing).

Everything is installed to update-safe locations (`/var`, `~/.config`), with a
systemd drop-in that points `bluetooth.service` at the patched binary.

## Files

| File | Purpose |
|------|---------|
| `install.sh` | one-touch installer (run this) |
| `incontainer.sh` | builds the patched `bluetoothd` inside a Debian distrobox |
| `patch.py` | applies the SDP quirk to the BlueZ source (version-tolerant) |
| `connect.sh` | pairs/connects the controller (installed as `~/hori-connect.sh`) |

## Compatibility

- Steam Deck / SteamOS (x86_64). `distrobox` ships with SteamOS.
- The build auto-detects your BlueZ version (`bluetoothctl --version`).
  Verified on **BlueZ 5.87**; the patch is written to apply to other 5.x too.
- Needs internet during install (to fetch the BlueZ source).

## After a SteamOS update

Major SteamOS updates can wipe `/usr` and some of `/etc`. If the controller
stops connecting, just re-run `bash install.sh`.

## Notes / safety

- This builds a patched `bluetoothd` from official BlueZ sources; it does not
  replace your system binary in place (it runs the patched one via a systemd
  drop-in, leaving the original untouched).
- Use at your own risk. See `LICENSE` (MIT).

## Credits

Reverse-engineered from `btmon` captures and fixed by trial on real hardware.
If it helped you, a ⭐ is appreciated — and please open an issue with your
SteamOS / BlueZ version if you hit a snag.
