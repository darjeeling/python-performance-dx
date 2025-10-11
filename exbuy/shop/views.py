from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import F, Sum, Count, Q, Avg
from rest_framework import status, viewsets
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from decimal import Decimal

from .models import Product, Order, OrderItem, Review
from .serializers import (
    ProductListSerializer, ProductDetailSerializer, ProductDetailOptimizedSerializer,
    ReviewSerializer, ReviewListSerializer, ReviewListOptimizedSerializer,
    OrderListSerializer, OrderDetailSerializer, OrderCreateSerializer,
    OrderStatusUpdateSerializer, BulkOrderCreateSerializer,
    InventoryReserveSerializer, TopProductSerializer,
    OrderItemSerializer
)


# =============== 1. Health Check ===============
@api_view(['GET'])
def health_check(request):
    """
    Level A: 가장 간단한 헬스체크
    """
    return Response({'status': 'ok'}, status=status.HTTP_200_OK)


# =============== 2-5. Product Views ===============
class ProductViewSet(viewsets.ModelViewSet):
    """
    상품 CRUD - 읽기 중심 성능 테스트용
    """
    queryset = Product.objects.all()
    serializer_class = ProductListSerializer

    def get_queryset(self):
        """
        Level B: 필터링, 정렬, 페이지네이션
        ?category=electronics&min_price=100&max_price=1000&ordering=-price
        ?optimize=true (prefetch_related 적용)
        """
        queryset = Product.objects.all()

        # 필터링
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)

        min_price = self.request.query_params.get('min_price')
        if min_price:
            queryset = queryset.filter(price__gte=min_price)

        max_price = self.request.query_params.get('max_price')
        if max_price:
            queryset = queryset.filter(price__lte=max_price)

        # 검색
        q = self.request.query_params.get('q')
        if q:
            queryset = queryset.filter(Q(name__icontains=q) | Q(description__icontains=q))

        # 정렬
        ordering = self.request.query_params.get('ordering', '-created_at')
        queryset = queryset.order_by(ordering)

        # 최적화 옵션
        optimize = self.request.query_params.get('optimize', 'false').lower() == 'true'
        if optimize and self.action == 'retrieve':
            queryset = queryset.prefetch_related('reviews')

        return queryset

    def get_serializer_class(self):
        if self.action == 'retrieve':
            optimize = self.request.query_params.get('optimize', 'false').lower() == 'true'
            return ProductDetailOptimizedSerializer if optimize else ProductDetailSerializer
        return ProductListSerializer

    @action(detail=True, methods=['get'])
    def reviews(self, request, pk=None):
        """
        3. GET /products/{id}/reviews
        Level B-C: N+1 쿼리 테스트
        ?optimize=true (select_related 적용)
        """
        product = self.get_object()
        optimize = request.query_params.get('optimize', 'false').lower() == 'true'

        if optimize:
            reviews = product.reviews.select_related('product').all()
            serializer = ReviewListOptimizedSerializer(reviews, many=True)
        else:
            reviews = product.reviews.all()
            serializer = ReviewListSerializer(reviews, many=True)

        return Response(serializer.data)


@api_view(['GET'])
def search_products(request):
    """
    5. GET /search/products
    Level B: 텍스트 검색 + 복합 필터
    ?q=laptop&category=electronics&min_price=500
    """
    queryset = Product.objects.all()

    q = request.query_params.get('q', '')
    if q:
        queryset = queryset.filter(
            Q(name__icontains=q) | Q(description__icontains=q)
        )

    category = request.query_params.get('category')
    if category:
        queryset = queryset.filter(category=category)

    min_price = request.query_params.get('min_price')
    if min_price:
        queryset = queryset.filter(price__gte=min_price)

    max_price = request.query_params.get('max_price')
    if max_price:
        queryset = queryset.filter(price__lte=max_price)

    in_stock = request.query_params.get('in_stock')
    if in_stock == 'true':
        queryset = queryset.filter(stock__gt=0)

    serializer = ProductListSerializer(queryset, many=True)
    return Response(serializer.data)


