# MELCO-Care 🏥

**Agentic AI System Augmenting the Indian Healthcare Environment**

MELCO-Care is an intelligent healthcare assistant designed for Indian hospitals, focusing on Tier-2/3 cities and rural areas. It helps patients book appointments through symptom-based triage, provides AI-powered medical guidance, and assists hospital administration with resource management.

---

## 🎯 Project Overview

### Problem Statement
Indian government healthcare systems face significant challenges:
- **Overloaded Hospitals**: 80% of doctor time spent on administrative tasks
- **Long Wait Times**: Patients wait hours due to inefficient routing
- **Resource Invisibility**: No real-time bed/ICU/inventory tracking
- **Fragmented Patient Journey**: Multiple visits, misdirected referrals

### Solution
MELCO-Care provides an **agentic AI system** that:
1. **Triages patients** based on symptoms using VLM (Vision Language Models)
2. **Routes to appropriate departments** with shortest wait times
3. **Books appointments** with real-time queue management
4. **Analyzes medical images** (prescriptions, lab reports, skin conditions)

---

## ✅ What's Implemented (MVP)

### Core Features
| Feature | Status | Description |
|---------|--------|-------------|
| **Appointment Scheduling** | ✅ Complete | AI-powered symptom analysis and doctor booking |
| **Symptom Triage** | ✅ Complete | VLM analyzes symptoms and suggests departments |
| **Doctor Queue Management** | ✅ Complete | Real-time queue tracking and wait time estimation |
| **Multi-Role Support** | ✅ Complete | Patient, Doctor, Admin interfaces |
| **Image Analysis** | ✅ Complete | Analyze medical images via VLM |
| **Chat History** | ✅ Complete | Persistent conversation storage |

### Technical Components
| Component | Technology | Status |
|-----------|------------|--------|
| Frontend | Streamlit | ✅ Complete |
| Backend API | FastAPI | ✅ Complete |
| Database | SQLite + SQLModel | ✅ Complete |
| VLM Integration | Ollama (gemma3:4b, qwen3-vl:8b) | ✅ Complete |
| Orchestrator Agent | Custom Python | ✅ Complete |
| RAG Context Builder | Custom Python | ✅ Complete |

---

## 🚧 What's Left (Future Phases)

### Phase 2 Features
- [ ] **Bed Management**: Real-time hospital bed tracking
- [ ] **Emergency Routing**: Ambulance dispatch integration
- [ ] **Government Scheme Matcher**: Match patients to Ayushman Bharat, PMJAY
- [ ] **Pharmacy/Inventory Agent**: Medicine availability tracking
- [ ] **Voice Input**: Hinglish voice support for rural users

### Technical Improvements
- [ ] **LangGraph Integration**: Replace custom orchestrator with LangGraph
- [ ] **PostgreSQL Migration**: Scale from SQLite to PostgreSQL
- [ ] **Redis Caching**: Add caching for faster responses
- [ ] **Authentication**: Add proper JWT-based auth
- [ ] **Docker Deployment**: Containerized deployment

---

## 🚀 Quick Start

