#!/usr/bin/env python3
"""
将 configs/watchlists/entities.json 同步到 watch_entities 表。

默认只补入数据库中不存在的实体，不覆盖已有记录。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


HERE = Path(__file__).resolve()
ROOT = HERE.parents[2]
if not (ROOT / "configs" / "watchlists" / "entities.json").exists():
    ROOT = HERE.parents[1]

API_DIR = ROOT / "apps" / "api"
if (API_DIR / "database.py").exists():
    sys.path.insert(0, str(API_DIR))
else:
    sys.path.insert(0, str(ROOT))

from database import SessionLocal  # noqa: E402
from models import WatchEntity  # noqa: E402


def load_entities() -> list[dict]:
    path = ROOT / "configs" / "watchlists" / "entities.json"
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    db = SessionLocal()
    try:
        entities = load_entities()
        existing = {
            (row.entity_type, row.name_en)
            for row in db.query(WatchEntity.entity_type, WatchEntity.name_en).all()
        }

        added = 0
        for entity in entities:
            key = (entity.get("entity_type"), entity.get("name_en"))
            if key in existing:
                continue

            db.add(
                WatchEntity(
                    id=entity["id"],
                    entity_type=entity.get("entity_type"),
                    name_en=entity.get("name_en"),
                    name_zh=entity.get("name_zh"),
                    aliases=entity.get("aliases", []),
                    x_handle=entity.get("x_handle"),
                    github_handle=entity.get("github_handle"),
                    website_url=entity.get("website_url"),
                    organization=entity.get("organization"),
                    priority=entity.get("priority", "P2"),
                    keywords=entity.get("keywords", []),
                    is_active=entity.get("is_active", "true"),
                )
            )
            existing.add(key)
            added += 1

        db.commit()
        print(f"added={added}")
        return 0
    except Exception as exc:
        db.rollback()
        print(f"error: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
