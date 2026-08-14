from django.urls import path
from . import views

urlpatterns = [
    path("menu/", views.menu), path("cart/", views.cart_detail), path("cart/items/", views.cart_items),
    path("cart/items/<int:pk>/", views.cart_item_detail), path("orders/", views.order_history),
    path("orders/place/", views.order_place),
    path("agent/message/", views.agent_message),
    path("speech/", views.speech),
]
