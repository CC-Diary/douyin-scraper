#!/bin/bash
# 设置 macOS 开机自动抓取 (launchd)
# 用法: ./setup-auto.sh [hour] [minute]
# 例如: ./setup-auto.sh 9 0  (每天早上9点)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HOUR="${1:-9}"
MINUTE="${2:-0}"
PLIST_NAME="com.douyin-scraper"
PLIST_PATH="$HOME/Library/LaunchAgents/${PLIST_NAME}.plist"
PYTHON_PATH="$(which python3)"

echo "========================================="
echo "  设置开机自动抓取"
echo "========================================="
echo ""

# 创建日志目录
mkdir -p "$SCRIPT_DIR/logs"

# 生成 plist 文件
cat > "$PLIST_PATH" << PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${PLIST_NAME}</string>

    <key>ProgramArguments</key>
    <array>
        <string>${PYTHON_PATH}</string>
        <string>${SCRIPT_DIR}/scraper.py</string>
    </array>

    <key>WorkingDirectory</key>
    <string>${SCRIPT_DIR}</string>

    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>${HOUR}</integer>
        <key>Minute</key>
        <integer>${MINUTE}</integer>
    </dict>

    <key>StandardOutPath</key>
    <string>${SCRIPT_DIR}/logs/launchd-stdout.log</string>

    <key>StandardErrorPath</key>
    <string>${SCRIPT_DIR}/logs/launchd-stderr.log</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
    </dict>
</dict>
</plist>
PLIST

# 加载任务
launchctl unload "$PLIST_PATH" 2>/dev/null
launchctl load "$PLIST_PATH"

echo "[✓] 定时任务已设置!"
echo ""
echo "  时间: 每天 ${HOUR}:$(printf '%02d' $MINUTE)"
echo "  配置: ${PLIST_PATH}"
echo "  日志: ${SCRIPT_DIR}/logs/"
echo ""
echo "管理命令:"
echo "  查看状态: launchctl list | grep douyin"
echo "  手动运行: python3 ${SCRIPT_DIR}/scraper.py"
echo "  停用:     launchctl unload ${PLIST_PATH}"
echo "  启用:     launchctl load ${PLIST_PATH}"
echo "  删除:     launchctl unload ${PLIST_PATH} && rm ${PLIST_PATH}"
