# accounts/constants.py

# User roles
ROLE_CHOICES = [
    ('owner', 'Owner'),
    ('admin', 'Admin'),
    ('manager', 'Manager'),
    ('user', 'User'),
]

# Document types & categories
DOCUMENT_TYPE_CHOICES = [
    ('Business License', 'Business License'),
    ('BRELA',           'BRELA'),
    ('TIN',             'TIN'),
    ('Tax Clearance',   'Tax Clearance'),
    ('Bank Statement',  'Bank Statement'),
]

DOCUMENT_CATEGORY_CHOICES = [
    ('legal', 'Legal'),
    ('financial', 'Financial'),
    ('operational', 'Operational'),
    ('hr', 'Human Resources'),
    ('marketing', 'Marketing'),
    ('other', 'Other'),
]

# File upload settings
VALID_FILE_EXTENSIONS = ['.pdf', '.doc', '.docx']
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

# Limits
MAX_COMPANY_USERS = 5
MAX_COMPANIES_PER_USER = 3

# Document expiry / notification
DEFAULT_DOCUMENT_EXPIRY_DAYS = 30
DOCUMENT_EXPIRY_NOTIFICATION_DAYS = 7  # Notify 7 days before expiry
DOCUMENT_EXPIRY_NOTIFICATION_BATCH_SIZE = 100
NOTIFICATION_RETRY_ATTEMPTS = 3
NOTIFICATION_RETRY_DELAY_MINUTES = 5

# Invitation settings
INVITATION_EXPIRY_DAYS = 7
