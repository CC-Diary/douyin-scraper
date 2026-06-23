#!/bin/bash
# 每日自动流程：抓取 → 分析
cd "$(dirname "$0")"

echo "[$(date)] 开始每日抓取+分析"

# 1. 抓取 + 口播转录
python3 scraper.py --transcribe >> logs/daily.log 2>&1

# 2. 选题分析
python3 analyze.py >> logs/daily.log 2>&1

echo "[$(date)] 完成"
