import pytest


@pytest.fixture(autouse=True)
def state_dir(tmp_path, monkeypatch):
    """Keep the app's saved state out of the real .local/ folder."""
    monkeypatch.setenv("NPV_STATE_DIR", str(tmp_path))
    return tmp_path
