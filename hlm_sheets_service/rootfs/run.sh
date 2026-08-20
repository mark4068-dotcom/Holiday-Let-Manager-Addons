#!/bin/sh
set -eu

credential_path="/data/google-service-account.json"

python3 - <<'PY'
import json
import os
from pathlib import Path

options = json.loads(Path("/data/options.json").read_text(encoding="utf-8"))
raw_credentials = options.get("google_service_account_json", "")
try:
    credentials = json.loads(raw_credentials)
except (TypeError, json.JSONDecodeError):
    raise SystemExit("ERROR: Configure a valid Google service-account JSON value.")

if not all(credentials.get(key) for key in ("client_email", "private_key", "token_uri")):
    raise SystemExit("ERROR: Google service-account JSON is incomplete.")

path = Path("/data/google-service-account.json")
path.write_text(json.dumps(credentials), encoding="utf-8")
os.chmod(path, 0o600)
PY

api_token="$(python3 -c '
import json
from pathlib import Path
print(json.loads(Path("/data/options.json").read_text())["api_token"])
')"

if [ "${#api_token}" -lt 32 ]; then
  echo "ERROR: Configure an API token of at least 32 characters in the add-on."
  exit 1
fi

export GOOGLE_APPLICATION_CREDENTIALS="${credential_path}"
export HLM_SHEETS_API_TOKEN="${api_token}"
export HLM_SHEETS_SPREADSHEET_ID="1KqEwDLxnCL6SUQi8ePqOFskd1IIv6btsXQw2VKN5-Ko"
export HLM_SHEETS_STATUS_RANGE="20_published_ha!A1:R"
export HLM_SHEETS_HOST="0.0.0.0"
export HLM_SHEETS_PORT="8787"

exec python3 -m hlm_sheets_service.app
