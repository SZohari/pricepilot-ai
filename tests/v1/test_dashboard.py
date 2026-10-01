from pathlib import Path
import pytest
pytest.importorskip("pyarrow", reason="Optional legacy Streamlit UI requires a compatible PyArrow build")
from streamlit.testing.v1 import AppTest
from src.application.service import load_demo


def test_default_dashboard_and_scenario_controls(monkeypatch):
    monkeypatch.delenv("PRICEPILOT_DB_PATH", raising=False)
    app = AppTest.from_file(str(Path("src/dashboard/app.py")), default_timeout=30).run()
    assert not app.exception
    assert app.title[0].value == "PricePilot"
    assert app.metric[0].value == str(len(load_demo().products))
    # Stress scenario rerenders through the shared domain service.
    app.sidebar.slider[0].set_value(30).run()
    assert not app.exception
    assert app.metric[0].value == str(len(load_demo().products))
