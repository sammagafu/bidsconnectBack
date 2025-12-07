from rest_framework import serializers
from .models import PowerOfAttorney, TenderSecuringDeclaration, LitigationHistory, CoverLetter

class PowerOfAttorneySerializer(serializers.ModelSerializer):
    class Meta:
        model = PowerOfAttorney
        fields = '__all__'

class TenderSecuringDeclarationSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenderSecuringDeclaration
        fields = '__all__'

class LitigationHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = LitigationHistory
        fields = '__all__'

class CoverLetterSerializer(serializers.ModelSerializer):
    class Meta:
        model = CoverLetter
        fields = '__all__'