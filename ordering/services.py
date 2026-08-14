from decimal import Decimal
from django.db import transaction
from rest_framework.exceptions import ValidationError
from .models import Cart, CartItem, Order, OrderItem, Product

def serialize_cart(cart: Cart) -> dict:
    items, subtotal = [], Decimal("0.00")
    for item in cart.items.select_related("product").order_by("id"):
        line_total = item.product.price * item.quantity
        subtotal += line_total
        items.append({"id": item.id, "product_id": item.product_id, "name": item.product.name, "quantity": item.quantity,
                      "unit_price": f"{item.product.price:.2f}", "line_total": f"{line_total:.2f}"})
    return {"id": cart.id, "session_id": cart.session_id, "items": items, "subtotal": f"{subtotal:.2f}", "total": f"{subtotal:.2f}"}

def serialize_order(order: Order) -> dict:
    return {
        "order_number": order.order_number,
        "status": order.status,
        "total": f"{order.total:.2f}",
        "created_at": order.created_at.isoformat(),
        "items": [
            {
                "name": item.product_name,
                "quantity": item.quantity,
                "unit_price": f"{item.unit_price:.2f}",
                "line_total": f"{item.line_total:.2f}",
            }
            for item in order.items.all()
        ],
    }

def serialize_customer_orders(customer_id: str) -> list[dict]:
    orders = Order.objects.filter(customer_id=customer_id).prefetch_related("items").order_by("-created_at")
    return [serialize_order(order) for order in orders]

@transaction.atomic
def add_item(session_id: str, product_id: int, quantity: int) -> Cart:
    try: product = Product.objects.select_for_update().get(pk=product_id)
    except Product.DoesNotExist: raise ValidationError({"product_id": "Product does not exist."})
    if not product.is_available: raise ValidationError({"product_id": "Product is currently unavailable."})
    cart, _ = Cart.objects.get_or_create(session_id=session_id)
    item, created = CartItem.objects.select_for_update().get_or_create(cart=cart, product=product, defaults={"quantity": quantity})
    if not created:
        item.quantity += quantity
        item.full_clean()
        item.save(update_fields=["quantity", "updated_at"])
    return cart

@transaction.atomic
def place_order(session_id: str, customer_id: str = "") -> Order:
    existing = Order.objects.filter(source_session_id=session_id).first()
    if existing:
        if customer_id and not existing.customer_id:
            existing.customer_id = customer_id
            existing.save(update_fields=["customer_id"])
        return existing
    try: cart = Cart.objects.select_for_update().get(session_id=session_id)
    except Cart.DoesNotExist: raise ValidationError({"session_id": "Cart is empty."})
    cart_items = list(cart.items.select_related("product").select_for_update())
    if not cart_items: raise ValidationError({"session_id": "Cart is empty."})
    product_ids = [item.product_id for item in cart_items]
    products = {p.id: p for p in Product.objects.select_for_update().filter(id__in=product_ids)}
    if len(products) != len(product_ids): raise ValidationError("One or more products no longer exist.")
    total = Decimal("0.00")
    for item in cart_items:
        if not products[item.product_id].is_available:
            raise ValidationError({"product": f"{products[item.product_id].name} is currently unavailable."})
        total += products[item.product_id].price * item.quantity
    order = Order.objects.create(status=Order.Status.CONFIRMED, total=total, source_session_id=session_id, customer_id=customer_id)
    OrderItem.objects.bulk_create([OrderItem(order=order, product=p, product_name=p.name, quantity=item.quantity,
        unit_price=p.price, line_total=p.price * item.quantity) for item in cart_items for p in [products[item.product_id]]])
    cart.delete()
    return order
