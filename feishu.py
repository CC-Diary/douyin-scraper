#!/usr/bin/env python3
"""
飞书多维表格对接模块
将抓取的抖音内容推送到飞书 Bitable
"""

import json
import time
import httpx

FEISHU_BASE = "https://open.feishu.cn/open-apis"


class FeishuBitable:
    def __init__(self, app_id: str, app_secret: str, app_token: str, table_id: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self.app_token = app_token
        self.table_id = table_id
        self._token = None
        self._token_expire = 0

    def _get_tenant_token(self) -> str:
        """获取 tenant_access_token"""
        if self._token and time.time() < self._token_expire:
            return self._token

        resp = httpx.post(
            f"{FEISHU_BASE}/auth/v3/tenant_access_token/internal",
            json={"app_id": self.app_id, "app_secret": self.app_secret},
        )
        data = resp.json()
        if data.get("code") != 0:
            raise Exception(f"获取飞书 Token 失败: {data}")

        self._token = data["tenant_access_token"]
        self._token_expire = time.time() + data.get("expire", 7200) - 300
        return self._token

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._get_tenant_token()}",
            "Content-Type": "application/json",
        }

    def batch_create_records(self, records: list[dict]) -> dict:
        """批量写入记录到多维表格"""
        url = f"{FEISHU_BASE}/bitable/v1/apps/{self.app_token}/tables/{self.table_id}/records/batch_create"

        # 飞书 API 限制每次最多 500 条
        results = []
        for i in range(0, len(records), 500):
            batch = records[i:i + 500]
            resp = httpx.post(url, headers=self._headers(), json={"records": batch})
            data = resp.json()
            if data.get("code") != 0:
                print(f"  [!] 写入飞书失败: {data.get('msg')}")
            else:
                results.append(data)
            time.sleep(0.5)

        return results

    def test_connection(self) -> bool:
        """测试飞书连接"""
        try:
            token = self._get_tenant_token()
            print(f"  [✓] 飞书 Token 获取成功")
            return True
        except Exception as e:
            print(f"  [!] 飞书连接失败: {e}")
            return False


def video_to_record(video: dict, account_name: str) -> dict:
    """将视频数据转换为飞书多维表格记录格式"""
    create_time = video.get("create_time", 0)
    publish_ts = int(create_time * 1000) if create_time else None
    fetch_ts = int(time.time() * 1000)

    return {
        "fields": {
            "博主": account_name,
            "标题": video.get("title", ""),
            "文案": video.get("transcript") or video.get("description", ""),
            "链接": {"text": video.get("url", ""), "link": video.get("url", "")},
            "发布日期": publish_ts,
            "点赞": video.get("likes", 0),
            "评论": video.get("comments", 0),
            "分享": video.get("shares", 0),
            "收藏": video.get("collects", 0),
            "视频ID": video.get("id", ""),
            "抓取日期": fetch_ts,
        }
    }


def clean_old_records(config: dict, days: int = 3):
    """删除飞书中超过指定天数的旧记录"""
    feishu = config.get("feishu", {})
    if not feishu.get("app_id"):
        return

    bitable = FeishuBitable(
        app_id=feishu["app_id"],
        app_secret=feishu["app_secret"],
        app_token=feishu["app_token"],
        table_id=feishu["table_id"],
    )

    cutoff = int((time.time() - days * 86400) * 1000)

    try:
        headers = bitable._headers()
        all_ids = []
        page_token = ""
        for _ in range(20):
            params = {"page_size": 500}
            if page_token:
                params["page_token"] = page_token
            resp = httpx.get(
                f"{FEISHU_BASE}/bitable/v1/apps/{bitable.app_token}/tables/{bitable.table_id}/records",
                headers=headers, params=params,
            )
            data = resp.json()
            for r in data.get("data", {}).get("items", []):
                fetch_date = r.get("fields", {}).get("抓取日期", 0)
                if fetch_date and fetch_date < cutoff:
                    all_ids.append(r["record_id"])
            page_token = data.get("data", {}).get("page_token", "")
            if not data.get("data", {}).get("has_more"):
                break

        if all_ids:
            for i in range(0, len(all_ids), 500):
                batch = all_ids[i:i + 500]
                httpx.post(
                    f"{FEISHU_BASE}/bitable/v1/apps/{bitable.app_token}/tables/{bitable.table_id}/records/batch_delete",
                    headers=headers, json={"records": batch},
                )
            print(f"  [✓] 已清理 {len(all_ids)} 条{days}天前的旧记录")
    except Exception as e:
        print(f"  [!] 清理旧记录失败: {e}")


def push_to_feishu(config: dict, account_name: str, videos: list[dict]):
    """将视频列表推送到飞书多维表格"""
    feishu = config.get("feishu", {})
    if not feishu.get("app_id"):
        print("  [!] 飞书未配置，跳过推送")
        return

    bitable = FeishuBitable(
        app_id=feishu["app_id"],
        app_secret=feishu["app_secret"],
        app_token=feishu["app_token"],
        table_id=feishu["table_id"],
    )

    records = [video_to_record(v, account_name) for v in videos]
    if records:
        result = bitable.batch_create_records(records)
        print(f"  [✓] 已推送 {len(records)} 条到飞书多维表格")
        return result
