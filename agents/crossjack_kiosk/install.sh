#!/bin/bash

set -euo pipefail

SOURCE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="${HOME}/.local/share/hlm-kiosk-agent"
SERVICE_DIR="${HOME}/.config/systemd/user"
CONFIG_FILE="${HOME}/.config/hlm-kiosk-agent.json"

install -d -m 0755 "${APP_DIR}" "${SERVICE_DIR}"
install -m 0755 "${SOURCE_DIR}/hlm_kiosk_agent.py" "${APP_DIR}/hlm_kiosk_agent.py"
install -m 0644 "${SOURCE_DIR}/hlm-kiosk-agent.service" "${SERVICE_DIR}/hlm-kiosk-agent.service"

python3 -m venv "${APP_DIR}/venv"
"${APP_DIR}/venv/bin/pip" install \
  --disable-pip-version-check \
  --requirement "${SOURCE_DIR}/requirements.txt"
"${APP_DIR}/venv/bin/python" -m py_compile "${APP_DIR}/hlm_kiosk_agent.py"

systemctl --user daemon-reload
if [[ -f "${CONFIG_FILE}" ]]; then
  chmod 0600 "${CONFIG_FILE}"
  systemctl --user enable --now hlm-kiosk-agent.service
  systemctl --user --no-pager status hlm-kiosk-agent.service
else
  printf 'Installed but not started: create %s from config.example.json first.\n' "${CONFIG_FILE}"
fi
