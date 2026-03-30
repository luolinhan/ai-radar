# AI Global Intel Radar

全球AI重点人物与机构情报监控系统

## 功能

- 多源采集：RSS、GitHub、X/Twitter、arXiv、Hacker News
- 中文翻译：自动翻译英文源内容
- 要点提取：结构化提取关键信息
- 影响分析：判断对研究、产品、市场的影响
- 特别提醒：飞书即时通知重要事件
- 控制台：Web界面查看和管理

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
    source-connectors/  # 采集器封装
  configs/
    watchlists/    # 监控名单
    prompts/       # Prompt版本
    dictionaries/  # 术语词典
  infra/
    docker/        # Docker配置
    scripts/       # 部署脚本
```

## 部署

服务器部署脚本见 `infra/scripts/deploy.sh`