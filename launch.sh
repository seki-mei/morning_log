#!/bin/zsh
pkill -f "morning_log/main.py" && echo "killed"
sleep 0.5
nohup python3 ~/morning_log/main.py > /dev/null 2>&1 &
disown
