from langchain.tools import tool
from .tools import (
  get_order_details as _get_order_details, 
  get_refund_history as _get_refund_history,
  check_delivery_status as _check_delivery_status,
  search_knowledge_base as _search_knowledge_base,
  get_customer_risk_profile as _get_customer_risk_profile
)


@tool
def get_order_details(order_id: int) -> dict:
  """Fetch complete order details including status, carrier, tracking number and days since order was placed. Use this when customer mentions their order or complaints about delivery."""
  return _get_order_details(order_id)


@tool
def get_refund_history(user_id: int) -> dict:
  """Get complete refund history for a user. Use this before making any refund decisions."""
  return _get_refund_history(user_id)


@tool
def check_delivery_status(tracking_number: str, carrier: str) -> dict:
  """Check current delivery status using tracking number and carrier. Use this to check delivery details as per customer message"""
  return _check_delivery_status(tracking_number, carrier)


@tool
def search_knowledge_base(query: str) -> dict:
  """Search CoolBreeze AC company documents including refund policy, warranty policy and product FAQ. Use this when customer asks for company policies, warranty coverage, refund eligibility or any general product related queries"""
  return _search_knowledge_base(query)


@tool
def get_customer_risk_profile(user_id: int) -> dict:
  """Get complete risk profile for a customer including order history, refund patterns, refund request and refund ratio. Use this to assess the fraud risk."""

  return _get_customer_risk_profile(user_id)