# =============== 6-9. Order Views ===============
class OrderViewSet(viewsets.ModelViewSet):
    """
    주문 관리 - 쓰기/트랜잭션 테스트용
    """
    queryset = Order.objects.all()
    serializer_class = OrderListSerializer

    def get_queryset(self):
        queryset = Order.objects.all()

        # 최적화: 상세 조회 시 items와 product를 prefetch
        if self.action == 'retrieve':
            optimize = self.request.query_params.get('optimize', 'false').lower() == 'true'
            if optimize:
                queryset = queryset.prefetch_related('items__product')

        return queryset

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return OrderDetailSerializer
        elif self.action == 'create':
            return OrderCreateSerializer
        elif self.action == 'partial_update':
            return OrderStatusUpdateSerializer
        return OrderListSerializer

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """
        6. POST /orders
        Level C: 트랜잭션 + 다건 insert + 재고 차감
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_id = serializer.validated_data['user_id']
        items_data = serializer.validated_data['items']

        # 주문 생성
        order = Order.objects.create(user_id=user_id, total_price=0)
        total_price = Decimal('0.00')

        # 주문 아이템 생성 + 재고 차감
        order_items = []
        for item_data in items_data:
            product = get_object_or_404(Product, id=item_data['product_id'])

            # 재고 확인
            if product.stock < item_data['quantity']:
                raise ValueError(f"재고 부족: {product.name}")

            # 재고 차감
            product.stock -= item_data['quantity']
            product.save()

            # 주문 아이템 생성
            order_item = OrderItem(
                order=order,
                product=product,
                quantity=item_data['quantity'],
                unit_price=product.price
            )
            order_items.append(order_item)
            total_price += product.price * item_data['quantity']

        OrderItem.objects.bulk_create(order_items)

        # 총액 업데이트
        order.total_price = total_price
        order.save()

        return Response(
            OrderDetailSerializer(order).data,
            status=status.HTTP_201_CREATED
        )

    def partial_update(self, request, *args, **kwargs):
        """
        8. PATCH /orders/{id}
        Level A: 단순 상태 업데이트
        """
        order = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        order.status = serializer.validated_data['status']
        order.save()

        return Response(OrderDetailSerializer(order).data)


@api_view(['POST'])
@transaction.atomic
def bulk_create_orders(request):
    """
    9. POST /orders/bulk
    Level C: 벌크 인서트 성능 테스트
    """
    serializer = BulkOrderCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    orders_data = serializer.validated_data['orders']
    created_orders = []

    for order_data in orders_data:
        user_id = order_data['user_id']
        items_data = order_data['items']

        # 주문 생성
        order = Order.objects.create(user_id=user_id, total_price=0)
        total_price = Decimal('0.00')

        # 주문 아이템 생성
        order_items = []
        for item_data in items_data:
            product = get_object_or_404(Product, id=item_data['product_id'])

            if product.stock < item_data['quantity']:
                raise ValueError(f"재고 부족: {product.name}")

            product.stock -= item_data['quantity']
            product.save()

            order_item = OrderItem(
                order=order,
                product=product,
                quantity=item_data['quantity'],
                unit_price=product.price
            )
            order_items.append(order_item)
            total_price += product.price * item_data['quantity']

        OrderItem.objects.bulk_create(order_items)
        order.total_price = total_price
        order.save()

        created_orders.append(order)

    return Response(
        {'created': len(created_orders), 'order_ids': [o.id for o in created_orders]},
        status=status.HTTP_201_CREATED
    )


# =============== 10. Inventory ===============
@api_view(['POST'])
@transaction.atomic
def reserve_inventory(request):
    """
    10. POST /inventory/reserve
    Level C: 동시성 제어 (낙관적/비관적 락 테스트)
    ?lock_type=optimistic|pessimistic
    """
    serializer = InventoryReserveSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    product_id = serializer.validated_data['product_id']
    quantity = serializer.validated_data['quantity']
    lock_type = request.query_params.get('lock_type', 'optimistic')

    if lock_type == 'pessimistic':
        # 비관적 락 (SELECT FOR UPDATE)
        product = Product.objects.select_for_update().get(id=product_id)
    else:
        # 낙관적 락 (F() 사용)
        product = Product.objects.get(id=product_id)

    if product.stock < quantity:
        return Response(
            {'error': '재고 부족'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if lock_type == 'pessimistic':
        product.stock -= quantity
        product.save()
    else:
        # F()를 사용한 원자적 업데이트
        Product.objects.filter(id=product_id).update(stock=F('stock') - quantity)
        product.refresh_from_db()

    return Response({
        'product_id': product.id,
        'reserved': quantity,
        'remaining_stock': product.stock
    })


# =============== 11. Stats ===============
@api_view(['GET'])
def top_products(request):
    """
    11. GET /stats/top-products
    Level C: 집계 쿼리 (GROUP BY, JOIN)
    ?limit=10
    """
    limit = int(request.query_params.get('limit', 10))

    # 상품별 판매 통계
    stats = OrderItem.objects.values(
        'product_id',
        'product__name'
    ).annotate(
        total_quantity=Sum('quantity'),
        total_revenue=Sum(F('quantity') * F('unit_price')),
        order_count=Count('order', distinct=True)
    ).order_by('-total_revenue')[:limit]

    serializer = TopProductSerializer(stats, many=True, context={
        'product_id': 'product_id',
        'product_name': 'product__name'
    })

    # 수동으로 필드 매핑
    result = []
    for item in stats:
        result.append({
            'product_id': item['product_id'],
            'product_name': item['product__name'],
            'total_quantity': item['total_quantity'],
            'total_revenue': item['total_revenue'],
            'order_count': item['order_count']
        })

    return Response(result)


# =============== 12-13. Review Views ===============
class ReviewViewSet(viewsets.ModelViewSet):
    """
    리뷰 관리
    """
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer

    def get_queryset(self):
        queryset = Review.objects.all()

        # 상품별 필터
        product_id = self.request.query_params.get('product_id')
        if product_id:
            queryset = queryset.filter(product_id=product_id)

        # 사용자별 필터
        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        # 최적화 옵션
        optimize = self.request.query_params.get('optimize', 'false').lower() == 'true'
        if optimize:
            queryset = queryset.select_related('product')

        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            optimize = self.request.query_params.get('optimize', 'false').lower() == 'true'
            return ReviewListOptimizedSerializer if optimize else ReviewListSerializer
        return ReviewSerializer


# =============== 14. File Upload ===============
class FileUploadView(APIView):
    """
    14. POST /uploads
    Level A-B: 파일 업로드 I/O 테스트
    """
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, format=None):
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response(
                {'error': '파일이 제공되지 않았습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 파일 크기 및 타입 검증
        max_size = 10 * 1024 * 1024  # 10MB
        if file_obj.size > max_size:
            return Response(
                {'error': '파일 크기는 10MB 이하여야 합니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 실제로는 파일을 저장하지 않고 메타데이터만 반환 (성능 테스트용)
        return Response({
            'filename': file_obj.name,
            'size': file_obj.size,
            'content_type': file_obj.content_type,
            'status': 'uploaded'
        }, status=status.HTTP_201_CREATED)
