from rest_framework import serializers
from .models import StaffMember


class StaffRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = StaffMember
        fields = ["id", "email", "password", "first_name", "last_name", "role"]

    def create(self, validated_data):
        return StaffMember.objects.create_user(**validated_data)


class StaffSerializer(serializers.ModelSerializer):
    class Meta:
        model = StaffMember
        fields = ["id", "email", "first_name", "last_name", "role", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]


class StaffLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()
