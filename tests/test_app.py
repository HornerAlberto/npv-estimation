"""Smoke tests: the Streamlit app runs without errors across parameter changes."""

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
