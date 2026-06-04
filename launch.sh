#!/bin/zsh
DIR="$(cd "$(dirname "$0")" && pwd)"
pkill -f "morning_log/main.py" && echo "killed"
sleep 0.5
nohup python3 "$DIR/main.py" > /dev/null 2>&1 &
disown
