from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


class CatalogValidationError(Exception):
    """Raised when the catalog JSON does not match the contract."""


@dataclass(frozen=True)
class CatalogModule:
    id: str
    title: str
    description: str
    skill_ids: list[str]
    domain: str
    level: str
    duration_min: int
    prerequisites: list[str]


class CourseCatalogService:
    def __init__(self, modules: list[CatalogModule]) -> None:
        self.modules = modules
        self.modules_by_id = {m.id: m for m in modules}
        self.modules_by_skill: dict[str, list[CatalogModule]] = {}
        for module in modules:
            for skill_id in module.skill_ids:
                self.modules_by_skill.setdefault(skill_id, []).append(module)

    @classmethod
    def from_env(cls) -> "CourseCatalogService":
        configured = os.getenv("CATALOG_PATH", "").strip()
        candidate_paths = [
            configured,
            "data/catalog/modules.json",
            "../data/catalog/modules.json",
            "/workspace/data/catalog/modules.json",
        ]

        for candidate in candidate_paths:
            if not candidate:
                continue
            path = Path(candidate)
            if path.exists():
                return cls.from_json(path)

        raise CatalogValidationError(
            "Catalog file not found. Set CATALOG_PATH or create data/catalog/modules.json"
        )

    @classmethod
    def from_json(cls, file_path: Path) -> "CourseCatalogService":
        with file_path.open("r", encoding="utf-8") as f:
            raw = json.load(f)

        if not isinstance(raw, list):
            raise CatalogValidationError("Catalog JSON must be a list of module objects")

        modules = [cls._validate_module(item, idx) for idx, item in enumerate(raw)]
        cls._validate_references(modules)
        return cls(modules)

    @staticmethod
    def _validate_module(raw: dict, index: int) -> CatalogModule:
        if not isinstance(raw, dict):
            raise CatalogValidationError(f"Module at index {index} is not an object")

        required = ["id", "title", "skill_ids", "domain", "level", "duration_min", "prerequisites"]
        for key in required:
            if key not in raw:
                raise CatalogValidationError(f"Module at index {index} missing required key: {key}")

        module_id = raw["id"]
        title = raw["title"]
        description = raw.get("description", "")
        skill_ids = raw["skill_ids"]
        domain = raw["domain"]
        level = raw["level"]
        duration_min = raw["duration_min"]
        prerequisites = raw["prerequisites"]

        if not isinstance(module_id, str) or not module_id.strip():
            raise CatalogValidationError(f"Module at index {index} has invalid id")
        if not isinstance(title, str) or not title.strip():
            raise CatalogValidationError(f"Module {module_id} has invalid title")
        if not isinstance(description, str):
            raise CatalogValidationError(f"Module {module_id} has invalid description")
        if not isinstance(skill_ids, list) or not all(isinstance(v, str) and v.strip() for v in skill_ids):
            raise CatalogValidationError(f"Module {module_id} has invalid skill_ids")
        if not isinstance(domain, str) or not domain.strip():
            raise CatalogValidationError(f"Module {module_id} has invalid domain")
        if not isinstance(level, str) or not level.strip():
            raise CatalogValidationError(f"Module {module_id} has invalid level")
        if not isinstance(duration_min, int) or duration_min <= 0:
            raise CatalogValidationError(f"Module {module_id} has invalid duration_min")
        if not isinstance(prerequisites, list) or not all(
            isinstance(v, str) and v.strip() for v in prerequisites
        ):
            raise CatalogValidationError(f"Module {module_id} has invalid prerequisites")

        return CatalogModule(
            id=module_id,
            title=title,
            description=description,
            skill_ids=skill_ids,
            domain=domain,
            level=level,
            duration_min=duration_min,
            prerequisites=prerequisites,
        )

    @staticmethod
    def _validate_references(modules: list[CatalogModule]) -> None:
        ids = {m.id for m in modules}
        if len(ids) != len(modules):
            raise CatalogValidationError("Catalog contains duplicate module ids")

        for module in modules:
            for prereq in module.prerequisites:
                if prereq not in ids:
                    raise CatalogValidationError(
                        f"Module {module.id} references unknown prerequisite: {prereq}"
                    )

    def pick_modules_for_skills(self, skill_ids: set[str], limit: int = 10) -> list[CatalogModule]:
        if not skill_ids:
            return []

        matched: dict[str, CatalogModule] = {}
        for skill_id in skill_ids:
            for module in self.modules_by_skill.get(skill_id, []):
                matched[module.id] = module

        if not matched:
            return []

        level_rank = {"Beginner": 0, "Intermediate": 1, "Advanced": 2}

        ranked = sorted(
            matched.values(),
            key=lambda m: (
                -len(skill_ids.intersection(set(m.skill_ids))),
                level_rank.get(m.level, 99),
                m.duration_min,
                m.title.lower(),
            ),
        )

        required: dict[str, CatalogModule] = {}
        for module in ranked[:limit]:
            self._collect_prerequisites(module.id, required)
            required[module.id] = module

        return sorted(required.values(), key=lambda m: (level_rank.get(m.level, 99), m.title.lower()))

    def _collect_prerequisites(self, module_id: str, selected: dict[str, CatalogModule]) -> None:
        module = self.modules_by_id[module_id]
        for prereq_id in module.prerequisites:
            if prereq_id in selected:
                continue
            prereq = self.modules_by_id[prereq_id]
            selected[prereq_id] = prereq
            self._collect_prerequisites(prereq_id, selected)
