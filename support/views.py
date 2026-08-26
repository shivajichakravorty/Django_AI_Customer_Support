from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, StreamingHttpResponse
import json
import time
import queue as queue_module
from orders.models import Order
from support.agents import run_support_agent
from .models import Conversation, Message
from django.contrib.admin.views.decorators import staff_member_required
from .event_queue import subscribe, unsubscribe, publish, DONE
from .langchain_agents import run_support_agent_langchain





# Create your views here.

def chat(request, order_id):
  if request.method == 'POST':
    data = json.loads(request.body)
    user_message = data.get("message")
    if not user_message:
      return JsonResponse({"error": "Empty message"}, status=400)
    
    order = get_object_or_404(Order, id=order_id, user=request.user)
    conversation, created = Conversation.objects.get_or_create(user=request.user, order=order)
    Message.objects.create(conversation=conversation, role="user", content=user_message)
    event = {"type": "user", "message": user_message, "name": request.user.first_name}
    publish(conversation.id, event)


    #Use any one of the below lines to run the support agent. The first one is the original raw support agent and the second one is the LangChain based support agent. You can switch between them by commenting/uncommenting the respective lines.


    #Uncomment the below line to use the original raw support agent
    #reply = run_support_agent(user_message, conversation.id, order.id, request.user.id)

    #Uncomment the below line to use the LangChain based support agent
    reply = run_support_agent_langchain(user_message, conversation.id, order.id, request.user.id)

    
    Message.objects.create(conversation=conversation, role="agent", content=reply)
    event = {"type": "agent", "message": reply, "name": request.user.first_name}
    publish(conversation.id, event)

    

    return JsonResponse({"Reply": reply})

@staff_member_required
def dashboard(request):
  conversations = Conversation.objects.all().order_by("-created_at")
  context = {
    "conversations": conversations
  }
  return render(request, "support/dashboard.html", context)



@staff_member_required
def conversation_detail(request, conversation_id):
  conversation = get_object_or_404(Conversation, id=conversation_id)
  messages = conversation.messages.order_by("created_at")
  agentlogs = conversation.agent_logs.order_by("created_at")
  context = {
    "conversation": conversation,
    "messages": messages,
    "agentlogs": agentlogs
  }
  return render(request, "support/conversation_detail.html", context)


@staff_member_required
def stream(request, conversation_id):
  def event_stream(conversation_id):
    q = subscribe(conversation_id)

    try:
      while True:
        try:
          event = q.get(timeout=15) # wait for the next event, but not forever
        except queue_module.Empty:
          yield ": keepalive\n\n" # keep the connection alive and detect dead clients
          continue

        yield f"data: {json.dumps(event)}\n\n"
    finally:
      unsubscribe(conversation_id, q)

        
  response = StreamingHttpResponse(event_stream(conversation_id), content_type = "text/event-stream")
  response['Cache-Control'] = 'no-cache'
  response['X-Accel-Buffering'] = 'no'
  return response