from django.utils import timezone
from orders.models import Order, RefundRequest
from .tracking_data import DELIVERY_DATA
from .rag import search_knowledge_base as rag_search

def get_order_details(order_id):
  try:
    order = Order.objects.get(id=order_id)
    return{
      "order_id": order.id,
      "product_name": order.product_name,
      "amount": str(order.amount),
      "status": order.status,
      "carrier": order.carrier,
      "tracking_number": order.tracking_number,
      "delivery_address": order.delivery,
      "ordered_on": order.created_at.strftime("%d %b %Y"), 
      "days_since_order": (timezone.now() - order.created_at).days,

    }
  except Order.DoesNotExist:
    return {"error": f"Order #{order_id} not found"}
  
def get_refund_history(user_id):
  refunds = RefundRequest.objects.filter(user_id=user_id).order_by("-created_at")

  history = []
  for refund in refunds:
    history.append({
      "order_id": refund.order.id,
      "product": refund.order.product_name,
      "reason": refund.reason,
      "status": refund.status,
      "requested_on": refund.created_at.strftime("%d %b %Y"),      
      
    })
  return {
    "total_refund_requests": len(history),
    "history": history,
  
  }

def check_delivery_status(tracking_number, carrier=None):
  default_response = {
    "status": "Unknown",
    "last_location": "Tracking info unavailable",
    "last_update": "N/A",
    "estimated_delivery": "Contact carrier directly",
    "delay_reason": None,
  }
  result = DELIVERY_DATA.get(tracking_number, default_response).copy()
  result["tracking_number"] = tracking_number
  order = Order.objects.filter(tracking_number=tracking_number).first()
  result["carrier"] = order.carrier if order and order.carrier else "N/A"
  return result

def get_customer_risk_profile(user_id):

  refunds = RefundRequest.objects.filter(user_id=user_id)
  orders = Order.objects.filter(user_id=user_id)

  # Recent 90 days refund requests
  recent_refunds = refunds.filter(created_at__gte=timezone.now() - timezone.timedelta(days=90)).count()

  denied = refunds.filter(status="denied").count()
  approved = refunds.filter(status="approved").count()
  pending = refunds.filter(status="pending").count()

  total_orders = orders.count()
  total_refunds = refunds.count()

  if total_orders > 0:
    refund_to_order_ratio = round(total_refunds / total_orders, 2)
  else:
    refund_to_order_ratio = 0


  return {
    "user_id": user_id,
    "refund_to_order_ratio": refund_to_order_ratio,
    "recent_refunds": recent_refunds,
    "denied": denied,
    "approved": approved,
    "pending": pending,
    "total_orders": total_orders,
    "total_refunds": total_refunds,
  }


#Wrapper function - avoiding conflict
def search_knowledge_base(query):
  result = rag_search(query)
  return {"result": result}