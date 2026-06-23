# 抖音博主内容抓取工具

自动抓取对标账号的视频标题、**口播文案**（Whisper语音转录）、互动数据，推送到飞书多维表格，辅助每日选题。

## 功能

- 抓取对标账号的全部视频列表
- Whisper 本地转录口播文案（不调任何付费 API）
- 自动推送到飞书多维表格
- macOS 定时任务，开机自动运行

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

首次运行 `--transcribe` 时会自动下载 Whisper tiny 模型（72MB）。

### 2. 配置

复制配置模板并填写：

```bash
cp config.example.json config.json
```

需要配置：
- **抖音 Cookie** — 从浏览器导出（详见下方）
- **对标博主链接** — 抖音主页 URL
- **飞书应用** — 可选，用于推送数据

### 3. 运行

```bash
# 快速抓取元数据（几秒）
python scraper.py

# 抓取 + 口播文案转录（每个视频约10-30秒，只转录最近2天）
python scraper.py --transcribe
```

### 4. 定时自动运行（macOS）

```bash
bash setup-auto.sh 9 0   # 每天早上9点
```

## 获取抖音 Cookie

1. 用 Chrome/Edge 打开 https://www.douyin.com/ 并登录（**建议用小号**）
2. 安装 [Cookie-Editor](https://microsoftedge.microsoft.com/addons/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm) 插件
3. 点插件图标 → **Export** → **Copy**
4. 粘贴到 `config.json` 的 `cookie` 字段

> Cookie 有效期约 30 天，过期后重新获取即可。

## 飞书多维表格配置（可选）

1. 打开 https://open.feishu.cn/app 创建企业自建应用
2. 获取 App ID 和 App Secret
3. 在权限管理中添加 `bitable:app` 权限
4. 发布应用并审批通过
5. 创建多维表格，从 URL 中获取 app_token 和 table_id
6. 填入 `config.json` 的 `feishu` 字段

### 表格列格式

| 列名 | 类型 |
|------|------|
| 博主 | 文本 |
| 标题 | 文本 |
| 文案 | 文本（口播转录内容） |
| 链接 | 链接 |
| 发布日期 | 日期 |
| 点赞 | 数字 |
| 评论 | 数字 |
| 分享 | 数字 |
| 收藏 | 数字 |
| 视频ID | 文本 |
| 抓取日期 | 日期 |

## 项目结构

```
douyin-scraper/
├── scraper.py          # 主抓取脚本
├── feishu.py           # 飞书多维表格对接
├── setup.py            # 一键配置助手
├── setup-auto.sh       # macOS 定时任务设置
├── config.example.json # 配置模板
├── requirements.txt    # Python 依赖
├── .gitignore
└── README.md
```

## 输出

- **飞书多维表格** — 博主、标题、口播文案、链接、互动数据
- **本地文件** — `output/` 目录下按博主+日期保存 Markdown + JSON
- **日志** — `logs/` 目录下按日期记录

## 注意事项

- 抖音反爬较强，Cookie 是关键
- 建议用小号登录获取 Cookie
- Whisper tiny 模型中文识别有一定误差，可修改代码中的 `whisper.load_model('tiny')` 换成 `'base'` 或 `'small'`（需下载更大模型）
- 内容仅限个人学习使用

## License

MIT
