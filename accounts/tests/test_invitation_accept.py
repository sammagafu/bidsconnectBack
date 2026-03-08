# accounts/tests/test_invitation_accept.py
"""Tests for invitation accept: email match, company limit, 403/400."""
import uuid
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import Company, CompanyUser, CompanyInvitation
from accounts.constants import MAX_COMPANY_USERS

User = get_user_model()


class InvitationAcceptAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(
            email='owner@example.com', password='pass1234'
        )
        self.invitee = User.objects.create_user(
            email='invitee@example.com', password='pass1234'
        )
        self.other = User.objects.create_user(
            email='other@example.com', password='pass1234'
        )
        self.company = Company.objects.create(
            owner=self.owner, name='Test Co', deleted_at=None
        )
        CompanyUser.objects.create(
            company=self.company, user=self.owner, role='owner', deleted_at=None
        )

    def _create_invitation(self, invited_email, **kwargs):
        return CompanyInvitation.objects.create(
            company=self.company,
            invited_email=invited_email,
            invited_by=self.owner,
            role='user',
            expires_at=timezone.now() + timedelta(days=1),
            accepted=False,
            **kwargs
        )

    def test_accept_success_when_email_matches(self):
        """Logged-in user whose email matches invited_email can accept."""
        inv = self._create_invitation(self.invitee.email)
        url = reverse('accounts:invitation-accept', args=[inv.token])
        self.client.force_authenticate(self.invitee)
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('detail', resp.json())
        inv.refresh_from_db()
        self.assertTrue(inv.accepted)
        self.assertTrue(
            CompanyUser.objects.filter(
                company=self.company, user=self.invitee, deleted_at__isnull=True
            ).exists()
        )

    def test_accept_403_when_email_does_not_match(self):
        """Different logged-in user cannot accept (403)."""
        inv = self._create_invitation(self.invitee.email)
        url = reverse('accounts:invitation-accept', args=[inv.token])
        self.client.force_authenticate(self.other)
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            resp.json().get('detail'),
            'This invitation was sent to a different email address.'
        )
        inv.refresh_from_db()
        self.assertFalse(inv.accepted)
        self.assertFalse(
            CompanyUser.objects.filter(
                company=self.company, user=self.other, deleted_at__isnull=True
            ).exists()
        )

    def test_accept_400_when_company_at_limit(self):
        """When company already has MAX_COMPANY_USERS, accept returns 400."""
        # Fill company up to limit (owner already counts as 1)
        for i in range(MAX_COMPANY_USERS - 1):
            u = User.objects.create_user(
                email=f'user{i}@example.com', password='pass1234'
            )
            CompanyUser.objects.create(
                company=self.company, user=u, role='user', deleted_at=None
            )
        inv = self._create_invitation(self.invitee.email)
        url = reverse('accounts:invitation-accept', args=[inv.token])
        self.client.force_authenticate(self.invitee)
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            resp.json().get('detail'),
            'Company user limit reached.'
        )
