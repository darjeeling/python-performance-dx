from rest_framework import serializers
from .models import Product, Order, OrderItem, Review


# ============= Product Serializers =============

class ProductListSerializer(serializers.ModelSerializer):
    """
    상품 목록 조회용 (최적화 - 필요한 필드만)
    """
    class Meta:
        model = Product
        fields = ['id', 'name', 'price', 'stock', 'category', 'updated_at']


class ProductDetailSerializer(serializers.ModelSerializer):
    """
    상품 상세 조회용 (전체 필드)
    주의: ViewSet에서 annotate(review_count=Count('reviews'), average_rating=Avg('reviews__rating')) 필요
    """
    review_count = serializers.IntegerField(read_only=True)
    average_rating = serializers.FloatField(read_only=True)

    class Meta:
        model = Product
        fields = '__all__'


class ProductDetailOptimizedSerializer(serializers.ModelSerializer):
    """
    상품 상세 조회용 (최적화 버전)
    주의: ViewSet에서 annotate(review_count=Count('reviews'), average_rating=Avg('reviews__rating')) 필요
    """
    review_count = serializers.IntegerField(read_only=True)
    average_rating = serializers.FloatField(read_only=True)

    class Meta:
        model = Product
        fields = '__all__'


# ============= Review Serializers =============

class ReviewSerializer(serializers.ModelSerializer):
    """
    리뷰 기본 Serializer
    """
    class Meta:
        model = Review
        fields = ['id', 'product', 'user_id', 'rating', 'body', 'created_at']


class ReviewListSerializer(serializers.ModelSerializer):
    """
    리뷰 목록용 (상품명 포함)
    주의: ViewSet에서 select_related('product') 필요
    """
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = Review
        fields = ['id', 'product', 'product_name', 'user_id', 'rating', 'body', 'created_at']


# 하위 호환성을 위해 유지 (실제로는 ReviewListSerializer와 동일)
ReviewListOptimizedSerializer = ReviewListSerializer


# ============= OrderItem Serializers =============

class OrderItemSerializer(serializers.ModelSerializer):
    """
    주문 아이템 (기본)
    """
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'quantity', 'unit_price', 'subtotal']


class OrderItemDetailSerializer(serializers.ModelSerializer):
    """
    주문 아이템 (상품 정보 포함)
    주의: ViewSet에서 select_related('product') 또는 prefetch_related('items__product') 필요
    """
    product_name = serializers.CharField(source='product.name', read_only=True)
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_name', 'quantity', 'unit_price', 'subtotal']


class OrderItemCreateSerializer(serializers.Serializer):
    """
    주문 생성 시 아이템 입력용
    """
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)


# ============= Order Serializers =============

class OrderListSerializer(serializers.ModelSerializer):
    """
    주문 목록용 (간단)
    """
    class Meta:
        model = Order
        fields = ['id', 'user_id', 'status', 'total_price', 'created_at', 'updated_at']


class OrderDetailSerializer(serializers.ModelSerializer):
    """
    주문 상세용 (아이템 포함)
    """
    items = OrderItemDetailSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'user_id', 'status', 'total_price', 'items', 'created_at', 'updated_at']


class OrderCreateSerializer(serializers.Serializer):
    """
    주문 생성 요청용
    """
    user_id = serializers.IntegerField()
    items = OrderItemCreateSerializer(many=True)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("최소 1개 이상의 상품이 필요합니다.")
        return value


class OrderStatusUpdateSerializer(serializers.Serializer):
    """
    주문 상태 업데이트용
    """
    status = serializers.ChoiceField(choices=Order.STATUS_CHOICES)


class BulkOrderCreateSerializer(serializers.Serializer):
    """
    벌크 주문 생성용
    """
    orders = OrderCreateSerializer(many=True)

    def validate_orders(self, value):
        if len(value) > 1000:
            raise serializers.ValidationError("한 번에 최대 1000개까지 생성 가능합니다.")
        return value


# ============= Inventory Serializer =============

class InventoryReserveSerializer(serializers.Serializer):
    """
    재고 예약 요청용
    """
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)


# ============= Stats Serializer =============

class TopProductSerializer(serializers.Serializer):
    """
    인기 상품 통계용
    """
    product_id = serializers.IntegerField()
    product_name = serializers.CharField()
    total_quantity = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    order_count = serializers.IntegerField()
