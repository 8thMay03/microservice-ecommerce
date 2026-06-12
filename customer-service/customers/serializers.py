from rest_framework import serializers
from .models import Customer


class CustomerRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = Customer
        fields = [
            "id", "email", "password", "password_confirm",
            "first_name", "last_name", "phone", "address",
        ]

    def validate(self, data):
        if data["password"] != data.pop("password_confirm"):
            raise serializers.ValidationError("Passwords do not match.")
        return data

    def create(self, validated_data):
        return Customer.objects.create_user(**validated_data)


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ["id", "email", "first_name", "last_name", "phone", "address", "created_at"]
        read_only_fields = ["id", "created_at"]


class CustomerUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ["first_name", "last_name", "phone", "address"]


class CustomerLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()
