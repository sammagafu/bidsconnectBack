# bids/tests/test_bid_scope_and_permissions.py
"""Tests for bid list scoping (non-staff sees only own company bids) and company_id restriction."""
from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import Company, CompanyUser
from tenders.models import Category, Tender
from bids.models import Bid

User = get_user_model()


class BidListScopeTests(TestCase):
    """Non-staff users only see bids for companies they belong to."""

    def setUp(self):
        self.client = APIClient()
        self.user_a = User.objects.create_user(
            email='usera@example.com', password='pass1234'
        )
        self.user_b = User.objects.create_user(
            email='userb@example.com', password='pass1234'
        )
        self.staff = User.objects.create_user(
            email='staff@example.com', password='pass1234', is_staff=True
        )
        self.company_a = Company.objects.create(
            owner=self.user_a, name='Company A', deleted_at=None
        )
        self.company_b = Company.objects.create(
            owner=self.user_b, name='Company B', deleted_at=None
        )
        CompanyUser.objects.create(
            company=self.company_a, user=self.user_a, role='owner', deleted_at=None
        )
        CompanyUser.objects.create(
            company=self.company_b, user=self.user_b, role='owner', deleted_at=None
        )
        cat = Category.objects.create(name='Test', slug='test')
        self.tender = Tender.objects.create(
            title='T1',
            reference_number='REF-001',
            slug='ref-001',
            status='published',
            tender_type_country='National',
            tender_type_sector='Public Sector',
            category=cat,
            submission_deadline=timezone.now() + timezone.timedelta(days=7),
            created_by=self.user_a,
        )
        self.bid_a = Bid.objects.create(
            tender=self.tender,
            company=self.company_a,
            bidder=self.user_a,
            total_price=Decimal('100000'),
            currency='TZS',
            status='draft',
        )
        self.bid_b = Bid.objects.create(
            tender=self.tender,
            company=self.company_b,
            bidder=self.user_b,
            total_price=Decimal('200000'),
            currency='TZS',
            status='draft',
        )

    def _bid_ids_from_response(self, resp):
        data = resp.json()
        if isinstance(data, list):
            return [b['id'] for b in data]
        return [b['id'] for b in data.get('results', data)]

    def test_non_staff_sees_only_own_company_bids(self):
        """User A does not see User B's company bid when listing without filters."""
        self.client.force_authenticate(self.user_a)
        url = reverse('bids:bid-list')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ids = self._bid_ids_from_response(resp)
        self.assertIn(self.bid_a.id, ids)
        self.assertNotIn(self.bid_b.id, ids)

    def test_staff_sees_all_bids(self):
        """Staff user sees all bids."""
        self.client.force_authenticate(self.staff)
        url = reverse('bids:bid-list')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ids = self._bid_ids_from_response(resp)
        self.assertIn(self.bid_a.id, ids)
        self.assertIn(self.bid_b.id, ids)


class BidCompanyRestrictionTests(TestCase):
    """Creating a bid with company_id outside user's companies returns 400."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='user@example.com', password='pass1234'
        )
        self.company = Company.objects.create(
            owner=self.user, name='My Co', deleted_at=None
        )
        CompanyUser.objects.create(
            company=self.company, user=self.user, role='owner', deleted_at=None
        )
        self.other_company = Company.objects.create(
            owner=User.objects.create_user(email='other@example.com', password='x'),
            name='Other Co',
            deleted_at=None
        )
        cat = Category.objects.create(name='Test', slug='test')
        self.tender = Tender.objects.create(
            title='T1',
            reference_number='REF-002',
            slug='ref-002',
            status='published',
            tender_type_country='National',
            tender_type_sector='Public Sector',
            category=cat,
            submission_deadline=timezone.now() + timezone.timedelta(days=7),
            created_by=self.user,
        )

    def test_create_bid_with_other_company_returns_400(self):
        """Passing company_id of a company user is not member of fails validation."""
        self.client.force_authenticate(self.user)
        url = reverse('bids:bid-list')
        resp = self.client.post(url, {
            'tender_id': self.tender.id,
            'company_id': str(self.other_company.id),
            'total_price': '50000',
            'currency': 'TZS',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(
            Bid.objects.filter(
                tender=self.tender, company=self.other_company
            ).exists()
        )
