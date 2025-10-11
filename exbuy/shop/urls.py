from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Router for ViewSets
router = DefaultRouter()
router.register(r'products', views.ProductViewSet, basename='product')
router.register(r'orders', views.OrderViewSet, basename='order')
router.register(r'reviews', views.ReviewViewSet, basename='review')

urlpatterns = [
    # 1. Health check
    path('health', views.health_check, name='health-check'),

    # 2-4. Products (via router)
    # GET /products - 목록
    # GET /products/{id} - 상세
    # GET /products/{id}/reviews - 상품별 리뷰
    # DELETE /products/{id} - 삭제 (admin)

    # 5. Product search
    path('search/products', views.search_products, name='product-search'),

    # 6-8. Orders (via router)
    # POST /orders - 생성
    # GET /orders/{id} - 상세
    # PATCH /orders/{id} - 상태 업데이트

    # 9. Bulk order creation
    path('orders/bulk', views.bulk_create_orders, name='order-bulk-create'),

    # 10. Inventory reservation
    path('inventory/reserve', views.reserve_inventory, name='inventory-reserve'),

    # 11. Top products stats
    path('stats/top-products', views.top_products, name='stats-top-products'),

    # 12-13. Reviews (via router)
    # POST /reviews - 생성
    # GET /reviews - 목록

    # 14. File upload
    path('uploads', views.FileUploadView.as_view(), name='file-upload'),

    # Include router URLs
    path('', include(router.urls)),
]
