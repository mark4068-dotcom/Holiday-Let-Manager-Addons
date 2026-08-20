#!/bin/sh
set -eu

credential_path="/config/google-service-account.json"

if [ ! -r "${credential_path}" ]; then
  echo "ERROR: Google service-account key is missing at ${credential_path}."
  echo "Copy it into this add-on's private configuration folder before starting."
  exit 1
fi

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
