# bids/serializers.py
from rest_framework import serializers
from rest_framework.fields import CurrentUserDefault

from .models import Bid, BidDocument, AuditLog


class BidDocumentSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)

    class Meta:
        model = BidDocument
        fields = [
            'id',
            'required_document',
            'file',
            'uploaded_at',
        ]
        read_only_fields = ['uploaded_at']

    def validate(self, attrs):
        req_doc = attrs.get('required_document')
        # bid_instance provided via context when nested under BidSerializer
        bid = self.context.get('bid_instance') or attrs.get('bid')
        if req_doc and bid and req_doc.tender_id != bid.tender_id:
            raise serializers.ValidationError(
                "This document type is not required for the selected tender."
            )
        return attrs


class BidSerializer(serializers.ModelSerializer):
    # Automatically use the logged-in user as bidder if omitted
    bidder = serializers.HiddenField(default=CurrentUserDefault())
    # Nested docs are now optional if not required by the tender
    documents = BidDocumentSerializer(many=True, required=False)

    class Meta:
        model = Bid
        fields = [
            'id',
            'tender',
            'bidder',
            'company',
            'validity_days',
            'status',
            'submission_date',
            'documents',
        ]
        read_only_fields = ['submission_date']

    def create(self, validated_data):
        docs_data = validated_data.pop('documents', [])
        bid = super().create(validated_data)
        # only create docs if any were provided
        for doc in docs_data:
            BidDocument.objects.create(bid=bid, **doc)
        return bid

    def update(self, instance, validated_data):
        docs_data = validated_data.pop('documents', None)
        bid = super().update(instance, validated_data)

        # if documents key is provided, sync nested docs
        if docs_data is not None:
            keep_ids = []
            for doc in docs_data:
                doc_id = doc.get('id')
                if doc_id:
                    try:
                        obj = BidDocument.objects.get(id=doc_id, bid=bid)
                        obj.required_document = doc.get('required_document', obj.required_document)
                        if 'file' in doc:
                            obj.file = doc['file']
                        obj.save()
                        keep_ids.append(obj.id)
                    except BidDocument.DoesNotExist:
                        continue
                else:
                    new_obj = BidDocument.objects.create(bid=bid, **doc)
                    keep_ids.append(new_obj.id)
            # remove any documents not in the incoming list
            for existing in bid.documents.exclude(id__in=keep_ids):
                existing.delete()

        return bid


class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = [
            'id',
            'tender',
            'user',
            'action',
            'details',
            'timestamp',
        ]
        read_only_fields = ['timestamp']
