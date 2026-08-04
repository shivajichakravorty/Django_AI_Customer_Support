from anthropic import Anthropic
from django.conf import settings
from .tools import get_order_details, get_refund_history, check_delivery_status
from . models import Conversation, Message, AgentLog



client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

anthropic_model = settings.ANTHROPIC_MODEL

#SUPPORT SYSTEM PROMPT --->> JARVIS'S JOB DESCRIPTION

SUPPORT_SYSTEM_PROMPT = """

You are Melanie, a customer support agent at Coolbreeze AC.
You help customers with issues related to their AC orders. 

Your responsibilities:
- Always use your tools to gather facts before responding
- Check order details when customer mentions their order
- Check refund history before making any refund decisions
- Be empathetic but honest

Your personality:
- Friendly and professional
- Patient even when customer is angry
- Clear and concise in your replies

Important rules:
- Always check order details first before responding
- Never support or deny a refund request yourself
- If refund decision is needed - tell customer you are checking with your team


"""

#SUPPORT TOOLS --> TOOLS SCHEMA THAT AI AGENTS WILL READ

SUPPORT_TOOLS = [
  {
    "name": "get_order_details",
    "description": "Fetch complete order details including status, carrier, tracking number and days since order was placed. Use this when customer mentions their order or complaints about delivery.",
    "input_schema": {
      "type": "object",
      "properties": {
        "order_id": {
          "type": "integer",
          "description": "The order ID to look up"
        }
      },
      "required": ["order_id"]
    }
  },

  {
      "name": "get_refund_history",
      "description": "Get complete refund history for a user. Use this before making any refund decisions.",
      "input_schema": {
        "type": "object",
        "properties": {
          "user_id": {
            "type": "integer",
            "description": "The user ID to check refund history for"
          }
        },
        "required": ["user_id"]
      }
  },

  {
    "name": "check_delivery_status",
    "description": "Check current delivery status using tracking number and carrier. Use this to check delivery details as per customer message",
    "input_schema": {
      "type": "object",
      "properties": {
        "tracking_number": {
          "type": "string",
          "description": "The tracking number of the order"
        },
        "carrier": {
          "type": "string",
          "description": "The carrier of the order"
        }
      },
      "required": ["tracking_number", "carrier"]

    }

  }

]


#EXECUTE TOOL --> BRIDGE BETWEEN CLAUDE AND PYTHON FUNCTION TOOLS. 

def execute_tool(tool_name, tool_input):
  if tool_name == "get_order_details":
    return get_order_details(tool_input["order_id"])

  if tool_name == "get_refund_history":
    return get_refund_history(tool_input["user_id"])

  if tool_name == "check_delivery_status":
    return check_delivery_status(tool_input["tracking_number"], tool_input["carrier"])
  
  return None




#AGENT LOOP --> WHILE LOOP THAT LOOPS UNTIL THE TASK IS DONE

def run_support_agent(user_message, conversation_id, order_id, user_id):
  conv = Conversation.objects.get(id=conversation_id)
  conversation_messages = []

  for msg in conv.messages.order_by("created_at"):
    api_role = "assistant" if msg.role == "agent" else msg.role
    conversation_messages.append({"role": api_role, "content": msg.content})

  # send this conversation_messages to LLM
  while True:
    response = client.messages.create(model=anthropic_model, 
    max_tokens=1024,
    system=SUPPORT_SYSTEM_PROMPT + f"\n\nContext: This conversation is about the order #{order_id}, user: {user_id}",
    tools=SUPPORT_TOOLS,
    messages=conversation_messages
  )
    print("Stop Reason ===>", response.stop_reason)
    print("Content ===>", response.content)

    if response.stop_reason == 'tool_use':
          conversation_messages.append({
             "role": "assistant",
             "content": response.content
          })

          tool_result = []
          for block in response.content:
             if block.type == 'tool_use':
                # print("Tool call:", block.name)
                # print("Tool input:", block.input)

                #execute the tool here
                result = execute_tool(block.name, block.input)
                # print("Tool result:", result)
                tool_result.append({
                   "type": "tool_result",
                   "tool_use_id": block.id,
                   "content": str(result)
                })

          conversation_messages.append({
             "role": "user",
             "content": tool_result
          })
    else:
       return response.content[0].text