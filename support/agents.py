from anthropic import Anthropic
from django.conf import settings
from .tools import get_order_details, get_refund_history, check_delivery_status, get_customer_risk_profile
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
- Never use bold text, bullet points or any markdown formatting. Plain text only. 
- Keep the replies concise and conversational. Maximum 3 sentences, no long paragraphs.


"""

MANAGER_SYSTEM_PROMPT = """

You are a senior support manager at CoolBreeze AC.
A support agent has escalated a customer case to you for a refund decision.

Your responsibilities:
- Review the case summary carefully
- Consider the customer's refund history
- Make a fair and final refund decision
- Give a clear reason for your decision

Your decision options:
- Approve refund - if the case is genuine and within policy
- Deny refund - if the case is suspicious or outside of policy
- Escalate to risk team - if you suspect fraud

Important rules:
- Be fair but firm
- Base decision on facts - not emotions
- Always give a specific reason for your decision
- Keep your response concise and professional
"""

RISK_SYSTEM_PROMPT = """
You are a fraud risk analyst at CoolBreeze AC.
A support manager has sent you a customer profile for risk assessment.

Your job:
- Analyse the customer's order and refund patterns
- Identify suspicious behavior
- Return a clear risk verdict

Risk levels:
- LOW - genuine customer, normal behavior
- MEDIUM - some suspicious signals, proceed with caution
- HIGH - clear fraud pattern, recommend denial

Your response format:
- Risk Level: LOW / MEDIUM / HIGH
- Key Signals: what you found suspicious or genuine
- Recommendation: what manager should do

Important:
- Be objective - base verdict on data only
- One bad refund does not mae someone fraudulent
- Look for patterns - not isolated incidents

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

  },

  {
     "name": "escalate_to_manager",
     "description": "Escalate the case to the manager for a refund decision. Use this when customer requests a refund or compensation. Prepare a detailed case summary including order details, refund history and customer complaint before escalating",
     "input_schema": {
        "type": "object",
        "properties": {
           "case_summary": {
              "type": "string",
              "description": "Complete case summary including order details, refund history and customer complaint"
           }
        },
        "required": ["case_summary"]

     }

     
  }

]

MANAGER_TOOLS = [
   {
      "name": "assess_fraud_risk",
      "description": "Consult the risk agent to assess fraud risk for a customer. Use this when refund request looks suspicious or customer has multiple refund requests. Pass the user ID to the agent",
      "input_schema": {
         "type": "object",
         "properties": {
           "user_id": {
             "type": "integer",
             "description": "The user ID to check risk profile for"
           
           }
            
      },
      "required": ["user_id"]
      }

   }
]


RISK_TOOLS = [
   {
      "name": "get_customer_risk_profile",
      "description": "get complete risk profile for a customer including order history, refund patterns, refund request and refund ratio. Use this to assess the fraud risk.",
      "input_schema": {
         "type": "object",
         "properties": {
            "user_id": {
               "type": "integer",
               "description": "The user ID to check risk profile for"   
            }
         },
         "required": ["user_id"]

      }      
   }
]
#EXECUTE TOOL --> BRIDGE BETWEEN CLAUDE AND PYTHON FUNCTION TOOLS. 

def execute_tool(tool_name, tool_input, conversation_id=None):
  if tool_name == "get_order_details":
    return get_order_details(tool_input["order_id"])

  if tool_name == "get_refund_history":
    return get_refund_history(tool_input["user_id"])

  if tool_name == "check_delivery_status":
    return check_delivery_status(tool_input["tracking_number"], tool_input["carrier"])

  if tool_name == "escalate_to_manager":
    return run_manager_agent(tool_input["case_summary"], conversation_id)

  if tool_name == "assess_fraud_risk":
    return run_risk_agent(tool_input["user_id"], conversation_id)

  if tool_name == "get_customer_risk_profile":
    return get_customer_risk_profile(tool_input["user_id"])
  
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
    # print("Stop Reason ===>", response.stop_reason)
    # print("Content ===>", response.content)

    if response.stop_reason == 'tool_use':
          conversation_messages.append({
             "role": "assistant",
             "content": response.content
          })

          tool_result = []
          for block in response.content:
             if block.type == 'tool_use':
                #log tool call
                AgentLog.objects.create(conversation=conv, event_type="tool_call", message=f"Calling tool {block.name} with input {block.input}")
                # print("Tool call:", block.name)
                # print("Tool input:", block.input)

                #execute the tool here
                result = execute_tool(block.name, block.input, conversation_id)
                # print("Tool result:", result)
                AgentLog.objects.create(conversation=conv, event_type="tool_result", message=f"Tool {block.name} returned {str(result)[:200]}")

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
       AgentLog.objects.create(conversation=conv, event_type="final", message=response.content[0].text)
       return response.content[0].text


def run_manager_agent(case_summary, conversation_id):
   conv = Conversation.objects.get(id=conversation_id)
   AgentLog.objects.create(conversation=conv, event_type="manager", message=f"Case received for review: {case_summary[:200]}")
   manager_messages = [
      {"role": "user", "content": case_summary}
   ]

   while True:
      response = client.messages.create(model=anthropic_model,
      max_tokens=1024,
      system=MANAGER_SYSTEM_PROMPT,
      messages=manager_messages
      )

      if response.stop_reason == 'tool_use':
         tool_result = []
         for block in response.content:
            if block.type == 'tool_use':
               AgentLog.objects.create(conversation=conv, event_type="manager", message=f"Consulting risk agent for fraud assessment")

               result = execute_tool(block.name, block.input, conversation_id=conversation_id)
               AgentLog.objects.create(conversation=conv, event_type="tool_result", message=f"Tool {block.name} returned {str(result)[:200]}")


               tool_result.append({
                  "type": "tool_result",
                  "tool_use_id": block.id,
                  "content": str(result)
               })

         manager_messages.append({
            "role": "user",
            "content": tool_result
         })
      else:
         AgentLog.objects.create(Conversation=conv, event_type="manager", message=f"Decision: {response.content[0].text[:200]}")
         return response.content[0].text


def run_risk_agent(user_id, conversation_id):
   conv = Conversation.objects.get(id=conversation_id)
   AgentLog.objects.create(conversation=conv, event_type="risk", message=f"Starting fraud assessment for user ID: {user_id}")

   risk_messages = [
      {"role": "user", "content": f"Please assess the fraud risk for user ID {user_id}. Use your tool to get their profile and return a final response."}
   ]

   while True:
      response = client.messages.create(model=anthropic_model,
      max_tokens=1024,
      system=RISK_SYSTEM_PROMPT,
      tools=RISK_TOOLS,
      messages=risk_messages
      )

      if response.stop_reason == 'tool_use':
         tool_result = []
         for block in response.content:
            if block.type == 'tool_use':
               AgentLog.objects.create(conversation=conv, event_type="risk", message=f"Calling tool {block.name} with input {block.input}")
               print("Risk tool call:", block.name)
               print("Risk tool input:", block.input)

               #execute the tool here)
               result = execute_tool(block.name, block.input)
               print("Risk tool result:", result)

               tool_result.append({
                  "type": "tool_result",
                  "tool_use_id": block.id,
                  "content": str(result)
               })

         risk_messages.append({
            "role": "user",
            "content": tool_result
         })
      else:
         AgentLog.objects.create(conversation=conv, event_type="risk", message=f"Decision: {response.content[0].text[:200]}")
         return response.content[0].text


         

