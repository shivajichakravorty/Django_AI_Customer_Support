# Django_AI_Customer_Support

An AI-powered, multi-agent customer support system built with Django and LangChain. The system features autonomous agents collaborating to handle customer inquiries, escalate complex cases, and assess account risks dynamically.

**Production Deployment:** [Live Application](https://djangoaicustomersupport-production.up.railway.app/login/)

### 🔑 Demo Credentials
Use these pre-configured accounts to explore the system and test the multi-agent routing logic:

| Role | Username | Password |
| :--- | :--- | :--- |
| **Customer Portal** | `priya` | `1234` |
| **Customer Portal** | `rathan` | `1234` |
| **Customer Portal** | `arjun` | `1234` |
| **Customer Portal** | `fraud_test` | `Django@1234` |
| **Django Admin / Dashboard** | `djangoadmin` | `1234` |

*Note: The system is currently seeded with hardcoded dummy data (including sample order histories and refund requests) so you can test escalations right away.*
Use code with caution.Would you like me to regenerate the entire complete markdown code block with these changes included, or would you like to add some specific instructions on how to trigger a manager escalation during the chat?

## 🚀 Features

* **Multi-Agent Architecture:** Powered by LangChain and Claude API.
* **Melanie (Support Agent):** Primary interface interacting directly with customers.
* **Manager Agent:** Handles escalations referred by Melanie for advanced assistance.
* **Risk Agent:** Assesses customer account risks to guide manager decisions.
* **RAG Integration:** Retrieves context-aware data for precise support responses.
* **SSE Dashboard:** Real-time updates delivered via Server-Sent Events.

## 🛠️ Tech Stack

* **Backend Framework:** Django
* **AI & Orchestration:** LangChain, Claude API, RAG (Retrieval-Augmented Generation)
* **Vector Database:** ChromaDB
* **Real-Time Delivery:** SSE (Server-Sent Events) Dashboard
* **Database:** SQL
* **Frontend:** JavaScript, HTML, Bootstrap

## 📐 Architecture Diagram

The multi-agent workflow coordinates tasks sequentially based on escalation depth:

```
[ Customer ] 
     │
     ▼
┌──────────────┐      Escalates      ┌──────────────┐
│   Melanie    │ ──────────────────> │    Manager   │
│ (Support AI) │                     │    Agent     │
└──────────────┘                     └──────────────┘
       ▲                                    │  Requires
       │ Context                            │  Risk Check
       ▼                                    ▼
┌──────────────┐                     ┌──────────────┐
│  RAG Store   │                     │  Risk Agent  │
│ (Knowledge)  │                     │ (Acct Review)│
└──────────────┘                     └──────────────┘
```

## 🗄️ Database Schema & Project Structure

The Django project is divided into two decoupled applications managing the e-commerce transaction data and the live AI interaction context:

### 1. `orders` App
Manages catalog inventory, customer purchases, and post-sale interaction logs.
* **Product:** `name`, `description`, `price`, `category`, `in_stock` (availability).
* **Order:** `user`, `product`, `product_name`, `amount`, `status`, `carrier`, `tracking_number`, `delivery_address`, `created_at`, `updated_at`.
* **Refund Request:** `order` (FK), `user` (FK), `reason_for_refund`, `status`, `created_at`.

### 2. `support` App
Persists conversational context to fuel LangChain memory and handles agent logging telemetry.
* **Conversation:** `user`, `order`, `created_at`.
* **Messages:** `conversation` (FK), `role` (user/assistant/system), `content`, `created_at`.
* **AgentLog:** `conversation` (FK), `event_type` (pipeline stage/state transition), `message` (agent response), `created_at`.

## 🔌 API Endpoints

### SSE Dashboard Stream

| Endpoint | Protocol | Description |
| :--- | :--- | :--- |
| `/support/dashboard` | SSE (HTTP) | Streams live agent logs, active chat threads, and agent state transitions to the dashboard. |

*Production URL:* `https://djangoaicustomersupport-production.up.railway.app/support/dashboard`

## 📦 Installation


```bash
# Clone the repository
git clone https://github.com/shivajichakravorty/Django_AI_Customer_Support.git

# Navigate to the directory
cd django-ai-customer-support

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`

# Install dependencies
pip install -r requirements.txt
```

## ⚙️ Configuration

Create a `.env` file in the root directory and configure your keys:

```env
DEBUG=True
SECRET_KEY=your_django_secret_key
ANTHROPIC_API_KEY=your_claude_api_key
DATABASE_URL=your_sql_database_url
```

## 🏃 Usage

```bash
# Apply database migrations
python manage.py migrate

# Start the development server
python manage.py runserver
```

Open `http://127.0.0.1:8000/login/` in your browser to view the application locally.

## 🤝 Contributing

1. Fork project
2. Create branch
3. Commit changes
4. Push branch
5. Open PR

