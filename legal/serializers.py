# serializers.py
from rest_framework import serializers
from .models import PowerOfAttorney
from django.utils.text import slugify

class PowerOfAttorneySerializer(serializers.ModelSerializer):
    """
    Detailed serializer for Power of Attorney model, used for create/update operations.
    Handles all fields with proper validation and formatting.
    """
    class Meta:
        model = PowerOfAttorney
        fields = [
            'id',
            'slug',
            'document_date',
            'company_name',
            'company_address',
            'company_po_box',
            'attorney_name',
            'attorney_po_box',
            'attorney_address',
            'tender_number',
            'tender_description',
            'tender_beneficiary',
            'witness_name',
            'witness_po_box',
            'witness_title',
            'witness_address',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'id',
            'slug',
            'created_at',
            'updated_at'
        ]

    def validate_tender_number(self, value):
        """
        Validate tender number and ensure uniqueness.
        Convert to uppercase for consistency.
        """
        # Convert to uppercase before validation
        value = value.upper()
        
        # Check if tender_number already exists (excluding current instance)
        instance = self.instance
        if PowerOfAttorney.objects.filter(tender_number=value).exclude(
            pk=instance.pk if instance else None
        ).exists():
            raise serializers.ValidationError(
                "A power of attorney with this tender number already exists."
            )
        return value

    def validate(self, data):
        """
        Add cross-field validation if needed.
        """
        # Ensure all required PO Box fields follow the correct format
        po_box_fields = ['company_po_box', 'attorney_po_box', 'witness_po_box']
        for field in po_box_fields:
            if field in data and data[field]:
                if not data[field].startswith('P.O. Box'):
                    raise serializers.ValidationError({
                        field: "PO Box must start with 'P.O. Box'"
                    })
        return data

    def to_representation(self, instance):
        """
        Customize the output representation.
        """
        representation = super().to_representation(instance)
        # Add any custom representation if needed
        return representation

    def create(self, validated_data):
        """
        Create a new Power of Attorney instance.
        Slug will be generated automatically in model's save method.
        """
        return PowerOfAttorney.objects.create(**validated_data)

    def update(self, instance, validated_data):
        """
        Update an existing Power of Attorney instance.
        Slug will be updated automatically in model's save method if tender_number changes.
        """
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class PowerOfAttorneyListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for listing Power of Attorney instances.
    Includes only essential fields for better performance.
    """
    class Meta:
        model = PowerOfAttorney
        fields = [
            'id',
            'slug',
            'tender_number',
            'company_name',
            'attorney_name',
            'document_date',
            'tender_description',
            'tender_beneficiary',
            'created_at'
        ]
        read_only_fields = fields  # All fields are read-only for listing

    def to_representation(self, instance):
        """
        Customize the output representation for lists.
        """
        representation = super().to_representation(instance)
        # Add any custom representation if needed
        return representation