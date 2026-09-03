"""Suggest next-service due dates/km from the maintenance guidelines catalog."""

from __future__ import annotations

import calendar
from datetime import date
from typing import NamedTuple

from app.data.guidelines import load_guidelines

# Map common service-form tags → guideline task names (case-insensitive keys).
_TAG_TO_TASK: dict[str, str] = {
    "engine oil": "Engine oil change",
    "oil filter": "Oil filter replacement",
    "air filter": "Air filter cleaning",
    "spark plug": "Spark plug inspection",
    "chain lubrication": "Chain lubrication",
    "chain lube": "Chain lubrication",
    "chain sprocket": "Chain and sprocket replacement",
    "brake fluid": "Brake fluid change",
    "brake pads": "Brake pad inspection",
    "tyre change": "Tyre replacement",
    "tire change": "Tyre replacement",
}


class NextDueSuggestion(NamedTuple):
    next_service_date: date | None
    next_service_odometer: int | None
    matched_tasks: list[str]


def _normalize(label: str) -> str:
    return " ".join(label.strip().lower().split())


def _add_months(start: date, months: int) -> date:
    year = start.year + (start.month - 1 + months) // 12
    month = (start.month - 1 + months) % 12 + 1
    day = min(start.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _resolve_task_name(service_tag: str, task_by_norm: dict[str, str]) -> str | None:
    key = _normalize(service_tag)
    mapped = _TAG_TO_TASK.get(key)
    if mapped is not None:
        return mapped
    return task_by_norm.get(key)


def suggest_next_due(
    *,
    services_done: list[str],
    visit_date: date,
    visit_odometer: int,
) -> NextDueSuggestion:
    """
    Soonest next due from matched guideline intervals.

    Among matched tasks, take the minimum interval_km and minimum interval_months
    (whichever fields exist). Unmatched / custom tags are ignored.
    """
    guidelines = load_guidelines()
    by_task = {g["task"]: g for g in guidelines}
    task_by_norm = {_normalize(g["task"]): g["task"] for g in guidelines}

    matched: list[dict] = []
    matched_names: list[str] = []
    for tag in services_done:
        task_name = _resolve_task_name(tag, task_by_norm)
        if task_name is None or task_name not in by_task:
            continue
        if task_name in matched_names:
            continue
        matched.append(by_task[task_name])
        matched_names.append(task_name)

    if not matched:
        return NextDueSuggestion(None, None, [])

    min_km: int | None = None
    min_months: int | None = None
    for guide in matched:
        km = guide.get("interval_km")
        months = guide.get("interval_months")
        if isinstance(km, int) and km > 0:
            min_km = km if min_km is None else min(min_km, km)
        if isinstance(months, int) and months > 0:
            min_months = months if min_months is None else min(min_months, months)

    next_odo = visit_odometer + min_km if min_km is not None else None
    next_date = (
        _add_months(visit_date, min_months) if min_months is not None else None
    )
    return NextDueSuggestion(next_date, next_odo, matched_names)
