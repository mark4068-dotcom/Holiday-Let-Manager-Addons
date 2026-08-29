#!/usr/bin/with-contenv bashio
set -e
export OPTIONS_PATH=/data/options.json
export DATA_DIR=/data/hlm-ferry-status
export CHROMIUM_PATH=/usr/bin/chromium-browser
exec node /app/src/server.js
