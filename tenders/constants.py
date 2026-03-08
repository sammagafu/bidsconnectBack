# tenders/constants.py
# Tender document access and summary pricing (TZS)
# Use tenders.pricing.get_platform_fee(fee_type) for runtime prices; these are fallbacks when no PricingConfig exists.

# Fee for non-members / unregistered users to get tender document (TZS)
TENDER_DOCUMENT_FEE_NON_MEMBER_TZS = 3_000

# Tender summary and updates: premium = free; one-time = 50,000 TZS
TENDER_SUMMARY_PREMIUM_FREE = True
TENDER_SUMMARY_ONE_TIME_FEE_TZS = 50_000

# Currency for display
TENDER_PARTICIPATION_FEE_CURRENCIES = ('TZS', 'USD')
