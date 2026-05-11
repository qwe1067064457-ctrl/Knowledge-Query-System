from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


LAW_CATEGORIES = [
    "government_administration",
    "agriculture",
    "general_regulatory",
    "defense_security",
    "employment_labor",
    "health",
    "finance",
    "transportation",
    "tax",
    "environment",
]


@dataclass(frozen=True)
class LawKnowledgeBuildSummary:
    source_dir: Path
    law_root: Path
    ecfr_root: Path
    copied: int
    category_counts: dict[str, int]
    manifest_path: Path


def count_markdown_files(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for item in path.iterdir() if item.is_file() and item.suffix.lower() == ".md")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def ensure_law_storage_structure(backend_dir: Path, group_id: str = "law") -> Path:
    storage_root = backend_dir / "storage" / "groups" / group_id
    shared_root = storage_root / "shared" / "domain_cases"
    cases_root = shared_root / "cases"
    cases_root.mkdir(parents=True, exist_ok=True)

    meta_path = storage_root / "meta.json"
    if not meta_path.exists():
        write_json(
            meta_path,
            {
                "id": group_id,
                "name": "Law Knowledge Base",
                "description": "Legal knowledge group for statutes, regulations, cases, and reusable legal analysis.",
                "status": "active",
                "default_agent_id": "default",
                "knowledge": {
                    "root": f"knowledge/groups/{group_id}",
                    "documents": f"knowledge/groups/{group_id}/documents",
                    "uploads": f"knowledge/groups/{group_id}/uploads",
                },
                "memory_policy": {},
                "metadata": {"created_by": "codex_law_kb_builder"},
                "created_at": datetime.now(UTC).isoformat(),
                "updated_at": datetime.now(UTC).isoformat(),
            },
        )

    index_path = shared_root / "index.json"
    if not index_path.exists():
        write_json(index_path, {"items": []})

    return storage_root


def copy_category_documents(source_dir: Path, ecfr_root: Path) -> dict[str, int]:
    category_counts: dict[str, int] = {}
    for category_dir in sorted(item for item in source_dir.iterdir() if item.is_dir()):
        category = category_dir.name
        target_dir = ecfr_root / category
        target_dir.mkdir(parents=True, exist_ok=True)

        count = 0
        for source_file in sorted(category_dir.iterdir()):
            if not source_file.is_file() or source_file.suffix.lower() != ".md":
                continue
            shutil.copy2(source_file, target_dir / source_file.name)
            count += 1
        category_counts[category] = count
    return category_counts


def build_manifest(
    *,
    source_dir: Path,
    law_root: Path,
    ecfr_root: Path,
    category_counts: dict[str, int],
) -> dict[str, Any]:
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "group_id": "law",
        "knowledge_root": str(law_root),
        "source": {
            "name": "Electronic Code of Federal Regulations",
            "short_name": "eCFR",
            "country": "United States",
            "document_type": "federal_regulations",
            "source_dir": str(source_dir),
            "target_dir": str(ecfr_root),
        },
        "categories": {
            category: {
                "count": count,
                "path": str(ecfr_root / category),
            }
            for category, count in sorted(category_counts.items())
        },
        "total_documents": sum(category_counts.values()),
    }


def render_law_readme() -> str:
    return """# Law 知识库

本目录是 `law` 组的知识库根目录，用于存放法律法规、司法解释、判例、案例资料等原始文献。

## 目录边界

- `documents/`：原始法律文献、法规条文、判例、指导案例等资料。
- `uploads/`：后续人工上传的临时资料或待整理资料。
- `storage/groups/law/shared/domain_cases/`：组共享的可复用案例卡片和分析结论，不存放大批量原始文档。

## 当前资料

- `documents/us/ecfr/`：美国 eCFR 联邦法规条文，已按主题分类为本地 Markdown 文件。
- `documents/cn/`：中国法律资料预留区，后续优先整理官方来源。
"""


