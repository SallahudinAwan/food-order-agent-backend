import logging
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Cart, CartItem, Product
from .agent import AgentConfigurationError, AgentProviderError, AgentRequestError, run_ordering_agent
from .serializers import AgentMessageSerializer, AddCartItemSerializer, CustomerSerializer, ProductSerializer, SessionSerializer, SpeechSerializer, UpdateCartItemSerializer
from .services import add_item, place_order, serialize_cart, serialize_customer_orders
from .speech import synthesize_speech

logger = logging.getLogger(__name__)

@api_view(["GET"])
def menu(request):
    products = Product.objects.all()
    if request.query_params.get("include_unavailable", "false").lower() != "true": products = products.filter(is_available=True)
    if query := request.query_params.get("q", "").strip():
        products = products.filter(Q(name__icontains=query) | Q(description__icontains=query) | Q(category__icontains=query))
    return Response(ProductSerializer(products.order_by("name"), many=True).data)

@api_view(["GET", "DELETE"])
def cart_detail(request):
    session_id = request.query_params.get("session_id", "").strip()
    if not session_id: return Response({"session_id": ["This query parameter is required."]}, status=400)
    cart, _ = Cart.objects.get_or_create(session_id=session_id)
    if request.method == "DELETE":
        cart.items.all().delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    return Response(serialize_cart(cart))

@api_view(["POST"])
def cart_items(request):
    serializer = AddCartItemSerializer(data=request.data); serializer.is_valid(raise_exception=True)
    cart = add_item(**serializer.validated_data)
    return Response(serialize_cart(cart), status=status.HTTP_201_CREATED)

@api_view(["PATCH", "DELETE"])
def cart_item_detail(request, pk: int):
    item = get_object_or_404(CartItem.objects.select_related("cart"), pk=pk)
    cart = item.cart
    if request.method == "DELETE":
        item.delete(); return Response(status=status.HTTP_204_NO_CONTENT)
    serializer = UpdateCartItemSerializer(data=request.data); serializer.is_valid(raise_exception=True)
    item.quantity = serializer.validated_data["quantity"]; item.full_clean(); item.save()
    return Response(serialize_cart(cart))

@api_view(["POST"])
def order_place(request):
    serializer = SessionSerializer(data=request.data); serializer.is_valid(raise_exception=True)
    order = place_order(**serializer.validated_data)
    return Response({"success": True, "order_number": order.order_number, "status": order.status, "total": f"{order.total:.2f}"}, status=201)

@api_view(["GET"])
def order_history(request):
    serializer = CustomerSerializer(data=request.query_params)
    serializer.is_valid(raise_exception=True)
    return Response(serialize_customer_orders(serializer.validated_data["customer_id"]))

@api_view(["POST"])
def agent_message(request):
    serializer = AgentMessageSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
        result = run_ordering_agent(**serializer.validated_data)
    except AgentRequestError as error:
        return Response({"detail": str(error)}, status=status.HTTP_400_BAD_REQUEST)
    except AgentConfigurationError as error:
        return Response({"detail": str(error)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    except AgentProviderError:
        logger.exception("Backend ordering agent request failed")
        return Response({"detail": "I could not process your order right now. Please try again."}, status=status.HTTP_502_BAD_GATEWAY)
    return Response(result)

@api_view(["POST"])
def speech(request):
    serializer = SpeechSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
        audio = synthesize_speech(**serializer.validated_data)
    except Exception:
        logger.exception("Speech synthesis request failed")
        return Response({"detail": "Urdu speech is temporarily unavailable."}, status=status.HTTP_502_BAD_GATEWAY)
    response = HttpResponse(audio, content_type="audio/mpeg")
    response["Cache-Control"] = "no-store"
    return response
