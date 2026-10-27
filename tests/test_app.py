"""Smoke tests: the Streamlit app runs without errors across parameter changes."""

import json
from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).parent.parent / "streamlit_app.py")


def run_app() -> AppTest:
    return AppTest.from_file(APP, default_timeout=60).run()


def test_app_runs_with_defaults():
    at = run_app()
    assert not at.exception
    assert at.title[0].value == "R&D value proposition"
    # Over 2 years, Realistic and Optimistic create value; Pessimistic does not.
    assert "2 of 3 scenarios create value" in at.warning[0].value


def test_app_survives_extreme_parameters():
    at = run_app()
    for key, value in [("margin", 0), ("rate", 0.0), ("occupation", 0)]:
        at.slider(key=key).set_value(value).run()
        assert not at.exception, key
    for key, value in [("n_rd", 0), ("billing", 0.0)]:
        at.number_input(key=key).set_value(value).run()
        assert not at.exception, key


def test_low_margin_shows_loss_warning():
    at = run_app()
    at.slider(key="margin").set_value(20).run()
    assert not at.exception
    assert at.warning or at.error


def test_one_year_window():
    at = run_app()
    at.segmented_control(key="window").set_value("1 year").run()
    assert not at.exception
    assert at.error  # no scenario pays back within a year with the default inputs


def test_discounted_monthly_budget():
    at = run_app()
    at.toggle(key="discounted").set_value(True).run()
    assert not at.exception
    assert any(m.label == "NPV" for m in at.metric)


def test_create_scenario_from_realistic():
    at = run_app()
    at.text_input(key="new_name").set_value("Stretch").run()
    at.button(key="create").click().run()
    assert not at.exception
    assert "Stretch" in at.pills(key="visible").options
    assert any("Created **Stretch**" in s.value for s in at.success)
    labels = [m.value for m in at.metric if m.label == "NPV"]
    assert len(labels) == 4
    assert labels[1] == labels[3]  # copy of Realistic has the same NPV


def test_payback_is_formatted():
    at = run_app()
    paybacks = [m.value for m in at.metric if m.label == "Discounted payback"]
    assert paybacks == ["Not reached", "Month 16", "Month 13"]


def test_validation_tab_cross_check_matches():
    for window in ("3 years", "2 years", "1 year"):
        at = run_app()
        at.segmented_control(key="window").set_value(window).run()
        assert not at.exception
        assert any("Cross-check" in s.value and "They match" in s.value for s in at.success), window
        months = [m.value for m in at.markdown if m.value.startswith("*Month ")]
        assert len(months) == int(window[0])


def test_three_year_window():
    at = run_app()
    at.segmented_control(key="window").set_value("3 years").run()
    assert not at.exception
    assert any("over 3 years" in s.value for s in [*at.success, *at.warning, *at.error])


def test_parameters_are_saved_and_restored(state_dir):
    at = run_app()
    at.slider(key="margin").set_value(80).run()
    at.segmented_control(key="window").set_value("3 years").run()
    saved = json.loads((state_dir / "state.json").read_text())
    assert saved["params"]["margin"] == 80
    assert saved["params"]["window"] == "3 years"

    again = run_app()
    assert not again.exception
    assert again.slider(key="margin").value == 80
    assert again.segmented_control(key="window").value == "3 years"


def test_saved_costs_drive_the_npv(state_dir):
    at = run_app()
    npvs = [m.value for m in at.metric if m.label == "NPV"]
    saved = json.loads((state_dir / "state.json").read_text())
    assert saved["costs"]  # the default costs are saved on the first run

    saved["costs"].append({"Name": "Big licence", "Type": "Licences", "Monthly amount": 50_000.0,
                           "Start month": 1, "End month": None})
    (state_dir / "state.json").write_text(json.dumps(saved))
    again = run_app()
    assert not again.exception
    assert [m.value for m in again.metric if m.label == "NPV"] != npvs
    assert len(json.loads((state_dir / "state.json").read_text())["costs"]) == len(saved["costs"])


def test_reset_restores_defaults(state_dir):
    at = run_app()
    at.slider(key="margin").set_value(50).run()
    at.sidebar.button[0].click().run()
    assert not at.exception
    assert at.slider(key="margin").value == 100
    assert json.loads((state_dir / "state.json").read_text())["params"]["margin"] == 100


def test_unreadable_state_falls_back_to_defaults(state_dir):
    (state_dir / "state.json").write_text("not json")
    at = run_app()
    assert not at.exception
    assert "2 of 3 scenarios create value" in at.warning[0].value
