#!/usr/bin/with-contenv bashio
set -eu

SOURCE=/opt/coastal-water-watch/coastal_water_watch
COMPONENTS=/homeassistant/custom_components
TARGET="$COMPONENTS/coastal_water_watch"
STAGING="$COMPONENTS/.coastal_water_watch.new"
BACKUP="$COMPONENTS/.coastal_water_watch.previous"

if [ ! -f "$SOURCE/manifest.json" ]; then
    bashio::log.fatal "Bundled Coastal Water Watch integration is missing"
    exit 1
fi

mkdir -p "$COMPONENTS"
rm -rf "$STAGING"
mkdir -p "$STAGING"
cp -a "$SOURCE/." "$STAGING/"

if [ -d "$TARGET" ]; then
    rm -rf "$BACKUP"
    mv "$TARGET" "$BACKUP"
fi

if ! mv "$STAGING" "$TARGET"; then
    bashio::log.error "Installation failed; restoring the previous integration"
    rm -rf "$TARGET"
    if [ -d "$BACKUP" ]; then
        mv "$BACKUP" "$TARGET"
    fi
    exit 1
fi

bashio::log.info "Coastal Water Watch 0.4.1 was installed successfully."
bashio::log.info "Restart Home Assistant, then add or reload Coastal Water Watch under Settings > Devices & services."

