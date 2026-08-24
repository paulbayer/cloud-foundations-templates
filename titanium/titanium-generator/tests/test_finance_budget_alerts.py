"""
Tests for #116: budget_alerts=false must actually disable the budget alert.

finance/01 gates the alert on tDeployBudgetAlerts (Default "true") AND a
non-empty uBudgetAlertEmail. The deploy guide always supplies an email, so unless
the generator sets tDeployBudgetAlerts="false" when the config carries no
notifications, an unwanted 80% alert deploys and the user's "no alerts" choice is
ignored. The generator must set tDeployBudgetAlerts from notification presence
(and carry the threshold when alerts are on).
"""

from titanium_generator.processors.finance_processor import FinanceProcessor


def _budget_params(config):
    return FinanceProcessor()._generate_budget_parameters(config)


def test_no_notifications_disables_alerts():
    params = _budget_params({"name": "aviato-monthly-budget", "amount": 2000,
                             "notifications": []})
    assert params["tDeployBudgetAlerts"] == "false"


def test_missing_notifications_key_disables_alerts():
    # Absent key is treated the same as an empty list.
    params = _budget_params({"name": "b", "amount": 100})
    assert params["tDeployBudgetAlerts"] == "false"


def test_notifications_enable_alerts_and_carry_type_and_threshold():
    params = _budget_params({
        "name": "b",
        "amount": 2000,
        "notifications": [
            {"type": "FORECASTED", "threshold": 90, "thresholdType": "PERCENTAGE"}
        ],
    })
    assert params["tDeployBudgetAlerts"] == "true"
    assert params["tBudgetNotificationType"] == "FORECASTED"
    assert params["tBudgetAlertThreshold"] == "90"


def test_notification_without_threshold_still_enables():
    params = _budget_params({"name": "b", "notifications": [{"type": "ACTUAL"}]})
    assert params["tDeployBudgetAlerts"] == "true"
    assert params["tBudgetNotificationType"] == "ACTUAL"
    assert "tBudgetAlertThreshold" not in params


def test_core_budget_fields_still_mapped():
    params = _budget_params({
        "name": "b", "amount": 2000, "timeUnit": "MONTHLY", "unit": "USD",
        "notifications": [],
    })
    assert params["tBudgetName"] == "b"
    assert params["tBudgetAmount"] == "2000"
    assert params["tBudgetTimeUnit"] == "MONTHLY"
    assert params["tBudgetUnit"] == "USD"
