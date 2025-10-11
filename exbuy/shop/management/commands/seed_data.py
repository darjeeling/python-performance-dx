from django.core.management.base import BaseCommand
from django.db import transaction
from faker import Faker
import random
from decimal import Decimal
from shop.models import Product, Order, OrderItem, Review

fake = Faker()


class Command(BaseCommand):
    help = '성능 테스트용 대량 데이터 생성'

    def add_arguments(self, parser):
        parser.add_argument(
            '--products',
            type=int,
            default=10000,
            help='생성할 상품 수 (기본: 10000)'
        )
        parser.add_argument(
            '--orders',
            type=int,
            default=50000,
            help='생성할 주문 수 (기본: 50000)'
        )
        parser.add_argument(
            '--reviews',
            type=int,
            default=100000,
            help='생성할 리뷰 수 (기본: 100000)'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='배치 크기 (기본: 1000)'
        )

    def handle(self, *args, **options):
        products_count = options['products']
        orders_count = options['orders']
        reviews_count = options['reviews']
        batch_size = options['batch_size']

        self.stdout.write(self.style.WARNING('기존 데이터 삭제 중...'))
        Review.objects.all().delete()
        OrderItem.objects.all().delete()
        Order.objects.all().delete()
        Product.objects.all().delete()

        self.stdout.write(self.style.SUCCESS('✓ 기존 데이터 삭제 완료'))

        # 1. 상품 생성
        self.stdout.write(f'상품 {products_count}개 생성 중...')
        self._create_products(products_count, batch_size)
        self.stdout.write(self.style.SUCCESS(f'✓ 상품 {products_count}개 생성 완료'))

        # 2. 주문 생성
        self.stdout.write(f'주문 {orders_count}개 생성 중...')
        self._create_orders(orders_count, batch_size)
        self.stdout.write(self.style.SUCCESS(f'✓ 주문 {orders_count}개 생성 완료'))

        # 3. 리뷰 생성
        self.stdout.write(f'리뷰 {reviews_count}개 생성 중...')
        self._create_reviews(reviews_count, batch_size)
        self.stdout.write(self.style.SUCCESS(f'✓ 리뷰 {reviews_count}개 생성 완료'))

        self.stdout.write(self.style.SUCCESS('\n=== 데이터 생성 완료 ==='))
        self.stdout.write(f'상품: {Product.objects.count()}')
        self.stdout.write(f'주문: {Order.objects.count()}')
        self.stdout.write(f'주문 아이템: {OrderItem.objects.count()}')
        self.stdout.write(f'리뷰: {Review.objects.count()}')

    @transaction.atomic
    def _create_products(self, count, batch_size):
        """상품 대량 생성"""
        categories = ['electronics', 'clothing', 'food', 'books', 'home']
        products = []

        for i in range(count):
            products.append(Product(
                name=fake.catch_phrase()[:200],
                price=Decimal(str(random.uniform(10, 1000))).quantize(Decimal('0.01')),
                stock=random.randint(0, 1000),
                category=random.choice(categories),
                description=fake.text(200),
            ))

            if (i + 1) % batch_size == 0:
                Product.objects.bulk_create(products)
                products = []
                self.stdout.write(f'  → {i + 1}/{count} 완료', ending='\r')

        if products:
            Product.objects.bulk_create(products)

        self.stdout.write('')  # 줄바꿈

    @transaction.atomic
    def _create_orders(self, count, batch_size):
        """주문 및 주문 아이템 대량 생성"""
        products = list(Product.objects.all())
        product_count = len(products)

        if product_count == 0:
            self.stdout.write(self.style.ERROR('상품이 없습니다. 먼저 상품을 생성하세요.'))
            return

        for i in range(count):
            # 주문 생성
            order = Order.objects.create(
                user_id=random.randint(1, 10000),
                status=random.choice(['pending', 'processing', 'shipped', 'delivered']),
                total_price=Decimal('0.00')
            )

            # 주문 아이템 생성 (1-5개)
            order_items = []
            total_price = Decimal('0.00')
            items_count = random.randint(1, 5)

            for _ in range(items_count):
                product = random.choice(products)
                quantity = random.randint(1, 10)
                unit_price = product.price

                order_items.append(OrderItem(
                    order=order,
                    product=product,
                    quantity=quantity,
                    unit_price=unit_price
                ))
                total_price += unit_price * quantity

            OrderItem.objects.bulk_create(order_items)

            # 총액 업데이트
            order.total_price = total_price
            order.save()

            if (i + 1) % 100 == 0:
                self.stdout.write(f'  → {i + 1}/{count} 완료', ending='\r')

        self.stdout.write('')  # 줄바꿈

    @transaction.atomic
    def _create_reviews(self, count, batch_size):
        """리뷰 대량 생성"""
        products = list(Product.objects.all())
        product_count = len(products)

        if product_count == 0:
            self.stdout.write(self.style.ERROR('상품이 없습니다. 먼저 상품을 생성하세요.'))
            return

        reviews = []

        for i in range(count):
            reviews.append(Review(
                product=random.choice(products),
                user_id=random.randint(1, 10000),
                rating=random.randint(1, 5),
                body=fake.text(200)
            ))

            if (i + 1) % batch_size == 0:
                Review.objects.bulk_create(reviews)
                reviews = []
                self.stdout.write(f'  → {i + 1}/{count} 완료', ending='\r')

        if reviews:
            Review.objects.bulk_create(reviews)

        self.stdout.write('')  # 줄바꿈
