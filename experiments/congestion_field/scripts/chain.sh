#!/bin/sh
# Wait until no launcher is running, then run the given jobsets: sh scripts/chain.sh <log> <jobset>...
cd "$(dirname "$0")/.."
while ps -eo args | grep -q "^sh scripts/launch.sh"; do sleep 30; done
exec sh scripts/launch.sh "$@"
