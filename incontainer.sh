#!/bin/bash
# Runs INSIDE the debian distrobox. $1 = BlueZ version (e.g. 5.87)
set -e
VER="$1"
export DEBIAN_FRONTEND=noninteractive
echo "[build] installing tools..."
sudo apt-get update -qq
sudo apt-get install -y -qq build-essential wget python3 libglib2.0-dev \
  libdbus-1-dev libudev-dev libical-dev libreadline-dev pkg-config
cd "$HOME"
echo "[build] fetching bluez-$VER source..."
wget -q "https://www.kernel.org/pub/linux/bluetooth/bluez-$VER.tar.xz" -O bluez.tar.xz
rm -rf "bluez-$VER"; tar xf bluez.tar.xz
echo "[build] applying HORI quirk patch..."
python3 "$HOME/hori-patch.py" "bluez-$VER"
cd "bluez-$VER"
echo "[build] configure + make (数分かかります)..."
./configure --disable-obex --disable-cups --disable-mesh --disable-monitor \
  --disable-tools --disable-client --disable-manpages --disable-systemd \
  --with-udevdir=/lib/udev >/tmp/hori-conf.log 2>&1
make -j"$(nproc)" >/tmp/hori-make.log 2>&1 || { echo "[build] make 失敗"; tail -20 /tmp/hori-make.log; exit 1; }
cp src/bluetoothd "$HOME/bluetoothd-hori"
echo "[build] done: $HOME/bluetoothd-hori"
