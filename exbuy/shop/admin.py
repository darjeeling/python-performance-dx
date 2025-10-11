from django.contrib import admin
from .models import Product, Order, OrderItem, Review


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'price', 'stock', 'category', 'updated_at']
    list_filter = ['category', 'updated_at']
    search_fields = ['name', 'description']
    ordering = ['-updated_at']


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['subtotal']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'user_id', 'status', 'total_price', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['user_id']
    ordering = ['-created_at']
    inlines = [OrderItemInline]


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['id', 'order', 'product', 'quantity', 'unit_price', 'subtotal']
    list_filter = ['order__status']
    search_fields = ['product__name']


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['id', 'product', 'user_id', 'rating', 'created_at']
    list_filter = ['rating', 'created_at']
    search_fields = ['product__name', 'body']
    ordering = ['-created_at']
