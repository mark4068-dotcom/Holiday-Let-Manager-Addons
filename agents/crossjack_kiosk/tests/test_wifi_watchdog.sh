#!/bin/bash
set -euo pipefail

TEST_ROOT="$(mktemp -d)"
trap 'rm -rf -- "${TEST_ROOT}"' EXIT
FAKE_BIN="${TEST_ROOT}/bin"
STATE_DIR="${TEST_ROOT}/state"
mkdir -p "$FAKE_BIN" "$STATE_DIR"

printf '%s\n' \
  '#!/bin/bash' \
  'if [[ "$1" == "-t" ]]; then' \
  '  [[ "${FAKE_CONNECTED:-0}" == 1 ]] || exit 1' \
  '  printf "GENERAL.STATE:100 (connected)\\n"' \
  'fi' > "${FAKE_BIN}/nmcli"
printf '%s\n' \
  '#!/bin/bash' \
  '[[ "${FAKE_CONNECTED:-0}" == 1 ]]' > "${FAKE_BIN}/ping"
printf '%s\n' '#!/bin/bash' 'exit 0' > "${FAKE_BIN}/logger"
printf '%s\n' '#!/bin/bash' 'exit 0' > "${FAKE_BIN}/sleep"
printf '%s\n' '#!/bin/bash' 'printf "2026-09-09T12:00:00+00:00\\n"' > "${FAKE_BIN}/date"
chmod 0755 "${FAKE_BIN}/nmcli" "${FAKE_BIN}/ping" "${FAKE_BIN}/logger" "${FAKE_BIN}/sleep" "${FAKE_BIN}/date"

WATCHDOG="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)/network_watchdog/crossjack-wifi-watchdog"
export PATH="${FAKE_BIN}:/usr/bin:/bin"
export STATE_DIR

printf '%s\n' '{"failure_count":2,"recovery_count":4,"last_recovery_at":"2026-09-01T10:00:00+00:00","last_recovery_reason":"test"}' > "${STATE_DIR}/wifi-watchdog.json"
FAKE_CONNECTED=1 "$WATCHDOG"
grep -q '"failure_count":0' "${STATE_DIR}/wifi-watchdog.json"
grep -q '"recovery_count":4' "${STATE_DIR}/wifi-watchdog.json"
grep -q '"last_recovery_at":"2026-09-01T10:00:00+00:00"' "${STATE_DIR}/wifi-watchdog.json"

FAKE_CONNECTED=0 "$WATCHDOG"
FAKE_CONNECTED=0 "$WATCHDOG"
FAKE_CONNECTED=0 "$WATCHDOG"
grep -q '"failure_count":0' "${STATE_DIR}/wifi-watchdog.json"
grep -q '"recovery_count":5' "${STATE_DIR}/wifi-watchdog.json"
grep -q '"last_recovery_at":"2026-09-09T12:00:00+00:00"' "${STATE_DIR}/wifi-watchdog.json"
grep -q '"last_recovery_reason":"gateway_or_home_assistant_unreachable"' "${STATE_DIR}/wifi-watchdog.json"

printf 'Wi-Fi watchdog tests passed\n'
