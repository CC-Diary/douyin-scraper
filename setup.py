#!/usr/bin/env python3
"""
一键配置助手
配置飞书、对标账号、自动运行
"""

import json
import sys
from pathlib import Path

CONFIG_FILE = Path(__file__).parent / "config.json"


def load_config():
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)


def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def setup_feishu():
    print("=" * 50)
    print("  第一步: 配置飞书多维表格")
    print("=" * 50)
    print()
    print("获取方式:")
    print()
    print("1. 打开 https://open.feishu.cn/app")
    print("2. 创建「企业自建应用」")
    print("3. 在「凭证与基础信息」中获取 App ID 和 App Secret")
    print("4. 在「权限管理」中添加:")
    print("   - bitable:app (多维表格)")
    print("   - bitable:app:readonly (可选)")
    print("5. 发布应用并审批通过")
    print()
    print("6. 打开飞书多维表格，新建一个表格")
    print("7. 表格列设置:")
    print("   - 博主 (文本)")
    print("   - 标题 (文本)")
    print("   - 文案 (文本)")
    print("   - 链接 (链接)")
    print("   - 发布日期 (日期)")
    print("   - 点赞 (数字)")
    print("   - 评论 (数字)")
    print("   - 分享 (数字)")
    print("   - 收藏 (数字)")
    print("   - 视频ID (文本)")
    print("   - 抓取日期 (日期)")
    print()
    print("8. 从表格 URL 中获取 app_token 和 table_id:")
    print("   URL 格式: https://xxx.feishu.cn/base/APPTokenXXX?table=tblYYY")
    print("   app_token = APPTokenXXX")
    print("   table_id = tblYYY")
    print()

    config = load_config()
    feishu = config.get("feishu", {})

    app_id = input(f"App ID [{feishu.get('app_id', '')}]: ").strip() or feishu.get("app_id", "")
    app_secret = input(f"App Secret [{feishu.get('app_secret', '')[:8]}...]: ").strip()
    if app_secret and "..." not in app_secret:
        feishu["app_secret"] = app_secret
    elif not app_secret:
        feishu["app_secret"] = feishu.get("app_secret", "")

    app_token = input(f"Bitable App Token [{feishu.get('app_token', '')}]: ").strip() or feishu.get("app_token", "")
    table_id = input(f"Table ID [{feishu.get('table_id', '')}]: ").strip() or feishu.get("table_id", "")

    feishu["app_id"] = app_id
    feishu["app_token"] = app_token
    feishu["table_id"] = table_id
    config["feishu"] = feishu

    save_config(config)

    if app_id and app_secret and app_token and table_id:
        print("\n[✓] 飞书配置完成!")
        # 测试连接
        try:
            from feishu import FeishuBitable
            bitable = FeishuBitable(app_id, feishu["app_secret"], app_token, table_id)
            bitable.test_connection()
        except Exception as e:
            print(f"  [!] 连接测试失败: {e}")
    else:
        print("\n[!] 部分字段未填写，飞书推送暂不可用")

    return config


def setup_accounts(config):
    print("\n" + "=" * 50)
    print("  第二步: 配置对标账号")
    print("=" * 50)
    print()
    print("输入抖音博主主页链接")
    print("格式: https://www.douyin.com/user/SEC_UID")
    print("输入空行结束")
    print()

    accounts = config.get("accounts", [])

    if accounts and accounts[0].get("douyin_url", "").startswith("https://www.douyin.com/user/MS4w"):
        accounts = []
        print("(已清除示例账号)")
        print()

    if accounts:
        print("当前已配置的账号:")
        for i, acc in enumerate(accounts, 1):
            print(f"  {i}. {acc['name']} - {acc['douyin_url']}")
        print()

    while True:
        name = input("博主名称 (空行结束): ").strip()
        if not name:
            break

        url = input("主页链接: ").strip()
        if not url:
            print("[!] 链接不能为空")
            continue

        if "douyin.com/user/" not in url:
            print("[!] 链接格式不正确")
            continue

        note = input("备注 (可选): ").strip()

        accounts.append({
            "name": name,
            "douyin_url": url,
            "note": note,
        })
        print(f"[✓] 已添加: {name}\n")

    config["accounts"] = accounts
    save_config(config)
    print(f"[✓] 共配置 {len(accounts)} 个账号")


def setup_cookie(config):
    print("\n" + "=" * 50)
    print("  第三步: 配置抖音 Cookie")
    print("=" * 50)
    print()
    print("Cookie 可以提高抓取成功率（可选但推荐）")
    print()
    print("获取步骤:")
    print("1. Chrome 打开 douyin.com 并登录（建议用小号）")
    print("2. F12 → Network → 刷新页面")
    print("3. 点任意请求 → Headers → 复制 Cookie")
    print()

    cookie = input("Cookie (直接回车跳过): ").strip()
    if cookie:
        config["cookie"] = cookie
        save_config(config)
        print("[✓] Cookie 已保存")
    else:
        print("[*] 跳过 Cookie 配置")


def setup_auto_run():
    print("\n" + "=" * 50)
    print("  第四步: 设置自动运行")
    print("=" * 50)
    print()
    print("电脑开机后，每天定时自动抓取并推送到飞书")
    print()

    time_str = input("每天几点运行? (格式 HH:MM, 默认 09:00): ").strip()
    if not time_str:
        time_str = "09:00"

    parts = time_str.split(":")
    hour = int(parts[0])
    minute = int(parts[1]) if len(parts) > 1 else 0

    import subprocess
    script_dir = Path(__file__).parent
    result = subprocess.run(
        ["bash", str(script_dir / "setup-auto.sh"), str(hour), str(minute)],
        capture_output=True, text=True
    )
    print(result.stdout)
    if result.stderr:
        print(result.stderr)


def main():
    print()
    print("╔══════════════════════════════════════════╗")
    print("║     抖音博主抓取工具 - 一键配置          ║")
    print("╚══════════════════════════════════════════╝")
    print()

    config = load_config()

    setup_feishu()
    setup_accounts(config)
    setup_cookie(config)
    setup_auto_run()

    print("\n" + "=" * 50)
    print("  全部配置完成!")
    print("=" * 50)
    print()
    print("现在开始:")
    print("  1. 手动测试: python3 scraper.py")
    print("  2. 之后每天自动运行，结果推送到飞书")
    print()
    print("管理:")
    print("  查看日志: cat logs/$(date +%Y-%m-%d).log")
    print("  手动触发: python3 scraper.py")
    print("  修改配置: python3 setup.py")
    print("  停用自动: launchctl unload ~/Library/LaunchAgents/com.douyin-scraper.plist")


if __name__ == "__main__":
    main()
