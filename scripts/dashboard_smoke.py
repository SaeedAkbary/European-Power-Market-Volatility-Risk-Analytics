"""Exercise all dashboard page branches against generated real outputs."""
from pathlib import Path

from streamlit.testing.v1 import AppTest

app = AppTest.from_file(str(Path("dashboards/app.py").resolve()), default_timeout=60).run()
assert not app.exception, app.exception
for page in ["Volatility Monitor", "Fundamental Drivers", "Probabilistic Forecasting", "Portfolio Risk"]:
    app.sidebar.radio[0].set_value(page).run()
    assert not app.exception, (page, app.exception)
print("All five dashboard pages passed Streamlit AppTest")
