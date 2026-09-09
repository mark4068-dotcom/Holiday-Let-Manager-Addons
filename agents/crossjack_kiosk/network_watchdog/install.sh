#!/bin/bash
set -euo pipefail

if [[ ${EUID} -ne 0 ]]; then
  printf 'Run this installer as root: sudo %s\n' "$0" >&2
  exit 1
fi

SOURCE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

install -d -m 0755 /var/lib/crossjack-kiosk
install -m 0755 "${SOURCE_DIR}/crossjack-wifi-watchdog" /usr/local/sbin/crossjack-wifi-watchdog
install -m 0644 "${SOURCE_DIR}/crossjack-wifi-watchdog.service" /etc/systemd/system/crossjack-wifi-watchdog.service
install -m 0644 "${SOURCE_DIR}/crossjack-wifi-watchdog.timer" /etc/systemd/system/crossjack-wifi-watchdog.timer

systemctl daemon-reload
systemctl enable --now crossjack-wifi-watchdog.timer
systemctl --no-pager status crossjack-wifi-watchdog.timer