def render_documents_index(category_counts: dict[str, int]) -> str:
    category_lines = "\n".join(f"- `{category}`：{count} 篇" for category, count in sorted(category_counts.items()))
    return f"""# Law Documents 索引

本索引用于帮助 agent 和人工先判断资料位置，再进入具体目录读取原文。

## 已归档资料

### 美国 / eCFR 联邦法规

路径：`documents/us/ecfr/`

类型：法规条文

数量：{sum(category_counts.values())} 篇

分类：

{category_lines}

## 待建设资料

- `documents/cn/laws/`：中国法律。
- `documents/cn/regulations/`：行政法规、部门规章、地方政府规章。
- `documents/cn/judicial_interpretations/`：司法解释。
- `documents/cn/guiding_cases/`：指导性案例。
- `documents/cn/judgments/`：裁判文书或案例文书，需确认来源和访问合规性。

## 和 domain_case 的区别

- `documents/` 保存原始文献。
- `domain_case` 保存从任务中沉淀出的可复用案例卡片、分析框架和结论。
- 不把大批量原始法规或判决全文写入 `domain_case`。
"""


def render_ecfr_index(category_counts: dict[str, int]) -> str:
    category_lines = "\n".join(f"- `{category}/`：{count} 篇" for category, count in sorted(category_counts.items()))
    return f"""# eCFR 联邦法规资料

来源：Electronic Code of Federal Regulations

国家/地区：United States

文献类型：federal regulations

本目录保存按 section 拆分后的 eCFR 法规条文，每篇为一个 Markdown 文件。

## 分类

{category_lines}

## 使用建议

- 查询美国联邦行政法规、监管义务、定义条款时优先检索本目录。
- 文件 front matter 中保留 `source_url`、`source_id`、`date_filed`、`category` 等字段。
- 本目录是原始法规文本，不等同于案例分析或法律意见。
"""


def render_cn_index() -> str:
    return """# 中国法律资料预留区

本目录用于后续整理中国法律文献，优先使用公开官方来源。

建议子目录：

- `laws/`：法律。
- `regulations/`：行政法规、部门规章、地方政府规章。
- `judicial_interpretations/`：司法解释。
- `guiding_cases/`：指导性案例。
- `judgments/`：裁判文书或案例文书，需确认来源、授权和访问限制。
"""


def build_law_knowledge_base(
    *,
    backend_dir: Path,
    source_dir: Path,
    group_id: str = "law",
) -> LawKnowledgeBuildSummary:
    if not source_dir.exists():
        raise FileNotFoundError(f"Source directory does not exist: {source_dir}")

    ensure_law_storage_structure(backend_dir, group_id=group_id)

    law_root = backend_dir / "knowledge" / "groups" / group_id
    documents_root = law_root / "documents"
    ecfr_root = documents_root / "us" / "ecfr"
    cn_root = documents_root / "cn"
    uploads_root = law_root / "uploads"

    ecfr_root.mkdir(parents=True, exist_ok=True)
    cn_root.mkdir(parents=True, exist_ok=True)
    uploads_root.mkdir(parents=True, exist_ok=True)

    category_counts = copy_category_documents(source_dir, ecfr_root)
    manifest = build_manifest(
        source_dir=source_dir,
        law_root=law_root,
        ecfr_root=ecfr_root,
        category_counts=category_counts,
    )

    write_text(law_root / "README.md", render_law_readme())
    write_text(documents_root / "index.md", render_documents_index(category_counts))
    write_text(ecfr_root / "index.md", render_ecfr_index(category_counts))
    write_text(cn_root / "index.md", render_cn_index())

    manifest_path = documents_root / "manifest.json"
    write_json(manifest_path, manifest)

    return LawKnowledgeBuildSummary(
        source_dir=source_dir,
        law_root=law_root,
        ecfr_root=ecfr_root,
        copied=sum(category_counts.values()),
        category_counts=category_counts,
        manifest_path=manifest_path,
    )
