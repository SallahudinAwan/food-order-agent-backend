from django.contrib import admin
from .models import Cart, CartItem, Order, OrderItem, Product

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price", "is_available", "updated_at")
    list_filter = ("category", "is_available")
    search_fields = ("name", "description")

class CartItemInline(admin.TabularInline): model = CartItem; extra = 0
@admin.register(Cart)
class CartAdmin(admin.ModelAdmin): list_display = ("session_id", "updated_at"); inlines = [CartItemInline]
admin.site.register(CartItem)

class OrderItemInline(admin.TabularInline): model = OrderItem; extra = 0; readonly_fields = ("product", "product_name", "quantity", "unit_price", "line_total")
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin): list_display = ("order_number", "status", "total", "customer_id", "created_at"); list_filter = ("status",); search_fields = ("order_number", "source_session_id", "customer_id"); inlines = [OrderItemInline]
admin.site.register(OrderItem)
