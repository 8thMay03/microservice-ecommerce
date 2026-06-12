from rest_framework import serializers
from .models import ManagerUser


class ManagerSerializer(serializers.ModelSerializer):
    class Meta:
        model = ManagerUser
        fields = ["id", "email", "first_name", "last_name", "created_at"]
        read_only_fields = ["id", "created_at"]


class ManagerRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = ManagerUser
        fields = ["email", "password", "first_name", "last_name"]

    def create(self, validated_data):
        return ManagerUser.objects.create_user(**validated_data)


class ManagerLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()
