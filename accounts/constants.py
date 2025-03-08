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

VALID_FILE_EXTENSIONS = ['.pdf', '.doc', '.docx']

MAX_COMPANY_USERS = 5

# Add this line
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB