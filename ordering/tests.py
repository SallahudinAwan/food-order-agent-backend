from decimal import Decimal
import os
from unittest.mock import patch
from google.genai import types
from django.urls import reverse
from rest_framework.test import APITestCase
from .agent import OrderingToolbox, SYSTEM_PROMPT, _is_explicit_confirmation, format_display_reply, format_speech_reply, run_ordering_agent
from .models import AgentConversation, Cart, CartItem, Order, Product

class OrderingApiTests(APITestCase):
    def setUp(self):
        self.zinger = Product.objects.create(name="Zinger Burger", description="Crispy", price=Decimal("650.00"), category="Burgers")
        self.fries = Product.objects.create(name="French Fries", description="Golden", price=Decimal("300.00"), category="Sides")
        self.unavailable = Product.objects.create(name="BBQ Pizza", price=Decimal("1300.00"), category="Pizza", is_available=False)
        self.session_id = "test-session"
        self.customer_id = "test-customer"

    def add(self, product=None, quantity=1, session_id=None):
        return self.client.post("/api/cart/items/", {"session_id": session_id or self.session_id, "product_id": (product or self.zinger).id, "quantity": quantity}, format="json")

    def test_search_menu_is_case_insensitive_and_hides_unavailable(self):
        response = self.client.get("/api/menu/?q=ZINGER")
        self.assertEqual(response.status_code, 200); self.assertEqual([p["name"] for p in response.data], ["Zinger Burger"])
        self.assertEqual(self.client.get("/api/menu/?q=BBQ").data, [])

    def test_add_product_and_merge_duplicate_rows(self):
        self.assertEqual(self.add(quantity=2).status_code, 201); self.add(quantity=1)
        item = CartItem.objects.get(); self.assertEqual(item.quantity, 3); self.assertEqual(CartItem.objects.count(), 1)

    def test_update_quantity(self):
        item_id = self.add().data["items"][0]["id"]
        response = self.client.patch(f"/api/cart/items/{item_id}/", {"quantity": 4}, format="json")
        self.assertEqual(response.status_code, 200); self.assertEqual(response.data["items"][0]["quantity"], 4)

    def test_remove_item(self):
        item_id = self.add().data["items"][0]["id"]
        self.assertEqual(self.client.delete(f"/api/cart/items/{item_id}/").status_code, 204); self.assertFalse(CartItem.objects.exists())

    def test_cart_total_is_server_calculated(self):
        self.add(quantity=2); self.add(product=self.fries, quantity=1)
        response = self.client.get(f"/api/cart/?session_id={self.session_id}")
        self.assertEqual(response.data["subtotal"], "1600.00"); self.assertEqual(response.data["total"], "1600.00")

    def test_reject_invalid_product(self): self.assertEqual(self.add(product=type("P", (), {"id": 99999})()).status_code, 400)
    def test_reject_unavailable_product(self): self.assertEqual(self.add(product=self.unavailable).status_code, 400)
    def test_reject_zero_and_negative_quantities(self):
        self.assertEqual(self.add(quantity=0).status_code, 400); self.assertEqual(self.add(quantity=-2).status_code, 400)

    def test_place_order_creates_snapshot_and_clears_cart(self):
        self.add(quantity=2); self.add(product=self.fries, quantity=1)
        response = self.client.post("/api/orders/place/", {"session_id": self.session_id}, format="json")
        self.assertEqual(response.status_code, 201); self.assertEqual(response.data["total"], "1600.00")
        order = Order.objects.get(); self.assertEqual(order.status, "confirmed"); self.assertRegex(order.order_number, r"^ORD-\d{7}$")
        burger_snapshot = order.items.get(product=self.zinger)
        self.assertEqual(burger_snapshot.unit_price, Decimal("650.00")); self.assertEqual(burger_snapshot.line_total, Decimal("1300.00"))
        self.assertFalse(Cart.objects.filter(session_id=self.session_id).exists())

    def test_order_uses_current_database_price(self):
        self.add(quantity=2); self.zinger.price = Decimal("700.00"); self.zinger.save()
        response = self.client.post("/api/orders/place/", {"session_id": self.session_id}, format="json")
        self.assertEqual(response.data["total"], "1400.00"); self.assertEqual(Order.objects.get().items.get().unit_price, Decimal("700.00"))

    def test_empty_cart_order_rejected(self):
        self.client.get(f"/api/cart/?session_id={self.session_id}")
        self.assertEqual(self.client.post("/api/orders/place/", {"session_id": self.session_id}, format="json").status_code, 400)

    def test_order_is_idempotent_for_same_session(self):
        self.add(); first = self.client.post("/api/orders/place/", {"session_id": self.session_id}, format="json")
        second = self.client.post("/api/orders/place/", {"session_id": self.session_id}, format="json")
        self.assertEqual(first.data["order_number"], second.data["order_number"]); self.assertEqual(Order.objects.count(), 1)

    def test_clear_cart(self):
        self.add(); response = self.client.delete(f"/api/cart/?session_id={self.session_id}")
        self.assertEqual(response.status_code, 204); self.assertFalse(CartItem.objects.exists())

    def test_agent_endpoint_requires_server_key(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": ""}):
            response = self.client.post(
                "/api/agent/message/",
                {"session_id": self.session_id, "customer_id": self.customer_id, "message": "Show me the menu"},
                format="json",
            )
        self.assertEqual(response.status_code, 503)

    @patch("ordering.views.run_ordering_agent")
    def test_agent_endpoint_returns_backend_agent_result(self, run_agent):
        run_agent.return_value = {
            "reply": "We offer Zinger Burger.",
            "speech_reply": "We offer Zinger Burger.",
            "products": [],
            "cart": {"items": [], "total": "0.00"},
            "orders": [],
            "order_placed": False,
            "tools_used": ["get_products"],
        }
        response = self.client.post(
            "/api/agent/message/",
            {"session_id": self.session_id, "customer_id": self.customer_id, "message": "What products do you have?"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["tools_used"], ["get_products"])
        run_agent.assert_called_once_with(session_id=self.session_id, customer_id=self.customer_id, message="What products do you have?")

    def test_python_tools_enforce_review_and_explicit_confirmation(self):
        conversation = AgentConversation.objects.create(session_id=self.session_id, customer_id=self.customer_id)
        toolbox = OrderingToolbox(conversation, self.customer_id, "Add one Zinger")
        toolbox.add_to_cart(self.zinger.id, 1)
        reviewed = toolbox.review_order()
        self.assertEqual(reviewed["total"], "650.00")

        unsafe = OrderingToolbox(conversation, self.customer_id, "maybe")
        with self.assertRaisesMessage(ValueError, "explicit confirmation"):
            unsafe.create_order()

        confirmed = OrderingToolbox(conversation, self.customer_id, "Yes, please")
        result = confirmed.create_order()
        self.assertTrue(result["success"])
        self.assertTrue(confirmed.order_placed)
        self.assertEqual(Order.objects.count(), 1)

        history = confirmed.get_orders()
        self.assertEqual(history[0]["order_number"], result["order_number"])
        self.assertEqual(history[0]["status"], "confirmed")

    def test_natural_english_and_urdu_confirmation_phrases(self):
        self.assertTrue(_is_explicit_confirmation("yes I confirm please play store"))
        self.assertTrue(_is_explicit_confirmation("yes place the order"))
        self.assertTrue(_is_explicit_confirmation("I confirm"))
        self.assertTrue(_is_explicit_confirmation("جی ہاں، آرڈر کر دیں"))
        self.assertTrue(_is_explicit_confirmation("G confirm kar de"))
        self.assertTrue(_is_explicit_confirmation("G confirm kar den aap order"))
        self.assertTrue(_is_explicit_confirmation("order final kar de"))
        self.assertFalse(_is_explicit_confirmation("Gmail ID confirm"))
        self.assertFalse(_is_explicit_confirmation("maybe place the order"))
        self.assertFalse(_is_explicit_confirmation("shayad order final kar de"))
        self.assertFalse(_is_explicit_confirmation("do not place the order"))
        self.assertFalse(_is_explicit_confirmation("can you confirm the total?"))

    @patch("ordering.agent.genai.Client")
    def test_confirmed_review_places_order_without_model_reinterpretation(self, client_class):
        conversation = AgentConversation.objects.create(session_id=self.session_id, customer_id=self.customer_id)
        toolbox = OrderingToolbox(conversation, self.customer_id, "Add one Zinger")
        toolbox.add_to_cart(self.zinger.id, 1)
        toolbox.review_order()

        with patch.dict(os.environ, {"GEMINI_API_KEY": "server-secret"}):
            result = run_ordering_agent(
                self.session_id,
                self.customer_id,
                "G confirm kar den aap order",
            )

        self.assertTrue(result["order_placed"])
        self.assertEqual(result["tools_used"], ["create_order"])
        self.assertIn("has been placed successfully", result["reply"])
        self.assertEqual(Order.objects.count(), 1)
        client_class.assert_not_called()

    def test_order_history_is_customer_scoped_and_includes_status(self):
        self.add()
        placed = self.client.post(
            "/api/orders/place/",
            {"session_id": self.session_id, "customer_id": self.customer_id},
            format="json",
        )
        order = Order.objects.get(order_number=placed.data["order_number"])
        order.status = Order.Status.COMPLETED
        order.save(update_fields=["status"])

        response = self.client.get(f"/api/orders/?customer_id={self.customer_id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]["status"], "completed")
        self.assertEqual(response.data[0]["items"][0]["name"], "Zinger Burger")
        self.assertEqual(self.client.get("/api/orders/?customer_id=someone-else").data, [])

    @patch("ordering.agent.genai.Client")
    def test_python_agent_executes_product_tool_and_uses_python_prompt(self, client_class):
        first_content = types.Content(
            role="model",
            parts=[types.Part.from_function_call(name="get_products", args={"query": "Zinger"})],
        )
        second_content = types.Content(role="model", parts=[types.Part(text="We offer a Zinger Burger for 650.00.")])
        client_class.return_value.models.generate_content.side_effect = [
            types.GenerateContentResponse(candidates=[types.Candidate(content=first_content)]),
            types.GenerateContentResponse(candidates=[types.Candidate(content=second_content)]),
        ]

        with patch.dict(os.environ, {"GEMINI_API_KEY": "server-secret", "GEMINI_AGENT_MODEL": "gemini-3.1-flash-lite"}):
            result = run_ordering_agent(self.session_id, self.customer_id, "Do you have a Zinger?")

        self.assertEqual(result["tools_used"], ["get_products"])
        self.assertIn("Zinger Burger", result["reply"])
        calls = client_class.return_value.models.generate_content.call_args_list
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0].kwargs["config"].system_instruction, SYSTEM_PROMPT)
        function_response = calls[1].kwargs["contents"][-1].parts[0].function_response
        self.assertEqual(function_response.name, "get_products")

    def test_agent_removes_markdown_and_speaks_english_prices_naturally(self):
        raw = "**Beef Burger:** Rs. 750.00\n* Chicken Pizza: 1200.00 rupees"
        self.assertEqual(format_display_reply(raw), "Beef Burger: Rs. 750\nChicken Pizza: 1200 rupees")
        speech = format_speech_reply(raw)
        self.assertNotIn("*", speech)
        self.assertNotIn(".00", speech)
        self.assertIn("seven fifty", speech)
        self.assertIn("twelve hundred", speech)

    def test_agent_speaks_urdu_prices_without_decimal_digits(self):
        speech = format_speech_reply("بیف برگر کی قیمت 750.00 روپے ہے")
        self.assertIn("سات سو پچاس", speech)
        self.assertNotIn("750.00", speech)

    @patch("ordering.views.synthesize_speech", return_value=b"ID3-test-audio")
    def test_urdu_speech_endpoint_returns_mpeg_audio(self, synthesize):
        response = self.client.post(
            "/api/speech/",
            {"text": "آپ کا آرڈر کنفرم ہو گیا ہے", "language": "ur-PK"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "audio/mpeg")
        self.assertEqual(response.content, b"ID3-test-audio")
        synthesize.assert_called_once_with(text="آپ کا آرڈر کنفرم ہو گیا ہے", language="ur-PK")

    def test_speech_endpoint_rejects_unsupported_language(self):
        response = self.client.post(
            "/api/speech/",
            {"text": "Bonjour", "language": "fr-FR"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
