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
    assert len(at.success) == 1  # all default scenarios create value


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
