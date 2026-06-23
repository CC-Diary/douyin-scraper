#!/bin/bash
# 设置每日定时抓取任务
# 用法: ./setup-cron.sh [hour] [minute]
# 例如: ./setup-cron.sh 9 0  (每天早上9点)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HOUR="${1:-9}"
MINUTE="${2:-0}"

CRON_CMD="$MINUTE $HOUR * * * cd $SCRIPT_DIR && /opt/homebrew/bin/python3 scraper.py >> $SCRIPT_DIR/logs/daily.log 2>&1"

# 创建日志目录
mkdir -p "$SCRIPT_DIR/logs"

# 检查是否已存在
if crontab -l 2>/dev/null | grep -q "douyin-scraper"; then
    echo "⚠️  已存在定时任务，先移除旧任务..."
    crontab -l 2>/dev/null | grep -v "douyin-scraper" | crontab -
fi

# 添加新任务
(crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -

echo "✅ 定时任务已设置!"
echo "   时间: 每天 $HOUR:$MINUTE"
echo "   日志: $SCRIPT_DIR/logs/daily.log"
echo ""
echo "查看任务: crontab -l"
echo "移除任务: crontab -l | grep -v douyin-scraper | crontab -"
