#!/bin/sh
# Re-copy the shared files into every skill that needs them.
cd "$(dirname "$0")/../skills" || exit 1
for d in yt-chapters yt-retention; do cp yt-edit/transcript.py "$d/"; done
cp yt-script/hooks.json yt-viral/
