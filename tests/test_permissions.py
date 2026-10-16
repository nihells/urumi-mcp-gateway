import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")

if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.services.unified_mcp import ADMIN_ONLY_TOOLS


def test_product_creation_is_admin_only():
    assert "woocommerce__create_product" in ADMIN_ONLY_TOOLS


def test_order_status_update_is_admin_only():
    assert "woocommerce__update_order_status" in ADMIN_ONLY_TOOLS


def test_read_only_tools_are_not_admin_only():
    assert "woocommerce__list_products" not in ADMIN_ONLY_TOOLS
    assert "woocommerce__list_orders" not in ADMIN_ONLY_TOOLS
    assert "woocommerce__get_order" not in ADMIN_ONLY_TOOLS