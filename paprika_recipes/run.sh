#!/bin/sh
set -eu
mkdir -p /share/paprika-recipes
exec python3 -m recipe_dashboard --host 0.0.0.0 --settings /data/options.json --data /data --imports /share/paprika-recipes
