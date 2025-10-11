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
        기본적으로 최적화 적용 (annotate로 review_count, average_rating 계산)
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

        # 상세 조회 시 리뷰 통계를 DB에서 계산 (N+1 방지)
        if self.action == 'retrieve':
            queryset = queryset.annotate(
                review_count=Count('reviews'),
                average_rating=Avg('reviews__rating')
            )

        return queryset

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ProductDetailSerializer
        return ProductListSerializer

    @action(detail=True, methods=['get'])
    def reviews(self, request, pk=None):
        """
        3. GET /products/{id}/reviews
        Level B-C: 기본적으로 최적화 적용 (select_related)
        """
        product = self.get_object()
        # 기본적으로 select_related 적용하여 N+1 방지
        reviews = product.reviews.select_related('product').all()
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

        # 최적화: 상세 조회 시 items와 product를 기본적으로 prefetch (N+1 방지)
        if self.action == 'retrieve':
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
        Level C: 트랜잭션 + 다건 insert + 재고 차감 (최적화됨)
        - in_bulk()로 상품 일괄 조회
        - bulk_update()로 재고 일괄 업데이트
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_id = serializer.validated_data['user_id']
        items_data = serializer.validated_data['items']

        # 1. 모든 상품을 한 번에 조회 (N번 쿼리 → 1번 쿼리)
        product_ids = [item['product_id'] for item in items_data]
        products = Product.objects.in_bulk(product_ids)

        # 존재하지 않는 상품 확인
        for product_id in product_ids:
            if product_id not in products:
                return Response(
                    {'error': f'상품 ID {product_id}를 찾을 수 없습니다.'},
                    status=status.HTTP_404_NOT_FOUND
                )

        # 2. 주문 생성
        order = Order.objects.create(user_id=user_id, total_price=0)
        total_price = Decimal('0.00')

        # 3. 주문 아이템 생성 준비 + 재고 확인
        order_items = []
        products_to_update = []

        for item_data in items_data:
            product = products[item_data['product_id']]

            # 재고 확인
            if product.stock < item_data['quantity']:
                raise ValueError(f"재고 부족: {product.name}")

            # 재고 차감 준비
            product.stock -= item_data['quantity']
            products_to_update.append(product)

            # 주문 아이템 생성 준비
            order_item = OrderItem(
                order=order,
                product=product,
                quantity=item_data['quantity'],
                unit_price=product.price
            )
            order_items.append(order_item)
            total_price += product.price * item_data['quantity']

        # 4. 벌크 업데이트 (N번 UPDATE → 1번 UPDATE)
        Product.objects.bulk_update(products_to_update, ['stock'])

        # 5. 주문 아이템 벌크 생성
        OrderItem.objects.bulk_create(order_items)

        # 6. 총액 업데이트
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
    Level C: 벌크 인서트 성능 테스트 (대폭 최적화됨)
    - 모든 상품을 한 번에 조회 (600번 → 1번)
    - bulk_create/bulk_update 활용
    """
    serializer = BulkOrderCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    orders_data = serializer.validated_data['orders']

    # 1. 모든 상품 ID를 수집하여 한 번에 조회 (최적화 핵심!)
    all_product_ids = set()
    for order_data in orders_data:
        for item_data in order_data['items']:
            all_product_ids.add(item_data['product_id'])

    products = Product.objects.in_bulk(list(all_product_ids))

    # 존재하지 않는 상품 확인
    for product_id in all_product_ids:
        if product_id not in products:
            return Response(
                {'error': f'상품 ID {product_id}를 찾을 수 없습니다.'},
                status=status.HTTP_404_NOT_FOUND
            )

    # 2. 주문 및 아이템 생성 준비
    orders_to_create = []
    order_items_to_create = []
    product_stock_changes = {}  # product_id -> 차감량

    for order_data in orders_data:
        user_id = order_data['user_id']
        items_data = order_data['items']
        total_price = Decimal('0.00')

        # 주문 객체 생성 (아직 DB에 저장 안함)
        order = Order(user_id=user_id, total_price=0)
        orders_to_create.append(order)

        # 주문 아이템 준비 (order는 나중에 연결)
        order_item_info = []
        for item_data in items_data:
            product = products[item_data['product_id']]
            quantity = item_data['quantity']

            # 재고 확인
            current_deduction = product_stock_changes.get(product.id, 0)
            if product.stock - current_deduction < quantity:
                raise ValueError(f"재고 부족: {product.name}")

            # 재고 차감량 누적
            product_stock_changes[product.id] = current_deduction + quantity

            # 주문 아이템 정보 저장 (order 연결은 나중에)
            order_item_info.append({
                'product': product,
                'quantity': quantity,
                'unit_price': product.price
            })
            total_price += product.price * quantity

        order.total_price = total_price
        # order와 연결할 아이템 정보 저장
        order._items_info = order_item_info

    # 3. 주문 벌크 생성 (N번 INSERT → 1번 INSERT)
    Order.objects.bulk_create(orders_to_create)

    # 4. 주문 아이템 생성 (order.id가 할당된 후)
    for order in orders_to_create:
        for item_info in order._items_info:
            order_item = OrderItem(
                order=order,
                product=item_info['product'],
                quantity=item_info['quantity'],
                unit_price=item_info['unit_price']
            )
            order_items_to_create.append(order_item)

    # 5. 주문 아이템 벌크 생성
    OrderItem.objects.bulk_create(order_items_to_create)

    # 6. 재고 벌크 업데이트 (N번 UPDATE → 1번 UPDATE)
    products_to_update = []
    for product_id, deduction in product_stock_changes.items():
        product = products[product_id]
        product.stock -= deduction
        products_to_update.append(product)

    Product.objects.bulk_update(products_to_update, ['stock'])

    return Response(
        {'created': len(orders_to_create), 'order_ids': [o.id for o in orders_to_create]},
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

        # 최적화: 목록 조회 시 기본적으로 select_related 적용 (N+1 방지)
        if self.action == 'list':
            queryset = queryset.select_related('product')

        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return ReviewListSerializer
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
