from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator


class Product(models.Model):
    """
    상품 모델 - 성능 테스트의 핵심 읽기 대상
    """
    CATEGORY_CHOICES = [
        ('electronics', 'Electronics'),
        ('clothing', 'Clothing'),
        ('food', 'Food'),
        ('books', 'Books'),
        ('home', 'Home & Garden'),
    ]

    name = models.CharField(max_length=200, db_index=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, db_index=True)
    stock = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, db_index=True)
    description = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['category', 'price']),  # 복합 인덱스: 카테고리별 가격 필터링
            models.Index(fields=['updated_at', 'stock']),  # 최근 업데이트 + 재고 조회
            models.Index(fields=['name']),  # 텍스트 검색용
        ]

    def __str__(self):
        return self.name


class Order(models.Model):
    """
    주문 모델 - 트랜잭션 테스트 대상
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]

    user_id = models.IntegerField(db_index=True)  # 간소화를 위해 FK 대신 int 사용
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True)
    total_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user_id', 'status']),  # 사용자별 주문 상태 조회
            models.Index(fields=['created_at', 'total_price']),  # 기간별 매출 집계
        ]

    def __str__(self):
        return f"Order {self.id} - {self.status}"


class OrderItem(models.Model):
    """
    주문 아이템 - 조인 성능 테스트 대상
    """
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='order_items')
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)  # 주문 시점 가격 저장

    class Meta:
        indexes = [
            models.Index(fields=['order', 'product']),
        ]

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

    @property
    def subtotal(self):
        return self.quantity * self.unit_price


class Review(models.Model):
    """
    리뷰 모델 - N+1 쿼리 테스트 대상
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user_id = models.IntegerField(db_index=True)  # 간소화를 위해 FK 대신 int 사용
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['product', 'rating']),  # 상품별 평점 조회
            models.Index(fields=['user_id', 'created_at']),  # 사용자별 리뷰 이력
        ]

    def __str__(self):
        return f"Review by User {self.user_id} - {self.rating}/5"
