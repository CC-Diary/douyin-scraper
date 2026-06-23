#!/usr/bin/env python3
"""
每日选题分析
1. 读取今天抓取的口播文案
2. 用 cheat-yourself rubric 评分
3. 用柱子哥视角给出改写建议
4. 推送到飞书
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"

# cheat-yourself v1 rubric 维度
RUBRIC = {
    "ER": {"name": "情感共鸣", "weight": 2.0, "desc": "前30秒能否让观众产生具体的、能命名的情感"},
    "HP": {"name": "钩子强度", "weight": 1.5, "desc": "前3秒能不能逼观众看下去30秒"},
    "QL": {"name": "金句密度", "weight": 1.0, "desc": "至少2-3行能被截图、单独传播"},
    "NA": {"name": "叙事性", "weight": 0.5, "desc": "有可辨识的弧线，还是平铺直叙"},
    "AB": {"name": "受众广度", "weight": 0.5, "desc": "潜在受众有多广"},
    "SR": {"name": "社会共振", "weight": 1.0, "desc": "触及当下的社会模式吗"},
}

# 柱子哥核心框架
ZHuzige_Framework = [
    "反差叙事：普通场景 + 反直觉结论",
    "数据具象化：不说'很多人'，说具体数字和案例",
    "四层约束：资料库→草稿→润色→终稿",
    "Skill即生产力：一份system prompt = 一个垂类小模型",
    "口语化金句：能截图传播的短句",
]


def load_today_data() -> dict:
    """读取今天抓取的数据"""
    today = datetime.now().strftime("%Y-%m-%d")
    results = {}

    for account_dir in OUTPUT_DIR.iterdir():
        if not account_dir.is_dir():
            continue
        json_file = account_dir / f"{today}.json"
        if json_file.exists():
            with open(json_file) as f:
                videos = json.load(f)
            # 只取有口播文案的
            with_transcript = [v for v in videos if v.get("transcript")]
            if with_transcript:
                results[account_dir.name] = with_transcript

    return results


def score_topic(video: dict) -> dict:
    """用 rubric 维度给选题打分（AI辅助判断）"""
    title = video.get("title", "")
    transcript = video.get("transcript", "")
    likes = video.get("likes", 0)
    text = f"{title} {transcript}"

    scores = {}

    # ER - 情感共鸣
    er = 3
    emotional_words = ["后悔", "焦虑", "真实", "泪目", "崩溃", "逆袭", "改变命运", "普通人", "底层", "翻身"]
    if any(w in text for w in emotional_words):
        er = 4
    if likes > 10000:
        er = min(5, er + 1)
    scores["ER"] = er

    # HP - 钩子强度
    hp = 3
    hook_patterns = ["你.*知道吗", "别再.*了", "为什么.*不", "我.*之后", "真相是", "千万不要", "后悔", "月薪", "赚了"]
    if any(re.search(p, text[:200]) for p in hook_patterns):
        hp = 4
    if likes > 5000:
        hp = min(5, hp + 1)
    scores["HP"] = hp

    # QL - 金句密度
    ql = 2
    sentences = re.split(r'[。！？\n]', transcript)
    quote_count = sum(1 for s in sentences if 10 < len(s) < 50 and any(kw in s for kw in ["就是", "不是", "而是", "其实", "说白了", "本质上"]))
    if quote_count >= 3:
        ql = 4
    elif quote_count >= 1:
        ql = 3
    scores["QL"] = ql

    # NA - 叙事性
    na = 3
    if "步骤" in text or "第一步" in text or "首先" in text:
        na = 2  # 列表式
    if "故事" in text or "经历" in text or "后来" in text:
        na = 4
    scores["NA"] = na

    # AB - 受众广度
    ab = 3
    niche_topics = ["编程", "代码", "算法", "技术", "开发"]
    broad_topics = ["赚钱", "工作", "生活", "成长", "焦虑", "毕业", "求职"]
    if any(w in text for w in niche_topics):
        ab = 2
    if any(w in text for w in broad_topics):
        ab = 4
    scores["AB"] = ab

    # SR - 社会共振
    sr = 2
    social_patterns = ["内卷", "躺平", "35岁", "裁员", "AI取代", "毕业即失业", "考公", "考编", "副业", "自由职业"]
    if any(w in text for w in social_patterns):
        sr = 4
    if likes > 5000:
        sr = min(5, sr + 1)
    scores["SR"] = sr

    # 综合分
    composite = sum(scores[k] * RUBRIC[k]["weight"] for k in scores) / 6.5 * 2.0

    return {"scores": scores, "composite": round(composite, 1)}


def zhuzige_rewrite_suggestion(video: dict, result: dict) -> str:
    """用柱子哥视角给出改写建议"""
    scores = result["scores"]
    composite = result["composite"]

    suggestions = []

    if scores["ER"] < 4:
        suggestions.append("情感共鸣弱 → 加一个「我后来后悔没早点用」的反转钩子")
    if scores["HP"] < 4:
        suggestions.append("钩子不够锋利 → 开头用具体场景（「上周我朋友问我...」）代替泛泛而谈")
    if scores["QL"] < 3:
        suggestions.append("金句太少 → 在结尾加一句能截图的话，比如「X不是Y，是Z」句式")
    if scores["AB"] < 3:
        suggestions.append("受众偏窄 → 把技术细节换成「省了多少钱/时间」的结果导向")

    # 柱子哥风格建议
    suggestions.append("柱子哥式改写：用「反差」结构 — 先说普通人的做法，再说反直觉的解法")
    suggestions.append("加一句数据具象化：把「很多人」换成具体数字（「我问了50个做自媒体的朋友...」）")

    return "\n".join(f"  • {s}" for s in suggestions)


def generate_report(all_results: dict) -> str:
    """生成分析报告"""
    today = datetime.now().strftime("%Y-%m-%d")
    lines = [
        f"# 每日选题分析 - {today}",
        "",
    ]

    all_scored = []

    for account, videos in all_results.items():
        lines.append(f"## {account}")
        lines.append("")
        for v in videos:
            result = score_topic(v)
            all_scored.append((account, v, result))

            lines.append(f"### {v['title'][:50]}")
            lines.append(f"- 链接: {v['url']}")
            lines.append(f"- 点赞: {v.get('likes', 0):,}")
            lines.append(f"- **综合分: {result['composite']}/10**")
            lines.append("")
            lines.append("| 维度 | 分数 | 说明 |")
            lines.append("|------|------|------|")
            for k, info in RUBRIC.items():
                lines.append(f"| {info['name']} | {result['scores'][k]} | {info['desc']} |")
            lines.append("")

            lines.append("**柱子哥视角改写建议:**")
            lines.append(zhuzige_rewrite_suggestion(v, result))
            lines.append("")
            lines.append("---")
            lines.append("")

    # 排序推荐
    all_scored.sort(key=lambda x: x[2]["composite"], reverse=True)
    lines.insert(2, "## 今日推荐选题 TOP 3")
    lines.insert(3, "")
    for i, (account, v, result) in enumerate(all_scored[:3], 1):
        lines.insert(3 + i, f"{i}. **{v['title'][:40]}** ({account}) — 综合分 {result['composite']}")
    lines.insert(3 + len(all_scored[:3]) + 1, "")
    lines.insert(3 + len(all_scored[:3]) + 2, "---")
    lines.insert(3 + len(all_scored[:3]) + 2, "")

    return "\n".join(lines)


def main():
    print("=" * 50)
    print("  每日选题分析")
    print("=" * 50)

    data = load_today_data()
    if not data:
        print("[!] 今天没有带口播文案的数据，先运行: python3 scraper.py --transcribe")
        return

    total = sum(len(v) for v in data.values())
    print(f"\n读取到 {len(data)} 个博主，共 {total} 条口播文案")

    # 生成报告
    report = generate_report(data)

    # 保存报告
    today = datetime.now().strftime("%Y-%m-%d")
    report_path = OUTPUT_DIR / f"analysis-{today}.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\n[✓] 分析报告已保存: {report_path}")

    # 推送到飞书
    try:
        sys.path.insert(0, str(BASE_DIR))
        from feishu import FeishuBitable, FEISHU_BASE
        import httpx, time

        config = json.load(open(BASE_DIR / "config.json"))
        feishu = config.get("feishu", {})
        if feishu.get("app_id"):
            bitable = FeishuBitable(
                app_id=feishu["app_id"],
                app_secret=feishu["app_secret"],
                app_token=feishu["app_token"],
                table_id=feishu["table_id"],
            )
            # 推送 TOP 3 推荐
            all_scored = []
            for account, videos in data.items():
                for v in videos:
                    result = score_topic(v)
                    all_scored.append((account, v, result))
            all_scored.sort(key=lambda x: x[2]["composite"], reverse=True)

            records = []
            for account, v, result in all_scored[:5]:
                records.append({
                    "fields": {
                        "博主": account,
                        "标题": v.get("title", ""),
                        "文案": f"[推荐分 {result['composite']}] {zhuzige_rewrite_suggestion(v, result)}",
                        "链接": {"text": v.get("url", ""), "link": v.get("url", "")},
                        "发布日期": int(v.get("create_time", 0) * 1000) if v.get("create_time") else None,
                        "点赞": v.get("likes", 0),
                        "评论": v.get("comments", 0),
                        "分享": v.get("shares", 0),
                        "收藏": v.get("collects", 0),
                        "视频ID": v.get("id", ""),
                        "抓取日期": int(time.time() * 1000),
                    }
                })
            if records:
                bitable.batch_create_records(records)
                print(f"[✓] TOP 5 推荐已推送到飞书")
    except Exception as e:
        print(f"[!] 飞书推送失败: {e}")

    # 打印推荐
    print(f"\n{'=' * 50}")
    print("  今日推荐选题 TOP 3")
    print("=" * 50)
    all_scored = []
    for account, videos in data.items():
        for v in videos:
            result = score_topic(v)
            all_scored.append((account, v, result))
    all_scored.sort(key=lambda x: x[2]["composite"], reverse=True)
    for i, (account, v, result) in enumerate(all_scored[:3], 1):
        print(f"\n  {i}. {v['title'][:45]}")
        print(f"     博主: {account} | 综合分: {result['composite']}/10")
        print(f"     {zhuzige_rewrite_suggestion(v, result)}")


if __name__ == "__main__":
    main()
