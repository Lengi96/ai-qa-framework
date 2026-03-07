"""Load and validate requirements, scenarios, and release gates."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


SUPPORTED_PROVIDERS = {"anthropic", "openai", "google"}
PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Requirement:
    id: str
    title: str
    feature: str
    business_goal: str
    priority: str
    risk: str
    source: str
    acceptance_criteria: tuple[str, ...]
    linked_scenarios: tuple[str, ...]
    release_gate: str


@dataclass(frozen=True)
class Scenario:
    id: str
    category: str
    objective: str
    requirement_ids: tuple[str, ...]
    system_prompt: str | None = None
    user_prompt: str = ""
    context: str | None = None
    expected_signals: tuple[str, ...] = ()
    forbidden_signals: tuple[str, ...] = ()
    severity: str = "medium"
    tags: tuple[str, ...] = ()
    provider_scope: tuple[str, ...] = ()
    max_tokens: int = 500
    expected_match: str = "all"
    prompt_variants: tuple[str, ...] = ()
    repeat_count: int = 1
    max_latency_seconds: float | None = None
    max_average_latency_seconds: float | None = None
    max_output_tokens: int | None = None
    min_response_length: int = 0

    @property
    def prompts(self) -> tuple[str, ...]:
        if self.prompt_variants:
            return self.prompt_variants
        return (self.user_prompt,)


@dataclass(frozen=True)
class GateConfig:
    overall_pass_rate: float = 90.0
    critical_requirements_pass_rate: float = 100.0
    high_risk_coverage: float = 95.0
    zero_failed_critical_requirements: bool = True


def _require_mapping(item: Any, context: str) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise ValueError(f"{context} must be a mapping")
    return item


def _require_non_empty_string(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip()


def _optional_string(value: Any, field_name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string or null")
    stripped = value.strip()
    return stripped or None


def _string_list(value: Any, field_name: str, *, allow_empty: bool = True) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list of strings")
    items = tuple(_require_non_empty_string(item, field_name) for item in value)
    if not allow_empty and not items:
        raise ValueError(f"{field_name} must not be empty")
    return items


def _float_or_none(value: Any, field_name: str) -> float | None:
    if value is None:
        return None
    if not isinstance(value, (int, float)):
        raise ValueError(f"{field_name} must be numeric")
    return float(value)


def _int_or_default(value: Any, field_name: str, default: int) -> int:
    if value is None:
        return default
    if not isinstance(value, int):
        raise ValueError(f"{field_name} must be an integer")
    return value


def _load_yaml_file(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return _require_mapping(data, str(path))


def _iter_yaml_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    return sorted(path.glob("*.yaml"))


@lru_cache(maxsize=8)
def load_requirements(path: str | Path | None = None) -> tuple[Requirement, ...]:
    source = Path(path) if path else PROJECT_ROOT / "requirements"
    requirements: list[Requirement] = []

    for file_path in _iter_yaml_files(source):
        data = _load_yaml_file(file_path)
        for index, raw in enumerate(data.get("requirements", []), start=1):
            item = _require_mapping(raw, f"{file_path} requirement #{index}")
            requirements.append(
                Requirement(
                    id=_require_non_empty_string(item.get("id"), "requirement.id"),
                    title=_require_non_empty_string(item.get("title"), "requirement.title"),
                    feature=_require_non_empty_string(item.get("feature"), "requirement.feature"),
                    business_goal=_require_non_empty_string(
                        item.get("business_goal"), "requirement.business_goal"
                    ),
                    priority=_require_non_empty_string(item.get("priority"), "requirement.priority").lower(),
                    risk=_require_non_empty_string(item.get("risk"), "requirement.risk").lower(),
                    source=_require_non_empty_string(item.get("source"), "requirement.source"),
                    acceptance_criteria=_string_list(
                        item.get("acceptance_criteria"),
                        "requirement.acceptance_criteria",
                        allow_empty=False,
                    ),
                    linked_scenarios=_string_list(
                        item.get("linked_scenarios"),
                        "requirement.linked_scenarios",
                        allow_empty=False,
                    ),
                    release_gate=_require_non_empty_string(
                        item.get("release_gate"), "requirement.release_gate"
                    ).lower(),
                )
            )

    if not requirements:
        raise ValueError(f"No requirements found in {source}")

    _ensure_unique_ids([requirement.id for requirement in requirements], "requirement")
    return tuple(requirements)


@lru_cache(maxsize=8)
def load_scenarios(path: str | Path | None = None) -> tuple[Scenario, ...]:
    source = Path(path) if path else PROJECT_ROOT / "scenarios"
    scenarios: list[Scenario] = []

    for file_path in _iter_yaml_files(source):
        data = _load_yaml_file(file_path)
        for index, raw in enumerate(data.get("scenarios", []), start=1):
            item = _require_mapping(raw, f"{file_path} scenario #{index}")
            provider_scope = tuple(
                provider.lower()
                for provider in _string_list(item.get("provider_scope"), "scenario.provider_scope")
            )
            invalid_providers = set(provider_scope) - SUPPORTED_PROVIDERS
            if invalid_providers:
                invalid = ", ".join(sorted(invalid_providers))
                raise ValueError(f"scenario.provider_scope contains unsupported providers: {invalid}")

            expected_match = (item.get("expected_match") or "all").lower()
            if expected_match not in {"all", "any"}:
                raise ValueError("scenario.expected_match must be 'all' or 'any'")

            scenarios.append(
                Scenario(
                    id=_require_non_empty_string(item.get("id"), "scenario.id"),
                    category=_require_non_empty_string(item.get("category"), "scenario.category").lower(),
                    objective=_require_non_empty_string(item.get("objective"), "scenario.objective"),
                    requirement_ids=_string_list(
                        item.get("requirement_ids"), "scenario.requirement_ids", allow_empty=False
                    ),
                    system_prompt=_optional_string(item.get("system_prompt"), "scenario.system_prompt"),
                    user_prompt=_require_non_empty_string(item.get("user_prompt"), "scenario.user_prompt"),
                    context=_optional_string(item.get("context"), "scenario.context"),
                    expected_signals=_string_list(item.get("expected_signals"), "scenario.expected_signals"),
                    forbidden_signals=_string_list(
                        item.get("forbidden_signals"), "scenario.forbidden_signals"
                    ),
                    severity=_require_non_empty_string(item.get("severity"), "scenario.severity").lower(),
                    tags=_string_list(item.get("tags"), "scenario.tags"),
                    provider_scope=provider_scope,
                    max_tokens=_int_or_default(item.get("max_tokens"), "scenario.max_tokens", 500),
                    expected_match=expected_match,
                    prompt_variants=_string_list(item.get("prompt_variants"), "scenario.prompt_variants"),
                    repeat_count=_int_or_default(item.get("repeat_count"), "scenario.repeat_count", 1),
                    max_latency_seconds=_float_or_none(
                        item.get("max_latency_seconds"), "scenario.max_latency_seconds"
                    ),
                    max_average_latency_seconds=_float_or_none(
                        item.get("max_average_latency_seconds"),
                        "scenario.max_average_latency_seconds",
                    ),
                    max_output_tokens=_int_or_default(
                        item.get("max_output_tokens"), "scenario.max_output_tokens", 0
                    )
                    or None,
                    min_response_length=_int_or_default(
                        item.get("min_response_length"), "scenario.min_response_length", 0
                    ),
                )
            )

    if not scenarios:
        raise ValueError(f"No scenarios found in {source}")

    _ensure_unique_ids([scenario.id for scenario in scenarios], "scenario")
    return tuple(scenarios)


@lru_cache(maxsize=8)
def load_quality_gates(path: str | Path | None = None) -> GateConfig:
    source = Path(path) if path else PROJECT_ROOT / "config" / "quality_gates.yaml"
    data = _load_yaml_file(source)
    gates = _require_mapping(data.get("quality_gates", {}), "quality_gates")

    return GateConfig(
        overall_pass_rate=float(gates.get("overall_pass_rate", 90)),
        critical_requirements_pass_rate=float(gates.get("critical_requirements_pass_rate", 100)),
        high_risk_coverage=float(gates.get("high_risk_coverage", 95)),
        zero_failed_critical_requirements=bool(gates.get("zero_failed_critical_requirements", True)),
    )


def _ensure_unique_ids(ids: list[str], label: str) -> None:
    duplicates = sorted({item for item in ids if ids.count(item) > 1})
    if duplicates:
        raise ValueError(f"Duplicate {label} ids found: {', '.join(duplicates)}")


def validate_traceability_links(
    requirements: tuple[Requirement, ...],
    scenarios: tuple[Scenario, ...],
) -> None:
    requirement_ids = {requirement.id for requirement in requirements}
    scenario_ids = {scenario.id for scenario in scenarios}

    missing_scenarios = sorted(
        {
            linked_scenario
            for requirement in requirements
            for linked_scenario in requirement.linked_scenarios
            if linked_scenario not in scenario_ids
        }
    )
    if missing_scenarios:
        raise ValueError(
            "Requirements reference missing scenarios: " + ", ".join(missing_scenarios)
        )

    missing_requirements = sorted(
        {
            requirement_id
            for scenario in scenarios
            for requirement_id in scenario.requirement_ids
            if requirement_id not in requirement_ids
        }
    )
    if missing_requirements:
        raise ValueError(
            "Scenarios reference missing requirements: " + ", ".join(missing_requirements)
        )

    for requirement in requirements:
        if requirement.release_gate == "critical" and not requirement.linked_scenarios:
            raise ValueError(f"Critical requirement {requirement.id} has no linked scenarios")


def load_quality_specs(
    *,
    requirements_path: str | Path | None = None,
    scenarios_path: str | Path | None = None,
    gates_path: str | Path | None = None,
) -> tuple[tuple[Requirement, ...], tuple[Scenario, ...], GateConfig]:
    requirements = load_requirements(requirements_path)
    scenarios = load_scenarios(scenarios_path)
    gates = load_quality_gates(gates_path)
    validate_traceability_links(requirements, scenarios)
    return requirements, scenarios, gates
