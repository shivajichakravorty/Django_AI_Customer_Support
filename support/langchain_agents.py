from aiohttp import request
from django.conf import settings
from django.template import response
from langchain.tools import tool
from langchain_anthropic import ChatAnthropic
from langchain.agents import create_agent

from support.event_queue import publish
from .langchain_tools import get_customer_risk_profile, get_order_details, check_delivery_status, get_refund_history, search_knowledge_base
from .agents import SUPPORT_SYSTEM_PROMPT, MANAGER_SYSTEM_PROMPT, RISK_SYSTEM_PROMPT
from langgraph.checkpoint.memory import InMemorySaver
from .models import Conversation, Message, AgentLog
from langchain.agents.middleware import wrap_tool_call


#Initialize Anthropic Client

llm = ChatAnthropic(model=settings.ANTHROPIC_MODEL, api_key=settings.ANTHROPIC_API_KEY)

# All support tools to be used by the agent
SUPPORT_TOOLS = [get_order_details, get_refund_history, check_delivery_status, search_knowledge_base]

checkpointer = InMemorySaver()

def run_support_agent_langchain(user_message, conversation_id, order_id, user_id):
  conv = Conversation.objects.get(id=conversation_id)
  config = {"configurable": {"thread_id": str(conversation_id)}}

  contextual_message = f"[Context: This conversation is about the order #{order_id}, user: {user_id}] {user_message}"

  # Middleware to log tool calls and results - intercepting tool calls to log them in the AgentLog model

  @tool
  def escalate_to_manager(case_summary: str) -> dict:
    """Escalate the case to the manager for a refund decision. Use this when customer requests a refund or compensation. Prepare a detailed case summary including order details, refund history and customer complaint before escalating"""
    decision = run_manager_agent_langchain(case_summary, conversation_id)
    return {"message": f"Case escalated to manager for review. Manager's decision: {decision}"}
  
  @wrap_tool_call
  def log_tool_calls_middleware(request, handler):
    #print("About to call a tool")
    tool_name = request.tool_call["name"] #this is the tool being called
    tool_args = request.tool_call["args"] #the arguemnet being passed to the respective tool
    AgentLog.objects.create(conversation=conv, event_type="tool_call", message=f"Calling tool {tool_name} with input {tool_args}")
    #Publishing the tool call event to the event queue for real-time updates in the frontend
    event = {"type": "tool_call", "message": f"Calling tool {tool_name} with input {tool_args}"}
    publish(conversation_id, event)
    result = handler(request) #tools are being executed here
    #print(f"Tool {tool_name} called with args: {tool_args}.")
    AgentLog.objects.create(conversation=conv, event_type="tool_result", message=f"Tool {tool_name} returned {str(result)[:200]}")
    #Publishing the tool result event to the event queue for real-time updates in the frontend
    event = {"type": "tool_result", "message": f"Tool {tool_name} returned {str(result)[:200]}"}
    publish(conversation_id, event)
    #print("Tool call completed")  
    return result

  #Create the support agent with the tools, system prompt, checkpointer and middleware
  support_agent = create_agent(
    model = llm,
    tools = SUPPORT_TOOLS + [escalate_to_manager],
    system_prompt = SUPPORT_SYSTEM_PROMPT,
    checkpointer = checkpointer, 
    middleware = [log_tool_calls_middleware]
  )

  result = support_agent.invoke(
    {"messages": [{"role": "user", "content": contextual_message}]},
    config=config,
  )

  #print("Result --->", result)
  final_message = result["messages"][-1].content
  # Save final reply to Agent Log
  AgentLog.objects.create(conversation=conv, event_type="final", message=final_message)
  # Publish final reply to event queue for real-time updates in the frontend
  event = {"type": "final", "message": final_message}
  publish(conversation_id, event)
  publish(conversation_id, {"type": "done", "message": "Request completed."})
  return final_message
  
def run_manager_agent_langchain(case_summary, conversation_id):
  conv = Conversation.objects.get(id=conversation_id)

  @tool
  def assess_risk(user_id: int) -> dict:
    """Assess the risk profile for a user. Use this to assess the fraud risk before making any refund decisions."""
    risk_profile = run_risk_assessment_agent_langchain(user_id, conversation_id)
    return {"message": f"Risk profile for user {user_id}: {risk_profile}"}

  @wrap_tool_call
  def log_manager_tool_calls_middleware(request, handler):
    event = {"type": "manager", "message": f"Consulting risk agent for fraud assessment...."}
    publish(conversation_id, event)
    AgentLog.objects.create(conversation=conv, event_type="manager", message=f"Consulting risk agent for fraud assessment....")

    result = handler(request) #tools are being executed here

    return result


  manager_agent = create_agent(
    model = llm,
    tools = [assess_risk],
    system_prompt = MANAGER_SYSTEM_PROMPT,
    middleware = [log_manager_tool_calls_middleware]
  )
  event = {"type": "manager", "message": f"Case received for review: {case_summary[:200]}"}
  publish(conversation_id, event)
  AgentLog.objects.create(conversation=conv, event_type="manager", message=f"Case received for review: {case_summary[:200]}")

  result = manager_agent.invoke(
    {"messages": [{"role": "user", "content": case_summary}]},
  )
  decision = result["messages"][-1].content
  event = {"type": "manager", "message": f"Decision: {decision[:200]}"}
  publish(conversation_id, event)
  AgentLog.objects.create(conversation=conv, event_type="manager", message=f"Decision: {decision[:200]}")
  #print("Manager's decision --->", decision)
  return decision


def run_risk_assessment_agent_langchain(user_id, conversation_id):

  conv = Conversation.objects.get(id=conversation_id)
  event = {"type": "risk", "message": f"Starting fraud assessment for user ID: {user_id}"}
  publish(conversation_id, event)
  AgentLog.objects.create(conversation=conv, event_type="risk", message=f"Starting fraud assessment for user ID: {user_id}")

  @wrap_tool_call
  def log_risk_tool_calls_middleware(request, handler):
    tool_name = request.tool_call["name"] #this is the tool being called
    tool_args = request.tool_call["args"] #the arguemnet being passed to the respective tool
    event = {"type": "risk", "message": f"Calling tool {tool_name} with input {tool_args}"}
    publish(conversation_id, event)
    AgentLog.objects.create(conversation=conv, event_type="risk", message=f"Calling tool {tool_name} with input {tool_args}")

    result = handler(request) #tools are being executed here

    return result

  risk_agent = create_agent(
    model = llm,
    tools = [get_customer_risk_profile],
    system_prompt = RISK_SYSTEM_PROMPT,
    middleware = [log_risk_tool_calls_middleware]
  )
  
  result = risk_agent.invoke(
    {"messages": [{"role": "user", "content": f"Assess the risk profile for user {user_id}. Use your tool to fetch the risk profile and provide a summary of the fraud risk."}]},
  )
  risk_profile = result["messages"][-1].content
  event = {"type": "risk", "message": f"Verdict: {risk_profile[:200]}"}
  publish(conversation_id, event)
  AgentLog.objects.create(conversation=conv, event_type="risk", message=f"Risk profile for user {user_id}: {risk_profile[:200]}")
  return risk_profile

