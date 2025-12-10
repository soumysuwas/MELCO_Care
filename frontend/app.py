"""
MELCO-Care Streamlit Frontend Application
Multi-role healthcare assistant interface
"""

import streamlit as st
import requests
from datetime import datetime
import os
from PIL import Image
import io

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api")

# Page configuration
st.set_page_config(
    page_title="MELCO-Care",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better UI
st.markdown("""
<style>
    /* Main container */
    .main {
        padding: 1rem;
    }
    
    /* Chat message styling */
    .chat-message {
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 0.5rem;
        display: flex;
        flex-direction: column;
    }
    
    .user-message {
        background-color: #e3f2fd;
        margin-left: 20%;
    }
    
    .assistant-message {
        background-color: #f5f5f5;
        margin-right: 20%;
    }
    
    /* Doctor card styling */
    .doctor-card {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 0.5rem;
        transition: box-shadow 0.3s;
    }
    
    .doctor-card:hover {
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    
    /* Priority badges */
    .priority-low { color: #4caf50; }
    .priority-medium { color: #ff9800; }
    .priority-high { color: #f44336; }
    .priority-emergency { color: #d32f2f; font-weight: bold; }
    
    /* Header styling */
    .header-container {
        display: flex;
        align-items: center;
        padding: 1rem 0;
        border-bottom: 2px solid #1976d2;
        margin-bottom: 1rem;
    }
    
    .logo-text {
        font-size: 2rem;
        font-weight: bold;
        color: #1976d2;
    }
    
    /* Sidebar styling */
    .sidebar .sidebar-content {
        background-color: #f8f9fa;
    }
    
    /* Success/Error messages */
    .success-box {
        background-color: #e8f5e9;
        border-left: 4px solid #4caf50;
        padding: 1rem;
        border-radius: 5px;
    }
    
    .error-box {
        background-color: #ffebee;
        border-left: 4px solid #f44336;
        padding: 1rem;
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)


# ============== SESSION STATE INITIALIZATION ==============

def init_session_state():
    """Initialize session state variables"""
    if "user_id" not in st.session_state:
        st.session_state.user_id = None
    if "user_role" not in st.session_state:
        st.session_state.user_role = None
    if "user_name" not in st.session_state:
        st.session_state.user_name = None
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "current_doctor_options" not in st.session_state:
        st.session_state.current_doctor_options = None
    if "pending_symptoms" not in st.session_state:
        st.session_state.pending_symptoms = None
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False


# ============== API FUNCTIONS ==============

def api_chat(user_id: int, message: str):
    """Send chat message to API"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/chat",
            json={"user_id": user_id, "message": message},
            timeout=120
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"success": False, "response": f"Error connecting to server: {str(e)}"}


def api_chat_with_image(user_id: int, message: str, image_file):
    """Send chat message with image to API"""
    try:
        files = {"image": image_file}
        data = {"user_id": user_id, "message": message}
        response = requests.post(
            f"{API_BASE_URL}/chat/with-image",
            files=files,
            data=data,
            timeout=120
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"success": False, "response": f"Error connecting to server: {str(e)}"}


def api_book_appointment(user_id: int, doctor_id: int, symptoms: str, symptoms_summary: str, priority: str):
    """Book an appointment"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/book-appointment",
            json={
                "user_id": user_id,
                "doctor_id": doctor_id,
                "symptoms": symptoms,
                "symptoms_summary": symptoms_summary,
                "priority": priority
            },
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"success": False, "message": f"Error: {str(e)}"}


def api_get_hospitals(city: str = None):
    """Get list of hospitals"""
    try:
        params = {"city": city} if city else {}
        response = requests.get(f"{API_BASE_URL}/admin/hospitals", params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except:
        return []


def api_get_users(role: str = None):
    """Get list of users"""
    try:
        params = {"role": role} if role else {}
        response = requests.get(f"{API_BASE_URL}/admin/users", params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except:
        return []


def api_get_system_status():
    """Get system status"""
    try:
        response = requests.get(f"{API_BASE_URL}/admin/status", timeout=10)
        response.raise_for_status()
        return response.json()
    except:
        return {"database_status": "unknown", "ollama_status": "unknown"}


# ============== UI COMPONENTS ==============

def render_login_page():
    """Render login/role selection page"""
    st.markdown("""
    <div style="text-align: center; padding: 2rem;">
        <h1 style="color: #1976d2;">🏥 MELCO-Care</h1>
        <p style="font-size: 1.2rem; color: #666;">
            AI-Powered Healthcare Assistant for Indian Hospitals
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("### Login")
        
        # Role selection
        role = st.selectbox(
            "Select your role",
            ["Patient", "Doctor", "Admin"],
            key="login_role"
        )
        
        # Get users for selected role
        users = api_get_users(role.lower())
        
        if users:
            user_options = {f"{u['name']} (ID: {u['user_id']})": u for u in users}
            selected_user = st.selectbox(
                "Select user",
                list(user_options.keys()),
                key="login_user"
            )
            
            if st.button("Login", type="primary", use_container_width=True):
                user = user_options[selected_user]
                st.session_state.user_id = user["user_id"]
                st.session_state.user_role = user["role"]
                st.session_state.user_name = user["name"]
                st.session_state.logged_in = True
                st.session_state.messages = []
                st.rerun()
        else:
            st.warning("Unable to fetch users. Is the backend running?")
            st.info("Start the backend with: `uvicorn backend.main:app --reload`")


def render_chat_message(role: str, content: str, has_image: bool = False):
    """Render a single chat message"""
    css_class = "user-message" if role == "user" else "assistant-message"
    icon = "👤" if role == "user" else "🏥"
    
    with st.chat_message(role, avatar=icon):
        st.markdown(content)
        if has_image:
            st.caption("📷 *Image attached*")


def render_doctor_cards(doctors: list):
    """Render doctor selection cards"""
    st.markdown("### 👨‍⚕️ Available Doctors")
    
    for i, doc in enumerate(doctors):
        with st.container():
            col1, col2, col3 = st.columns([3, 2, 1])
            
            with col1:
                st.markdown(f"**{doc['doctor_name']}**")
                st.caption(f"🏥 {doc['hospital_name']}, {doc['hospital_locality']}")
                st.caption(f"🩺 {doc['specialization']}")
            
            with col2:
                wait_mins = doc.get('estimated_wait_mins', 0)
                queue = doc.get('queue_length', 0)
                fee = doc.get('consultation_fee', 'Free')
                
                # Color code wait time
                if wait_mins < 30:
                    wait_color = "green"
                elif wait_mins < 60:
                    wait_color = "orange"
                else:
                    wait_color = "red"
                
                st.markdown(f"⏱️ Wait: :{wait_color}[~{wait_mins} mins]")
                st.caption(f"👥 Queue: {queue} patients")
                st.caption(f"💰 Fee: {fee}")
            
            with col3:
                if st.button("Book", key=f"book_{doc['doctor_id']}_{i}", type="primary"):
                    return doc
    
    return None


def render_chat_interface():
    """Render the main chat interface"""
    st.markdown("### 💬 Chat with MELCO-Care")
    
    # Display chat history
    for msg in st.session_state.messages:
        render_chat_message(msg["role"], msg["content"], msg.get("has_image", False))
    
    # Doctor options if available
    if st.session_state.current_doctor_options:
        selected_doctor = render_doctor_cards(st.session_state.current_doctor_options)
        
        if selected_doctor:
            # Book appointment
            result = api_book_appointment(
                user_id=st.session_state.user_id,
                doctor_id=selected_doctor["doctor_id"],
                symptoms=st.session_state.pending_symptoms or "General consultation",
                symptoms_summary=st.session_state.pending_symptoms or "General consultation",
                priority="medium"
            )
            
            if result.get("success"):
                st.success(f"""
                ✅ **Appointment Booked!**
                - Doctor: {selected_doctor['doctor_name']}
                - Token Number: {result.get('token_number')}
                - Hospital: {selected_doctor['hospital_name']}
                """)
                st.session_state.current_doctor_options = None
                st.session_state.pending_symptoms = None
            else:
                st.error(f"Failed to book: {result.get('message')}")
    
    # Chat input
    st.markdown("---")
    
    col1, col2 = st.columns([4, 1])
    
    with col1:
        user_input = st.chat_input("Type your symptoms or ask a question...")
    
    with col2:
        uploaded_image = st.file_uploader(
            "📷",
            type=["jpg", "jpeg", "png"],
            label_visibility="collapsed",
            key="image_upload"
        )
    
    if user_input:
        # Add user message
        st.session_state.messages.append({
            "role": "user",
            "content": user_input,
            "has_image": uploaded_image is not None
        })
        
        # Call API
        with st.spinner("MELCO-Care is thinking..."):
            if uploaded_image:
                result = api_chat_with_image(
                    st.session_state.user_id,
                    user_input,
                    uploaded_image
                )
            else:
                result = api_chat(st.session_state.user_id, user_input)
        
        # Process response
        response_text = result.get("response", "Sorry, I couldn't process that.")
        
        # Add assistant message
        st.session_state.messages.append({
            "role": "assistant",
            "content": response_text
        })
        
        # Store doctor options if available
        if result.get("doctor_options"):
            st.session_state.current_doctor_options = result["doctor_options"]
            st.session_state.pending_symptoms = user_input
        
        st.rerun()


def render_admin_dashboard():
    """Render admin dashboard"""
    st.markdown("### 🏥 Hospital Management")
    
    # System status
    status = api_get_system_status()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Database", status.get("database_status", "unknown").upper())
    with col2:
        st.metric("Ollama", status.get("ollama_status", "unknown").upper())
    with col3:
        st.metric("Total Users", status.get("total_users", 0))
    with col4:
        st.metric("Total Hospitals", status.get("total_hospitals", 0))
    
    st.markdown("---")
    
    # Hospital list
    st.markdown("### Hospital List")
    hospitals = api_get_hospitals()
    
    if hospitals:
        for h in hospitals:
            with st.expander(f"🏥 {h['name']} - {h['locality']}"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Beds", h["total_beds"])
                with col2:
                    st.metric("Occupied", h["occupied_beds"])
                with col3:
                    st.metric("Available", h["available_beds"])
                
                badge = "🏛️ Government" if h["is_government"] else "🏢 Private"
                st.caption(badge)
    else:
        st.info("No hospitals found")


def render_doctor_dashboard():
    """Render doctor dashboard"""
    st.markdown("### 👨‍⚕️ Doctor Dashboard")
    
    st.info("🚧 Doctor queue management coming soon!")
    
    # Placeholder for doctor-specific features
    st.markdown("""
    **Coming Soon:**
    - View your patient queue
    - Update consultation status
    - View patient symptoms and history
    - Mark appointments as complete
    """)


def render_sidebar():
    """Render sidebar"""
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.user_name}")
        st.caption(f"Role: {st.session_state.user_role.capitalize()}")
        st.caption(f"ID: {st.session_state.user_id}")
        
        st.markdown("---")
        
        # Navigation based on role
        if st.session_state.user_role == "admin":
            page = st.radio(
                "Navigate",
                ["Dashboard", "Chat"],
                key="nav"
            )
        elif st.session_state.user_role == "doctor":
            page = st.radio(
                "Navigate",
                ["My Queue", "Chat"],
                key="nav"
            )
        else:
            page = "Chat"
        
        st.markdown("---")
        
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.user_id = None
            st.session_state.user_role = None
            st.session_state.messages = []
            st.rerun()
        
        return page


# ============== MAIN APP ==============

def main():
    """Main application entry point"""
    init_session_state()
    
    if not st.session_state.logged_in:
        render_login_page()
    else:
        page = render_sidebar()
        
        # Header
        st.markdown("""
        <div style="display: flex; align-items: center; margin-bottom: 1rem;">
            <span style="font-size: 2rem; margin-right: 0.5rem;">🏥</span>
            <span style="font-size: 1.5rem; font-weight: bold; color: #1976d2;">MELCO-Care</span>
        </div>
        """, unsafe_allow_html=True)
        
        # Render appropriate page
        if page == "Dashboard":
            render_admin_dashboard()
        elif page == "My Queue":
            render_doctor_dashboard()
        else:
            render_chat_interface()


if __name__ == "__main__":
    main()
