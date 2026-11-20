import pytest

from power_risk.backtesting.validation import average_precision_score, brier_score_loss, mean_pinball_loss


def test_scoring_rules_and_tied_predictions():
    assert mean_pinball_loss([0, 10], [2, 8], .5) == 1
    assert brier_score_loss([0, 1], [.2, .8]) == pytest.approx(.04)
    assert average_precision_score([0, 1, 0, 1], [.5, .5, .5, .5]) == .5
    assert average_precision_score([0, 1], [.1, .9]) == 1
