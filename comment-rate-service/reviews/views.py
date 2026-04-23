from django.db.models import Avg, Count
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from .models import Rating, Comment
from .serializers import RatingSerializer, CommentSerializer, ProductRatingSummarySerializer


class RatingListView(APIView):
    """
    GET  /api/reviews/ratings/?product_id=<id>   — ratings for a product
    POST /api/reviews/ratings/                    — submit/update a rating
    """

    def get(self, request):
        product_id = request.query_params.get("product_id")
        customer_id = request.query_params.get("customer_id")
        qs = Rating.objects.all()
        if product_id:
            qs = qs.filter(product_id=product_id)
        if customer_id:
            qs = qs.filter(customer_id=customer_id)
        return Response(RatingSerializer(qs, many=True).data)

    def post(self, request):
        serializer = RatingSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        rating, created = Rating.objects.update_or_create(
            product_id=serializer.validated_data["product_id"],
            customer_id=serializer.validated_data["customer_id"],
            defaults={"score": serializer.validated_data["score"]},
        )
        return Response(
            RatingSerializer(rating).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class ProductRatingSummaryView(APIView):
    """GET /api/reviews/ratings/product/<product_id>/summary/"""

    def get(self, request, product_id):
        agg = Rating.objects.filter(product_id=product_id).aggregate(
            average_score=Avg("score"), total_ratings=Count("id")
        )
        return Response({
            "product_id": product_id,
            "average_score": round(agg["average_score"] or 0, 2),
            "total_ratings": agg["total_ratings"],
        })


class CommentListView(APIView):
    """
    GET  /api/reviews/comments/?product_id=<id>   — comments for a product
    POST /api/reviews/comments/                    — post a comment
    """

    def get(self, request):
        product_id = request.query_params.get("product_id")
        qs = Comment.objects.filter(is_approved=True)
        if product_id:
            qs = qs.filter(product_id=product_id)
        return Response(CommentSerializer(qs, many=True).data)

    def post(self, request):
        serializer = CommentSerializer(data=request.data)
        if serializer.is_valid():
            comment = serializer.save()
            return Response(CommentSerializer(comment).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CommentDetailView(APIView):
    """PUT/DELETE /api/reviews/comments/<id>/"""

    def put(self, request, pk):
        comment = get_object_or_404(Comment, pk=pk)
        content = request.data.get("content")
        if content is not None:
            comment.content = content
            comment.save()
        return Response(CommentSerializer(comment).data)

    def delete(self, request, pk):
        comment = get_object_or_404(Comment, pk=pk)
        comment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
