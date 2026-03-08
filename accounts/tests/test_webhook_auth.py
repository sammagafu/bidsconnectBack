# accounts/tests/test_webhook_auth.py
"""Tests for document expiry webhook: secret required when set, 401 when wrong."""
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient


class DocumentExpiryWebhookAuthTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse('accounts:document-expiry-webhook')

    @override_settings(DOCUMENT_EXPIRY_WEBHOOK_SECRET='')
    def test_webhook_200_when_secret_empty(self):
        """When DOCUMENT_EXPIRY_WEBHOOK_SECRET is empty, no auth required."""
        resp = self.client.post(
            self.url, {'event': 'check_expiry'}, format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('processed_count', resp.json())

    @override_settings(DOCUMENT_EXPIRY_WEBHOOK_SECRET='my-secret')
    def test_webhook_401_when_secret_required_and_missing(self):
        """When secret is set and header missing, returns 401."""
        resp = self.client.post(
            self.url, {'event': 'check_expiry'}, format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(
            resp.json().get('detail'),
            'Invalid or missing webhook secret.'
        )

    @override_settings(DOCUMENT_EXPIRY_WEBHOOK_SECRET='my-secret')
    def test_webhook_401_when_secret_wrong(self):
        """When X-Webhook-Secret is wrong, returns 401."""
        resp = self.client.post(
            self.url,
            {'event': 'check_expiry'},
            format='json',
            HTTP_X_WEBHOOK_SECRET='wrong'
        )
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    @override_settings(DOCUMENT_EXPIRY_WEBHOOK_SECRET='my-secret')
    def test_webhook_200_when_secret_correct(self):
        """When X-Webhook-Secret matches, request is processed."""
        resp = self.client.post(
            self.url,
            {'event': 'check_expiry'},
            format='json',
            HTTP_X_WEBHOOK_SECRET='my-secret'
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
