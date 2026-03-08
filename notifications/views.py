from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from rest_framework import status


def _normalize_tender_notification(n):
    """Return a unified notification dict for a TenderNotification."""
    return {
        "id": f"tender_{n.id}",
        "type": "tender",
        "title": n.tender.title if n.tender else None,
        "body": f"New tender published: {n.tender.reference_number}" if n.tender else None,
        "is_read": getattr(n, 'is_read', False),
        "created_at": n.created_at.isoformat() if n.created_at else None,
        "link": f"/tenders/tenders/{n.tender.slug}/" if n.tender and getattr(n.tender, 'slug', None) else None,
        "tender_id": n.tender_id,
        "tender_reference": n.tender.reference_number if n.tender else None,
        "sent_at": n.sent_at.isoformat() if n.sent_at else None,
    }


def _normalize_marketplace_notification(n):
    """Return a unified notification dict for a marketplace Notification."""
    return {
        "id": f"marketplace_{n.id}",
        "type": n.notification_type,
        "title": n.notification_type,
        "body": n.message,
        "is_read": n.is_read,
        "created_at": n.created_at.isoformat() if n.created_at else None,
        "link": None,
        "related_rfq_id": str(n.related_rfq_id) if n.related_rfq_id else None,
        "related_quote_id": n.related_quote_id,
        "related_message_id": n.related_message_id,
    }


class NotificationsListView(APIView):
    """
    Unified in-app notifications: tender + marketplace. Same shape for all items.
    Query params: type (tender|marketplace|QUOTE|MESSAGE|etc.), is_read (true|false), page, page_size (default 20).
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from tenders.models import TenderNotification
        from marketplace.models import Notification as MarketplaceNotification

        type_filter = request.query_params.get('type')
        is_read_param = request.query_params.get('is_read')
        try:
            page = max(1, int(request.query_params.get('page', 1)))
        except ValueError:
            page = 1
        try:
            page_size = min(100, max(1, int(request.query_params.get('page_size', 20))))
        except ValueError:
            page_size = 20

        items = []

        # Tender notifications
        if not type_filter or type_filter.lower() == 'tender':
            tn_qs = TenderNotification.objects.filter(
                subscription__user=request.user
            ).select_related('tender', 'subscription').order_by('-created_at')
            for n in tn_qs:
                items.append((n.created_at, _normalize_tender_notification(n)))

        # Marketplace notifications
        if not type_filter or type_filter.upper() in ('MARKETPLACE', 'QUOTE', 'MESSAGE', 'REVIEW', 'RFQ', 'SYSTEM'):
            mkt_qs = MarketplaceNotification.objects.filter(user=request.user).order_by('-created_at')
            if is_read_param is not None:
                if is_read_param.lower() in ('true', '1'):
                    mkt_qs = mkt_qs.filter(is_read=True)
                elif is_read_param.lower() in ('false', '0'):
                    mkt_qs = mkt_qs.filter(is_read=False)
            for n in mkt_qs:
                if type_filter and type_filter.upper() not in ('MARKETPLACE', n.notification_type):
                    continue
                items.append((n.created_at, _normalize_marketplace_notification(n)))

        # Sort merged by created_at desc
        items.sort(key=lambda x: x[0] or '', reverse=True)
        unified = [it[1] for it in items]

        # Apply is_read filter for tender we don't have is_read; for unified list we filter marketplace only when is_read param set
        if is_read_param is not None and (not type_filter or type_filter.lower() != 'tender'):
            if is_read_param.lower() in ('false', '0'):
                unified = [u for u in unified if u.get('is_read') is False]
            elif is_read_param.lower() in ('true', '1'):
                unified = [u for u in unified if u.get('is_read') is True]

        total = len(unified)
        start = (page - 1) * page_size
        end = start + page_size
        page_items = unified[start:end]

        return Response({
            "app": "notifications",
            "status": "ready",
            "items": page_items,
            "count": len(page_items),
            "total": total,
            "page": page,
            "page_size": page_size,
        })


class NotificationMarkReadView(APIView):
    """
    PATCH: Mark a notification as read. Only marketplace notifications support is_read.
    id format: marketplace_<pk> (e.g. marketplace_5). Tender notifications return 400 or no-op.
    """
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk):
        # pk can be "marketplace_123" or "tender_123"
        if not pk.startswith('marketplace_'):
            return Response(
                {"detail": "Mark as read is only supported for marketplace notifications."},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            id_num = int(pk.replace('marketplace_', ''))
        except ValueError:
            return Response({"detail": "Invalid notification id."}, status=status.HTTP_400_BAD_REQUEST)

        from marketplace.models import Notification as MarketplaceNotification
        notification = MarketplaceNotification.objects.filter(id=id_num, user=request.user).first()
        if not notification:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        is_read = request.data.get('is_read')
        if is_read is not None:
            notification.is_read = bool(is_read)
            notification.save(update_fields=['is_read'])

        return Response(_normalize_marketplace_notification(notification))


class NotificationsReadyView(APIView):
    """Unauthenticated ping: app status only."""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response({"app": "notifications", "status": "ready"})
