"""
Finance processor for Titanium Template Modifier.

This module handles the cloudFinancialManagement section which contains
budgets, Compute Optimizer, and Cost Optimization Hub settings.
"""

from typing import Dict, Any, List
from ..base_processor import SimpleProcessor
from ..processor_registry import register_processor


@register_processor('cost_management')
class FinanceProcessor(SimpleProcessor):
    """
    Processor for the Cloud Financial Management section.

    Handles:
    - Budget configuration with notifications
    - Compute Optimizer enablement
    - Cost Optimization Hub enablement
    """

    def extract_items(self, section_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract finance configuration items.

        Args:
            section_config: cloudFinancialManagement section from Titanium.yaml

        Returns:
            List of finance configuration items
        """
        items = []

        if not section_config:
            return items

        # Extract Budget configurations
        budgets = section_config.get('budgets', [])
        for budget in budgets:
            budget_name = budget.get('name', 'Budget')
            items.append({
                'name': budget_name,
                'type': 'budget',
                'enabled': True,
                'config': budget
            })

        # Extract Compute Optimizer configuration
        compute_optimizer = section_config.get('computeOptimizer', {})
        if compute_optimizer:
            items.append({
                'name': 'ComputeOptimizer',
                'type': 'compute_optimizer',
                'enabled': compute_optimizer.get('enable', True),
                'config': compute_optimizer
            })

        # Extract Cost Optimization Hub configuration
        cost_opt_hub = section_config.get('costOptimizationHub', {})
        if cost_opt_hub:
            items.append({
                'name': 'CostOptimizationHub',
                'type': 'cost_optimization_hub',
                'enabled': cost_opt_hub.get('enable', True),
                'config': cost_opt_hub
            })

        return items

    def _item_handlers(self):
        return {
            'budget': self._handle_budget,
            'compute_optimizer': self._handle_compute_optimizer,
            'cost_optimization_hub': self._handle_cost_optimization_hub,
        }

    def _handle_budget(self, item, updates):
        updates.update(self._generate_budget_parameters(item.get('config', {})))

    def _handle_compute_optimizer(self, item, updates):
        updates['tEnableComputeOptimizer'] = self._bool(item.get('enabled', True))

    def _handle_cost_optimization_hub(self, item, updates):
        updates['tEnableCostOptimizationHub'] = self._bool(item.get('enabled', True))

    def _generate_budget_parameters(self, config: Dict[str, Any]) -> Dict[str, str]:
        """Generate parameter updates for Budgets template."""
        params = {}

        if 'name' in config:
            params['tBudgetName'] = config['name']
        if 'amount' in config:
            params['tBudgetAmount'] = str(config['amount'])
        if 'timeUnit' in config:
            params['tBudgetTimeUnit'] = config['timeUnit']
        if 'unit' in config:
            params['tBudgetUnit'] = config['unit']

        # Notification settings. tDeployBudgetAlerts gates whether the alert (and
        # its SNS topic + email subscription) is deployed at all. The template
        # defaults it to "true", so when the config carries no notifications
        # (the advisor's budget_alerts=false path emits notifications: []) we MUST
        # set it to "false" explicitly — otherwise the alert email the deploy guide
        # prompts for makes DeployAlerts true and an unwanted 80% budget alert is
        # created, silently ignoring the user's choice (issue #116).
        notifications = config.get('notifications', [])
        params['tDeployBudgetAlerts'] = self._bool(bool(notifications))
        if notifications:
            first = notifications[0]
            params['tBudgetNotificationType'] = first.get('type', 'ACTUAL')
            # Carry the requested threshold so the deployed alert matches the
            # config rather than always falling back to the template's 80%.
            if 'threshold' in first:
                params['tBudgetAlertThreshold'] = str(first['threshold'])

        # Deployment targets
        targets = config.get('deploymentTargets', {})
        accounts = targets.get('accounts', [])
        if accounts:
            params['uBudgetTargetAccounts'] = ','.join(accounts)

        return params