#!/bin/bash
# Connect a HORI Wireless Controller Light (PS4-133) over Bluetooth.
# Put the controller in pairing mode first:
#   hold SHARE + PS together for ~5 seconds until the lightbar BLINKS.
set -u
echo "Put the controller in pairing mode (hold SHARE + PS ~5s until the lightbar blinks)..."
bluetoothctl power on   >/dev/null 2>&1
bluetoothctl pairable on >/dev/null 2>&1

find_mac(){ bluetoothctl devices 2>/dev/null | grep -i 'HORI' | head -1 | awk '{print $2}'; }

MAC=""
for r in $(seq 1 20); do
  bluetoothctl --timeout 6 scan on >/dev/null 2>&1
  MAC="$(find_mac)"
  [ -n "$MAC" ] && break
  echo "  scanning... ($r/20)"
done
[ -n "$MAC" ] || { echo "Controller not found. Make sure it is blinking and nearby, then retry."; exit 1; }

echo "Found controller: $MAC  — connecting..."
{ echo 'agent NoInputNoOutput'; sleep 1; echo 'default-agent'; sleep 1;
  echo "connect $MAC"; sleep 14; echo "trust $MAC"; sleep 1; echo quit; } | bluetoothctl >/dev/null 2>&1
sleep 2
if bluetoothctl info "$MAC" | grep -q 'Connected: yes'; then
  echo "Connected! The controller is ready to use."
  echo "(From now on, just press the PS button once to reconnect.)"
else
  echo "Could not connect this time. Put it in pairing mode again and re-run this script."
  exit 1
fi
