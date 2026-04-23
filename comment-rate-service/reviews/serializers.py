from rest_framework import serializers
from .models import Rating, Comment


class RatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rating
        fields = ["id", "product_id", "customer_id", "score", "created_at"]
        read_only_fields = ["id", "created_at"]


class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ["id", "product_id", "customer_id", "customer_name", "content", "is_approved", "created_at"]
        read_only_fields = ["id", "is_approved", "created_at"]


class ProductRatingSummarySerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    average_score = serializers.FloatField()
    total_ratings = serializers.IntegerField()
