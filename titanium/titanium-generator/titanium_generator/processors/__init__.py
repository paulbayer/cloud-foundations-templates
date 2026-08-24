"""
Simplified processors for Titanium sections.

This module contains concrete processor implementations that inherit from
SimpleProcessor and demonstrate the simplified approach.
"""

from .organization_processor import SimpleOrganizationProcessor
from .security_processor import SimpleSecurityProcessor
from .finance_processor import FinanceProcessor

__all__ = [
    'SimpleOrganizationProcessor',
    'SimpleSecurityProcessor',
    'FinanceProcessor'
]
