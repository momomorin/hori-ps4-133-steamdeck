#!/bin/bash
# =====================================================================
#  Make a HORI Wireless Controller Light (PS4-133) work WIRELESSLY
#  on a Steam Deck (SteamOS).  One-touch installer.
#
#  Run in Desktop Mode:   bash install.sh
#  Takes ~10-30 min (it builds a patched bluetoothd). Needs internet.
#  https://github.com/momomorin/hori-ps4-133-steamdeck
# =====================================================================
set -e
PKG="$(cd "$(dirname "$0")" && pwd)"
say(){ echo -e "\n==== $* ===="; }

say "HORI PS4-133 -> Steam Deck wireless setup"
VER="$(bluetoothctl --version 2>/dev/null | awk '{print $2}')"
[ -n "$VER" ] || { echo "BlueZ not found. Run this in SteamOS Desktop Mode."; exit 1; }
echo "Detected BlueZ version: $VER"
command -v distrobox >/dev/null || { echo "distrobox is required (ships with SteamOS)."; exit 1; }

say "Step 1/3: build a patched bluetoothd (this takes a while)"
cp "$PKG/incontainer.sh" "$HOME/hori-incontainer.sh"
cp "$PKG/patch.py"       "$HOME/hori-patch.py"
distrobox create --yes --name horibuild --image debian:12 >/dev/null 2>&1 || true
distrobox enter horibuild -- bash "$HOME/hori-incontainer.sh" "$VER"
[ -x "$HOME/bluetoothd-hori" ] || { echo "Build failed."; exit 1; }

say "Step 2/3: install it (you will be asked for your password)"
sudo install -D -m755 "$HOME/bluetoothd-hori" /var/lib/bluez-hori/bluetoothd-hori
sudo install -d /etc/systemd/system/bluetooth.service.d
printf '[Service]\nExecStart=\nExecStart=/var/lib/bluez-hori/bluetoothd-hori\n' \
  | sudo tee /etc/systemd/system/bluetooth.service.d/override.conf >/dev/null
if [ -f /etc/bluetooth/input.conf ]; then
  grep -q '^ClassicBondedOnly=false' /etc/bluetooth/input.conf \
    || sudo sed -i '/^\[General\]/a ClassicBondedOnly=false' /etc/bluetooth/input.conf
else
  printf '[General]\nClassicBondedOnly=false\n' | sudo tee /etc/bluetooth/input.conf >/dev/null
fi
echo hidp | sudo tee /etc/modules-load.d/hidp.conf >/dev/null
sudo modprobe hidp 2>/dev/null || true
printf '[Unit]\nDescription=Extend BT page timeout for HORI PS4-133\nAfter=bluetooth.service\nWants=bluetooth.service\n\n[Service]\nType=oneshot\nExecStart=/usr/bin/hciconfig hci0 pageto 16384\nRemainAfterExit=yes\n\n[Install]\nWantedBy=bluetooth.target\n' \
  | sudo tee /etc/systemd/system/hci-pageto.service >/dev/null
install -D -m755 "$PKG/connect.sh" "$HOME/hori-connect.sh"

say "Step 3/3: let Steam read the controller correctly"
mkdir -p "$HOME/.config/environment.d"
echo 'SDL_JOYSTICK_HIDAPI_PS4=0' > "$HOME/.config/environment.d/10-hori-sdl.conf"

sudo systemctl daemon-reload
sudo systemctl enable hci-pageto.service >/dev/null 2>&1 || true
sudo systemctl restart bluetooth

cat <<MSG

======================================================================
 Done!
 1) REBOOT the Steam Deck.
 2) Put the controller in pairing mode: hold SHARE + PS ~5s (lightbar blinks).
 3) Run:   bash ~/hori-connect.sh
 After the first pairing, just press the PS button to reconnect.
======================================================================
MSG
