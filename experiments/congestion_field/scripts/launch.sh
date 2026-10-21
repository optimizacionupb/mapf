#!/bin/sh
# Run several jobsets sequentially in the background: sh scripts/launch.sh <log> <jobset>...
cd "$(dirname "$0")/.."
log=$1; shift
for js in "$@"; do python3 -I scripts/run.py "$js" >> "runs/$log" 2>&1; done
