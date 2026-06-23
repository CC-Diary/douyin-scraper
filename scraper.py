#!/usr/bin/env python3
"""
抖音博主内容抓取工具
抓取对标账号的视频标题、口播文案（Whisper转录），推送到飞书多维表格

用法:
  python3 scraper.py              # 只抓取元数据（快）
  python3 scraper.py --transcribe # 抓取 + 转录口播文案（慢，每视频约10-30秒）
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

import httpx

BASE_DIR = Path(__file__).parent
CONFIG_FILE = BASE_DIR / "config.json"
OUTPUT_DIR = BASE_DIR / "output"
LOG_DIR = BASE_DIR / "logs"
WHISPER_MODEL = None


def load_config():
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)


def extract_sec_uid(url: str) -> str | None:
    match = re.search(r"/user/([A-Za-z0-9_-]+)", url)
    return match.group(1) if match else None


def parse_cookie_string(cookie_str: str) -> dict:
    cookies = {}
    for item in cookie_str.split(";"):
        item = item.strip()
        if "=" in item:
            k, v = item.split("=", 1)
            cookies[k.strip()] = v.strip()
    return cookies


def create_client(config: dict) -> httpx.Client:
    cookie_str = config.get("cookie", "")
    cookies = parse_cookie_string(cookie_str)
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Referer": "https://www.douyin.com/",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9",
    }
    client = httpx.Client(headers=headers, cookies=cookies, follow_redirects=True, timeout=30)
    client.get("https://www.douyin.com/")
    return client


def load_whisper():
    global WHISPER_MODEL
    if WHISPER_MODEL is None:
        import whisper
        print("  [*] 加载 Whisper tiny 模型...")
        WHISPER_MODEL = whisper.load_model("tiny")
    return WHISPER_MODEL


def transcribe_video(client: httpx.Client, video_url: str) -> str:
    """下载视频并用 Whisper 转录口播文案"""
    tmp_video = tempfile.mktemp(suffix=".mp4")
    tmp_audio = tempfile.mktemp(suffix=".wav")

    try:
        # 下载视频
        resp = client.get(video_url, timeout=60)
        with open(tmp_video, "wb") as f:
            f.write(resp.content)

        # 提取音频
        subprocess.run(
            ["ffmpeg", "-i", tmp_video, "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", tmp_audio, "-y"],
            capture_output=True, timeout=60,
        )

        # Whisper 转录
        model = load_whisper()
        result = model.transcribe(tmp_audio, language="zh")
        return result["text"].strip()
    except Exception as e:
        return f"[转录失败: {e}]"
    finally:
        for f in [tmp_video, tmp_audio]:
            if os.path.exists(f):
                os.remove(f)


def fetch_user_videos(client: httpx.Client, sec_uid: str, do_transcribe: bool = False) -> dict:
    """获取用户视频列表，可选转录口播文案"""
    # 获取用户信息
    info_url = "https://www.douyin.com/aweme/v1/web/user/profile/other/"
    resp = client.get(info_url, params={"sec_user_id": sec_uid})
    nickname = "未知"
    try:
        info = resp.json()
        nickname = info.get("user", {}).get("nickname", "未知")
    except Exception:
        pass

    # 获取视频列表
    videos = []
    max_cursor = "0"
    for _ in range(5):
        api_url = "https://www.douyin.com/aweme/v1/web/aweme/post/"
        params = {"sec_user_id": sec_uid, "count": "20", "max_cursor": max_cursor, "aid": "6383"}
        resp = client.get(api_url, params=params)
        try:
            data = resp.json()
            aweme_list = data.get("aweme_list", [])
            if not aweme_list:
                break
            for aweme in aweme_list:
                vid = aweme.get("aweme_id", "")
                desc = aweme.get("desc", "")
                stats = aweme.get("statistics", {})
                create_time = aweme.get("create_time", 0)
                video_url = aweme.get("video", {}).get("play_addr", {}).get("url_list", [""])[0]
                videos.append({
                    "id": vid,
                    "title": desc.split("\n")[0] if desc else "",
                    "description": desc,
                    "url": f"https://www.douyin.com/video/{vid}",
                    "video_url": video_url,
                    "create_time": create_time,
                    "likes": stats.get("digg_count", 0),
                    "comments": stats.get("comment_count", 0),
                    "shares": stats.get("share_count", 0),
                    "collects": stats.get("collect_count", 0),
                    "transcript": "",
                })
            max_cursor = str(data.get("max_cursor", ""))
            if not data.get("has_more", 0):
                break
            time.sleep(1)
        except Exception as e:
            print(f"  [!] API 解析失败: {e}")
            break

    # 只转录最近2天的视频
    if do_transcribe and videos:
        cutoff = time.time() - 2 * 86400  # 2天前的时间戳
        recent = [v for v in videos if v.get("create_time", 0) >= cutoff]
        if recent:
            print(f"  [*] 最近2天有 {len(recent)} 个视频，正在转录...")
            for i, v in enumerate(recent, 1):
                if v.get("video_url"):
                    print(f"  [{i}/{len(recent)}] {v['title'][:30]}...", end=" ", flush=True)
                    transcript = transcribe_video(client, v["video_url"])
                    v["transcript"] = transcript
                    print(f"✓ ({len(transcript)}字)")
                    time.sleep(1)
        else:
            print(f"  [*] 最近2天无新视频，跳过转录")

    return {"nickname": nickname, "videos": videos}


def save_as_markdown(account_name: str, videos: list[dict], date_str: str):
    account_dir = OUTPUT_DIR / re.sub(r'[\\/:*?"<>|]', "_", account_name)
    account_dir.mkdir(parents=True, exist_ok=True)

    filepath = account_dir / f"{date_str}.md"
    lines = [
        f"# {account_name} - {date_str}",
        "",
        f"> 抓取时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"> 视频数量: {len(videos)}",
        "",
        "---",
        "",
    ]

    for i, v in enumerate(videos, 1):
        lines.append(f"## {i}. {v.get('title', '无标题')}")
        lines.append("")
        lines.append(f"- **链接**: {v.get('url', '')}")
        if v.get("create_time"):
            dt = datetime.fromtimestamp(v["create_time"])
            lines.append(f"- **发布时间**: {dt.strftime('%Y-%m-%d %H:%M')}")
        for key, label in [("likes", "点赞"), ("comments", "评论"), ("shares", "分享"), ("collects", "收藏")]:
            val = v.get(key, 0)
            if val:
                lines.append(f"- **{label}**: {val:,}")
        lines.append("")
        if v.get("transcript"):
            lines.append("**口播文案**:")
            lines.append("")
            lines.append(f"> {v['transcript']}")
            lines.append("")
        elif v.get("description"):
            lines.append("**描述**:")
            lines.append("")
            lines.append(f"> {v['description']}")
            lines.append("")
        lines.append("---")
        lines.append("")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    json_path = account_dir / f"{date_str}.json"
    save_data = [{k: v for k, v in vid.items() if k != "video_url"} for vid in videos]
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(save_data, f, ensure_ascii=False, indent=2)

    return filepath


def setup_logging():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.log"

    class TeeOutput:
        def __init__(self, *streams):
            self.streams = streams
        def write(self, data):
            for s in self.streams:
                s.write(data)
                s.flush()
        def flush(self):
            for s in self.streams:
                s.flush()

    log_f = open(log_file, "a", encoding="utf-8")
    tee = TeeOutput(sys.__stdout__, log_f)
    sys.stdout = tee
    sys.stderr = tee
    return log_file


def main():
    do_transcribe = "--transcribe" in sys.argv

    log_file = setup_logging()

    print("=" * 50)
    mode = "抓取 + 口播转录" if do_transcribe else "仅抓取元数据"
    print(f"  抖音博主内容抓取工具 - {mode}")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    config = load_config()
    accounts = config.get("accounts", [])

    if not accounts:
        print("[!] 请先在 config.json 中配置对标账号")
        return
    if not config.get("cookie"):
        print("[!] 请先配置抖音 Cookie")
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("\n[1/4] 初始化会话...")
    client = create_client(config)

    today = datetime.now().strftime("%Y-%m-%d")
    all_results = {}

    print(f"\n[2/4] 开始抓取 {len(accounts)} 个账号...")
    for i, account in enumerate(accounts, 1):
        name = account["name"]
        sec_uid = extract_sec_uid(account["douyin_url"])
        if not sec_uid:
            print(f"\n  [{i}/{len(accounts)}] {name} - 无法解析链接")
            continue

        print(f"\n  [{i}/{len(accounts)}] {name}")
        result = fetch_user_videos(client, sec_uid, do_transcribe=do_transcribe)
        videos = result["videos"]
        real_name = result["nickname"]
        if real_name and real_name != "未知":
            name = real_name
            print(f"  昵称: {name}")
        print(f"  视频: {len(videos)} 个")

        if videos:
            filepath = save_as_markdown(name, videos, today)
            print(f"  [✓] 已保存: {filepath}")
            all_results[name] = videos
        else:
            all_results[name] = []
        time.sleep(2)

    client.close()

    # 推送飞书
    feishu_config = config.get("feishu", {})
    if feishu_config.get("app_id"):
        print(f"\n[3/4] 推送到飞书多维表格...")
        try:
            from feishu import push_to_feishu
            for name, videos in all_results.items():
                if videos:
                    push_to_feishu(config, name, videos)
        except Exception as e:
            print(f"  [!] 飞书推送失败: {e}")
    else:
        print(f"\n[3/4] 飞书未配置，跳过推送")

    # 汇总
    print(f"\n[4/4] 生成汇总...")
    summary_path = OUTPUT_DIR / f"summary-{today}.md"
    lines = [
        f"# 每日抓取汇总 - {today}",
        "",
        "| 博主 | 视频数 |",
        "|------|--------|",
    ]
    for name, videos in all_results.items():
        lines.append(f"| {name} | {len(videos)} |")
    lines.append("")
    lines.append(f"抓取时间: {datetime.now().strftime('%H:%M:%S')}")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    total = sum(len(v) for v in all_results.values())
    print(f"\n{'=' * 50}")
    print(f"  完成! 共抓取 {total} 个视频")
    print(f"  输出目录: {OUTPUT_DIR}")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    main()
