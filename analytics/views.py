from datetime import timedelta
from django.utils import timezone
from django.db.models import Count, Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions

from accounts.models import CompanyUser


class AnalyticsDashboardView(APIView):
    """
    Comprehensive analytics dashboard. Returns tenders, bids, marketplace, accounts, and payments stats.
    Query params:
      - scope: 'platform' (default) or 'company'. If 'company', require company_id.
      - company_id: UUID (required when scope=company). Filter stats to this company.
      - period: optional '30d' to add recent metrics (e.g. tenders published, bids submitted in last 30 days).
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        scope = request.query_params.get('scope', 'platform')
        company_id = request.query_params.get('company_id')
        period = request.query_params.get('period')

        if scope == 'company' and not company_id:
            return Response(
                {"detail": "company_id is required when scope=company"},
                status=400
            )
        if scope == 'company' and company_id:
            if not CompanyUser.objects.filter(
                company_id=company_id,
                user=request.user,
                deleted_at__isnull=True,
                company__deleted_at__isnull=True
            ).exists():
                return Response(
                    {"detail": "You do not have access to this company."},
                    status=403
                )

        from accounts.models import Company
        from tenders.models import Tender
        from bids.models import Bid
        from marketplace.models import ProductService, RFQ, Quote, CompanyReview
        from payments.models import Payment

        now = timezone.now()
        recent_cutoff = now - timedelta(days=30) if period == '30d' else None

        # Base filters for company scope
        company_filter_bids = Q(company_id=company_id) if scope == 'company' and company_id else Q()
        company_filter_products = Q(company_id=company_id) if scope == 'company' and company_id else Q()
        company_filter_quotes = Q(seller_id=company_id) if scope == 'company' and company_id else Q()
        company_filter_reviews = Q(company_id=company_id) if scope == 'company' and company_id else Q()

        # Tenders: platform = all tenders; company = tenders we've bid on (distinct count)
        if scope == 'platform':
            tender_qs = Tender.objects.all()
            tenders_total = tender_qs.count()
            tenders_by_status = dict(
                tender_qs.values('status').annotate(count=Count('id')).values_list('status', 'count')
            )
            for s in ['draft', 'pending', 'published', 'evaluation', 'awarded', 'closed', 'canceled']:
                tenders_by_status.setdefault(s, 0)
            tenders_recent_published = (
                tender_qs.filter(status='published', publication_date__gte=recent_cutoff).count()
                if recent_cutoff else None
            )
            tenders_recent_created = (
                tender_qs.filter(created_at__gte=recent_cutoff).count() if recent_cutoff else None
            )
        else:
            # Company scope: tenders that this company has bid on (distinct count)
            bids_company = Bid.objects.filter(company_id=company_id)
            tenders_total = bids_company.values('tender').distinct().count()
            tenders_by_status = {}  # Not applicable for company scope (use bids.by_status)
            tenders_recent_published = None
            tenders_recent_created = (
                bids_company.filter(created_at__gte=recent_cutoff).count() if recent_cutoff else None
            )

        tenders = {
            "total": tenders_total,
            "by_status": tenders_by_status,
        }
        if tenders_recent_published is not None:
            tenders["recent_published_30d"] = tenders_recent_published
        if tenders_recent_created is not None:
            tenders["recent_created_30d"] = tenders_recent_created

        # Bids
        bid_qs = Bid.objects.filter(company_filter_bids) if company_filter_bids else Bid.objects.all()
        bids_total = bid_qs.count()
        bids_by_status = dict(
            bid_qs.values('status').annotate(count=Count('id')).values_list('status', 'count')
        )
        for s in ['draft', 'submitted', 'under_evaluation', 'accepted', 'rejected', 'withdrawn']:
            bids_by_status.setdefault(s, 0)
        bids_recent_submitted = (
            bid_qs.filter(status='submitted', submission_date__gte=recent_cutoff).count()
            if recent_cutoff else None
        )
        bids = {"total": bids_total, "by_status": bids_by_status}
        if bids_recent_submitted is not None:
            bids["recent_submitted_30d"] = bids_recent_submitted

        # Marketplace
        product_qs = ProductService.objects.filter(company_filter_products) if company_filter_products else ProductService.objects.all()
        products_active = product_qs.filter(is_active=True).count()
        products_total = product_qs.count()

        if scope == 'company' and company_id:
            user_ids = list(CompanyUser.objects.filter(company_id=company_id, deleted_at__isnull=True).values_list('user_id', flat=True))
            rfq_qs = RFQ.objects.filter(buyer_id__in=user_ids)
        else:
            rfq_qs = RFQ.objects.all()
        rfq_open = rfq_qs.filter(status='OPEN').count()
        rfq_closed = rfq_qs.filter(status='CLOSED').count()

        quote_qs = Quote.objects.filter(company_filter_quotes) if company_filter_quotes else Quote.objects.all()
        quotes_pending = quote_qs.filter(status='PENDING').count()
        quotes_accepted = quote_qs.filter(status='ACCEPTED').count()
        quotes_rejected = quote_qs.filter(status='REJECTED').count()

        review_qs = CompanyReview.objects.filter(company_filter_reviews) if company_filter_reviews else CompanyReview.objects.all()
        reviews_approved = review_qs.filter(is_approved=True).count()

        marketplace = {
            "products_total": products_total,
            "products_active": products_active,
            "rfq_open": rfq_open,
            "rfq_closed": rfq_closed,
            "rfq_total": rfq_open + rfq_closed,
            "quotes_pending": quotes_pending,
            "quotes_accepted": quotes_accepted,
            "quotes_rejected": quotes_rejected,
            "quotes_total": quotes_pending + quotes_accepted + quotes_rejected,
            "reviews_approved": reviews_approved,
        }

        # Accounts: platform = all companies / users; company = members
        if scope == 'platform':
            from django.contrib.auth import get_user_model
            User = get_user_model()
            accounts = {
                "companies_total": Company.objects.filter(deleted_at__isnull=True).count(),
                "users_total": User.objects.count(),
            }
        else:
            accounts = {
                "company_members": CompanyUser.objects.filter(company_id=company_id, deleted_at__isnull=True).count(),
            }

        # Payments: platform = all; company = payments by users in company
        if scope == 'company' and company_id:
            user_ids = list(CompanyUser.objects.filter(company_id=company_id, deleted_at__isnull=True).values_list('user_id', flat=True))
            payment_qs = Payment.objects.filter(user_id__in=user_ids)
        else:
            payment_qs = Payment.objects.all()
        payments_total = payment_qs.count()
        payments_by_status = dict(
            payment_qs.values('status').annotate(count=Count('id')).values_list('status', 'count')
        )
        for s in ['pending', 'succeeded', 'failed']:
            payments_by_status.setdefault(s, 0)
        payments = {"total": payments_total, "by_status": payments_by_status}

        payload = {
            "app": "analytics",
            "status": "ready",
            "scope": scope,
            "period": period,
            "stats": {
                "tenders": tenders,
                "bids": bids,
                "marketplace": marketplace,
                "accounts": accounts,
                "payments": payments,
            },
        }
        if company_id:
            payload["company_id"] = str(company_id)
        return Response(payload)


class AnalyticsReadyView(APIView):
    """Unauthenticated ping: app status only."""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response({"app": "analytics", "status": "ready"})