### Prerequisites
- **Python 3.10+**: [Download](https://python.org)
- **Ollama**: [Download](https://ollama.ai/download)
- **GPU (Recommended)**: NVIDIA GPU with 8GB+ VRAM

### Installation

```bash
# Clone the repository
git clone https://github.com/soumysuwas/MELCO_Care.git
cd MELCO_Care

# Create virtual environment
python -m venv venv

# Activate (Windows)
.\venv\Scripts\Activate.ps1

# Activate (Linux/Mac)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Initialize database with synthetic data
python scripts/init_db.py
```

### Setup Ollama Models

```bash
# Pull required models
ollama pull gemma3:4b      # Primary model (faster)
ollama pull qwen3-vl:8b    # Vision model (for images)
```

### Run the Application

**Terminal 1 - Start Ollama:**
```bash
ollama serve
```

**Terminal 2 - Start Backend:**
```bash
.\venv\Scripts\Activate.ps1   # Windows
uvicorn backend.main:app --reload
```

**Terminal 3 - Start Frontend:**
```bash
.\venv\Scripts\Activate.ps1   # Windows
streamlit run frontend/app.py
```

### Access
- **Frontend**: http://localhost:8501
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

---

## 📁 Project Structure

```
MELCO_Care/
├── database/
│   ├── models.py              # SQLModel schemas (User, Hospital, Doctor, etc.)
│   ├── connection.py          # SQLite connection manager
│   ├── seed_data.py           # Synthetic data generator (50 users, 15 hospitals)
│   └── melco_care.db          # SQLite database file
│
├── backend/
│   ├── main.py                # FastAPI application entry point
│   ├── config.py              # Pydantic settings (env vars)
│   ├── routers/
│   │   ├── chat.py            # /api/chat, /api/book-appointment endpoints
│   │   └── admin.py           # /api/admin/* endpoints
│   ├── agents/
│   │   ├── orchestrator.py    # Central agent - routes intents to sub-agents
│   │   ├── appointment.py     # Appointment booking workflow
│   │   └── rag_builder.py     # RAG context builder for LLM prompts
│   └── services/
│       ├── vlm_service.py     # Ollama VLM integration
│       └── database_service.py# Database CRUD operations
│
├── frontend/
│   └── app.py                 # Streamlit multi-page application
│
├── scripts/
│   ├── init_db.py             # Database initialization
│   └── setup_ollama.ps1       # Ollama model setup (Windows)
│
├── uploads/                   # Uploaded medical images
├── .env                       # Environment configuration
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

---

## 🗄️ Database Schema

### Tables
| Table | Description | Records |
|-------|-------------|---------|
| `user` | All users (patients, doctors, admins) | 50 |
| `hospital` | Hyderabad hospitals | 15 |
| `department` | Hospital departments | ~75 |
| `doctor` | Doctor profiles with specializations | ~40 |
| `appointment` | Booking records | 20+ |
| `chatsession` | Chat sessions per user | Dynamic |
| `chatmessage` | Individual messages | Dynamic |

### Synthetic Data
- **2 Admins**: Hospital administrators
- **8 Doctors**: Various specializations
- **40 Patients**: Hyderabad residents with Indian names
- **15 Hospitals**: Mix of government and private (Gandhi Hospital, NIMS, Apollo, etc.)

---

## 🔌 API Endpoints

### Chat
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/chat` | POST | Send text message, get AI response |
| `/api/chat/with-image` | POST | Send message with medical image |
| `/api/book-appointment` | POST | Confirm and book appointment |
| `/api/appointments/{user_id}` | GET | Get user's appointments |
| `/api/chat/history/{user_id}` | GET | Get chat history |

### Admin
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/admin/hospitals` | GET | List all hospitals |
| `/api/admin/hospitals/{id}` | GET | Get hospital details |
| `/api/admin/hospitals/{id}/beds` | PATCH | Update bed count |
| `/api/admin/users` | GET | List users by role |
| `/api/admin/status` | GET | System health status |

---

## 🤖 AI Models

| Model | Purpose | Size |
|-------|---------|------|
| `gemma3:4b` | Primary - Intent classification, responses | 3.3 GB |
| `qwen3-vl:8b` | Vision - Medical image analysis | 6.1 GB |

### Supported Intents
- `appointment` - Book a doctor appointment
- `emergency` - Medical emergency alert
- `symptom_check` - Analyze symptoms
- `hospital_info` - Hospital/doctor information
- `general` - General queries

---

## ⚙️ Configuration

### Environment Variables (.env)
```env
# Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_PRIMARY_MODEL=gemma3:4b
OLLAMA_VISION_MODEL=qwen3-vl:8b
OLLAMA_FALLBACK_MODEL=gemma3:4b

# Database
DATABASE_URL=sqlite:///./database/melco_care.db

# API
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=True
```

---

## 🧪 Testing the System

### Test Symptom Analysis
1. Login as **Patient**
2. Type: "I have headache and fever since yesterday"
3. AI should suggest **General Medicine** department
4. See available doctors with wait times
5. Click **Book** to schedule appointment

### Test Image Analysis
1. Login as **Patient**
2. Upload a medical image (prescription, skin rash photo)
3. Type: "What does this show?"
4. AI analyzes and responds

### Test Admin Dashboard
1. Login as **Admin**
2. View hospital list with bed counts
3. Check system status (Ollama online, database stats)

---

## 🐛 Troubleshooting

### "Error connecting to server: Read timed out"
- The VLM is taking too long. Wait 30-60 seconds.
- Ensure Ollama is running: `ollama serve`
- Check GPU utilization - model runs faster on GPU

### "Ollama offline" in status
```bash
# Start Ollama server
ollama serve

# Verify models
ollama list
```

### Database errors
```bash
# Re-initialize database
del database\melco_care.db  # Windows
python scripts/init_db.py
```

---

## 👥 Contributors

- **Nikhil Suwas** - Developer

---

## 📄 License

MIT License - Built for Google Solution Challenge / Healthcare Hackathon

---

## 🙏 Acknowledgments

- **Ollama** for local LLM serving
- **Google Gemma** and **Alibaba Qwen** for open-source models
- **Streamlit** and **FastAPI** for rapid prototyping
