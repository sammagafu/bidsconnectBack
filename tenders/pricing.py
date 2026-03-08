# tenders/pricing.py
"""
Platform fee lookup: use PricingConfig when present, else fall back to constants.
Use get_platform_fee() for tender document and tender summary (and any future fee types).
"""
from decimal import Decimal

from .constants import (
    TENDER_DOCUMENT_FEE_NON_MEMBER_TZS,
    TENDER_SUMMARY_ONE_TIME_FEE_TZS,
)


def get_platform_fee(fee_type):
    """
    Return (amount, currency) for the given fee_type.
    Reads from PricingConfig if an active row exists; otherwise uses constants.
    fee_type: 'tender_document' | 'tender_summary_one_time'
    """
    from .models import PricingConfig

    try:
        config = PricingConfig.objects.get(fee_type=fee_type, is_active=True)
        amount = config.effective_amount
        return (amount, config.currency)
    except PricingConfig.DoesNotExist:
        pass
    # Fallback to constants
    if fee_type == 'tender_document':
        return (Decimal(str(TENDER_DOCUMENT_FEE_NON_MEMBER_TZS)), 'TZS')
    if fee_type == 'tender_summary_one_time':
        return (Decimal(str(TENDER_SUMMARY_ONE_TIME_FEE_TZS)), 'TZS')
    raise ValueError(f"Unknown fee_type: {fee_type}")
