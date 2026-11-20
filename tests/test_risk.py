import numpy as np
import pytest

from power_risk.portfolio.risk import risk_summary, scenario_pnl


def test_energy_duration_and_position_sign():
    assert scenario_pnl(200, 2, .25, 100) == -50
    assert scenario_pnl(200, 2, .25, 100, "generation") == 50
    with pytest.raises(ValueError):
        scenario_pnl(np.nan, 1, 1, 100)


def test_exact_empirical_tail_mass():
    assert risk_summary([-100, -50, 0, 50], .5)["expected_shortfall_loss_eur"] == 75
    assert risk_summary([-100, -50, 0, 50], .95)["expected_shortfall_loss_eur"] == pytest.approx(100)
