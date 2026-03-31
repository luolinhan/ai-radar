# AI Global Intel Radar

全球AI重点人物与机构情报监控系统

## 功能

- 多源采集：RSS、GitHub、X/Twitter、网页/官网主页
- 中文翻译：自动翻译英文源内容
- 要点提取：结构化提取关键信息
- 影响分析：判断对研究、产品、市场的影响
- 特别提醒：飞书即时通知重要事件
- 质量控制：按信号评分、重复URL窗口、历史窗口过滤告警
- 控制台：Web界面查看和管理
- X 采集依赖 `snscrape` 和外网可访问性，默认作为可选能力启用
- X 采集优先走 `RSSHub` 订阅，RSSHub 不可用时回退到 `snscrape`
- 默认 compose 会同时启动一个本地 `RSSHub` 服务给 X 订阅使用

## 快速启动

```bash
# 本地开发
docker compose up

# API: http://localhost:8000
# 控制台: http://localhost:3000
```

## 目录结构

```
ai-radar/
  apps/
    api/           # FastAPI后端
    dashboard/     # Next.js前端
    worker-ai/     # AI分析worker
    worker-collector/  # 采集worker
  packages/
    shared-schema/ # 共享数据模型
  configs/
    watchlists/    # 监控名单
      source_targets.json  # 采集源配置（RSS/GitHub，可扩展到X/网页）
    prompts/       # Prompt版本
    dictionaries/  # 术语词典
  infra/
    docker/        # Docker配置
    scripts/       # 部署脚本
```

## 部署

服务器部署脚本见 `infra/scripts/deploy.sh`

## 推送质量与频次调优

- 采集源：`configs/watchlists/source_targets.json`
- 影响名单：`configs/watchlists/entities.json`
- 告警频次与质量（`.env`）：
  - `ALERT_SCAN_INTERVAL_MINUTES`
  - `ALERT_MAX_PER_RUN`
  - `ALERT_DEDUP_HOURS`
  - `ALERT_LOOKBACK_HOURS`
  - `ALERT_MIN_QUALITY_SCORE`
  - `ALERT_SIGNAL_KEYWORDS`
- 采集频次与范围（`.env`）：
  - `RSS_COLLECT_INTERVAL_MINUTES`
  - `GITHUB_COLLECT_INTERVAL_MINUTES`
  - `X_COLLECT_INTERVAL_MINUTES`
  - `WEB_COLLECT_INTERVAL_MINUTES`
  - `RSS_MAX_ITEMS_PER_FEED`
  - `GITHUB_MAX_RELEASES_PER_REPO`
  - `X_MAX_ITEMS_PER_ACCOUNT`
  - `WEB_MAX_ITEMS_PER_SITE`
  - `WATCH_ENTITIES_PATH`
  - `SOURCE_TARGETS_PATH`
