from rest_framework import serializers
from .models import User


class UserSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(format='%Y-%m-%dT%H:%M:%S.%fZ', read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'name', 'age', 'city', 'created_at']
