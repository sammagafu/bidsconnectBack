# accounts/constants.py
ROLE_CHOICES = [
    ('owner', 'Owner'),
    ('admin', 'Admin'),
    ('manager', 'Manager'),
    ('user', 'User'),
]

DOCUMENT_TYPE_CHOICES = [
    ('contract', 'Contract'),
    ('agreement', 'Agreement'),
    ('report', 'Report'),
]

DOCUMENT_CATEGORY_CHOICES = [
    ('legal', 'Legal'),
    ('financial', 'Financial'),
    ('operational', 'Operational'),
    ('hr', 'Human Resources'),
    ('marketing', 'Marketing'),
    ('other', 'Other'),
]

VALID_FILE_EXTENSIONS = ['.pdf', '.doc', '.docx']

MAX_COMPANY_USERS = 5

# Add this line
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
DOCUMENT_EXPIRY_NOTIFICATION_DAYS = 7  # Notify 7 days before expiry
DOCUMENT_EXPIRY_NOTIFICATION_BATCH_SIZE = 100  # Process documents in batches
NOTIFICATION_RETRY_ATTEMPTS = 3
NOTIFICATION_RETRY_DELAY_MINUTES = 5