#!/bin/bash
# setup_cron.sh — 一键设置每日定时任务
# 用法：bash setup_cron.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON="$(which python3)"
LOG_DIR="$SCRIPT_DIR/logs"

mkdir -p "$LOG_DIR"

# 每天早上 8:00 运行（日本时间需确认服务器时区）
CRON_LINE="0 8 * * * cd $SCRIPT_DIR && GEMINI_API_KEY=\$GEMINI_API_KEY $PYTHON $SCRIPT_DIR/coffee_agent.py >> $LOG_DIR/agent_\$(date +\%Y\%m\%d).log 2>&1"

# 写入 crontab
(crontab -l 2>/dev/null | grep -v "coffee_agent"; echo "$CRON_LINE") | crontab -

echo "✅ cron 任务已设置："
echo "   $CRON_LINE"
echo ""
echo "⚠️  注意：请确保 GEMINI_API_KEY 已写入 ~/.bashrc 或 ~/.zshrc"
echo "   例：export GEMINI_API_KEY='AIzaSy...'"
echo ""
echo "查看当前 crontab："
crontab -l
