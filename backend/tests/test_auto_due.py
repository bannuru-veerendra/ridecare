"""Unit tests for catalog-based next-due suggestions."""

from datetime import date

from app.utils.auto_due import suggest_next_due


def test_suggest_engine_oil_sets_km_and_months():
    suggestion = suggest_next_due(
        services_done=["Engine Oil"],
        visit_date=date(2026, 1, 15),
        visit_odometer=10000,
    )
    assert suggestion.matched_tasks == ["Engine oil change"]
    assert suggestion.next_service_odometer == 13000
    assert suggestion.next_service_date == date(2026, 4, 15)


def test_suggest_picks_soonest_interval_across_tags():
    # Chain lube is every 500 km; oil is 3000 km / 3 months → km should be 500
    suggestion = suggest_next_due(
        services_done=["Engine Oil", "Chain Lubrication"],
        visit_date=date(2026, 1, 15),
        visit_odometer=10000,
    )
    assert "Chain lubrication" in suggestion.matched_tasks
    assert "Engine oil change" in suggestion.matched_tasks
    assert suggestion.next_service_odometer == 10500
    assert suggestion.next_service_date == date(2026, 4, 15)


def test_suggest_ignores_unknown_custom_tags():
    suggestion = suggest_next_due(
        services_done=["Custom polish"],
        visit_date=date(2026, 1, 15),
        visit_odometer=10000,
    )
    assert suggestion.matched_tasks == []
    assert suggestion.next_service_date is None
    assert suggestion.next_service_odometer is None


def test_suggest_matches_guideline_task_name_directly():
    suggestion = suggest_next_due(
        services_done=["Brake fluid change"],
        visit_date=date(2026, 1, 15),
        visit_odometer=10000,
    )
    assert suggestion.matched_tasks == ["Brake fluid change"]
    assert suggestion.next_service_odometer is None
    assert suggestion.next_service_date == date(2028, 1, 15)
