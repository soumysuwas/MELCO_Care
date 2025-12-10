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
    # Pharmacy state
    if "pharmacy_results" not in st.session_state:
        st.session_state.pharmacy_results = None
    if "prescription_data" not in st.session_state:
        st.session_state.prescription_data = None
    if "show_reservations" not in st.session_state:
        st.session_state.show_reservations = False


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


def api_validate_prescription(user_id: int, image_file):
    """Validate prescription via OCR"""
    try:
        files = {"image": image_file}
        data = {"user_id": str(user_id)}
        response = requests.post(
            f"{API_BASE_URL}/pharmacy/validate-prescription",
            files=files,
            data=data,
            timeout=120
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": f"Error: {str(e)}"}


def api_search_medicines(user_id: int, medicines: list, max_distance: float = 10.0):
    """Search for medicines at nearby pharmacies"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/pharmacy/search",
            json={
                "user_id": user_id,
                "medicines": medicines,
                "max_distance_km": max_distance,
                "city": "Hyderabad"
            },
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"success": False, "pharmacies": [], "error": str(e)}


def api_list_pharmacies():
    """Get list of pharmacies"""
    try:
        response = requests.get(f"{API_BASE_URL}/pharmacy/list", timeout=10)
        response.raise_for_status()
        return response.json()
    except:
        return {"pharmacies": []}


def api_reserve_medicine(user_id: int, pharmacy_id: int, medicines: list):
    """Reserve medicines for pickup"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/pharmacy/reserve",
            json={
                "user_id": user_id,
                "pharmacy_id": pharmacy_id,
                "medicines": medicines
            },
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"success": False, "message": str(e)}


def api_get_reservations(user_id: int):
    """Get user's reservations"""
    try:
        response = requests.get(
            f"{API_BASE_URL}/pharmacy/reservations/{user_id}",
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except:
        return {"reservations": []}


def api_cancel_reservation(reservation_id: int, user_id: int):
    """Cancel a reservation"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/pharmacy/cancel/{reservation_id}",
            params={"user_id": user_id},
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"success": False, "message": str(e)}


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
    
    # Show reservations page if requested
    if st.session_state.get("show_reservations"):
        render_reservations()
        return
    
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
    
    # Pharmacy results if available
    if st.session_state.pharmacy_results:
        render_pharmacy_results(st.session_state.pharmacy_results)
    
    # Chat input
    st.markdown("---")
    
    # Prescription upload section
    with st.expander("📋 Upload Prescription", expanded=False):
        prescription_file = st.file_uploader(
            "Upload your prescription image",
            type=["jpg", "jpeg", "png"],
            key="prescription_upload",
            help="Upload a prescription to find medicines at nearby pharmacies"
        )
        
        if prescription_file:
            col1, col2 = st.columns([1, 1])
            with col1:
                st.image(prescription_file, caption="Uploaded Prescription", width=200)
            with col2:
                if st.button("🔍 Validate & Find Medicines", type="primary"):
                    with st.spinner("Analyzing prescription..."):
                        result = api_validate_prescription(
                            st.session_state.user_id,
                            prescription_file
                        )
                    
                    if result.get("valid"):
                        st.success("✅ Prescription validated!")
                        
                        # Show extracted data
                        extracted = result.get("extracted_data", {})
                        if extracted:
                            st.markdown("**Extracted Information:**")
                            if extracted.get("doctor_name"):
                                st.write(f"👨‍⚕️ Doctor: {extracted['doctor_name']}")
                            if extracted.get("reg_number"):
                                verified = "✅" if result.get("doctor_verified") else "❓"
                                st.write(f"🔖 Reg: {extracted['reg_number']} {verified}")
                        
                        # Search for medicines
                        medicines = result.get("medicines", [])
                        if medicines:
                            st.markdown(f"**Medicines Found:** {', '.join(medicines)}")
                            with st.spinner("Searching pharmacies..."):
                                pharmacy_result = api_search_medicines(
                                    st.session_state.user_id,
                                    medicines
                                )
                            st.session_state.pharmacy_results = pharmacy_result
                            st.rerun()
                    else:
                        st.error(f"❌ {result.get('error', 'Could not validate prescription')}")
    
    # Medicine search input
    with st.expander("💊 Search Medicine", expanded=False):
        medicine_input = st.text_input(
            "Enter medicine name(s)",
            placeholder="e.g., paracetamol, cetirizine",
            key="medicine_search"
        )
        if st.button("🔍 Search", key="search_med_btn"):
            if medicine_input:
                medicines = [m.strip() for m in medicine_input.split(",")]
                with st.spinner("Searching pharmacies..."):
                    result = api_search_medicines(
                        st.session_state.user_id,
                        medicines
                    )
                st.session_state.pharmacy_results = result
                st.rerun()
    
    # Regular chat input
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


def render_pharmacy_results(results: dict):
    """Render pharmacy search results"""
    st.markdown("### 💊 Pharmacy Results")
    
    pharmacies = results.get("pharmacies", [])
    
    if not pharmacies:
        st.warning("No pharmacies found with the requested medicines nearby.")
        if st.button("Clear Results"):
            st.session_state.pharmacy_results = None
            st.rerun()
        return
    
    # Summary
    all_found = results.get("all_found", False)
    missing = results.get("missing_medicines", [])
    
    if all_found:
        st.success("✅ All medicines are available!")
    elif missing:
        st.warning(f"⚠️ Some medicines may not be available: {', '.join(missing)}")
    
    # Display pharmacies
    for i, pharmacy in enumerate(pharmacies[:5]):
        with st.expander(
            f"🏪 {pharmacy['name']} ({pharmacy['distance_km']} km) - "
            f"{pharmacy['available_count']}/{len(pharmacy['medicines'])} medicines",
            expanded=(i == 0)
        ):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown(f"**📍 {pharmacy['address']}**")
                st.caption(f"⏰ {pharmacy['operating_hours']}")
                if pharmacy.get('phone'):
                    st.caption(f"📞 {pharmacy['phone']}")
                if pharmacy.get('is_24hr'):
                    st.caption("🌙 Open 24 Hours")
            
            with col2:
                st.metric("Distance", f"{pharmacy['distance_km']} km")
            
            # Medicine availability with quantity
            st.markdown("**Medicines:**")
            in_stock_meds = []
            for med in pharmacy['medicines']:
                if med['in_stock']:
                    st.markdown(f"✅ **{med['name']}** - ₹{med['price']} (Stock: {med['stock']})")
                    in_stock_meds.append(med)
                else:
                    st.markdown(f"❌ ~~{med['name']}~~ - Out of Stock")
            
            # Reserve button for pharmacies with available medicines
            if in_stock_meds:
                st.markdown("---")
                st.markdown("**🛒 Reserve for Pickup:**")
                
                # Build medicines list for reservation
                meds_to_reserve = []
                for med in in_stock_meds:
                    qty = st.number_input(
                        f"{med['name']} qty",
                        min_value=1,
                        max_value=min(5, med['stock']),
                        value=1,
                        key=f"qty_{pharmacy['pharmacy_id']}_{med['name']}"
                    )
                    meds_to_reserve.append({"name": med['name'], "quantity": qty})
                
                if st.button("📦 Reserve Now", key=f"reserve_{pharmacy['pharmacy_id']}", type="primary"):
                    result = api_reserve_medicine(
                        st.session_state.user_id,
                        pharmacy['pharmacy_id'],
                        meds_to_reserve
                    )
                    if result.get("success"):
                        st.success(f"""
                        ✅ **Reserved!**
                        - Pickup Code: **{result['pickup_code']}**
                        - Total: ₹{result['total_amount']}
                        - Expires: {result['expires_at'][:16].replace('T', ' ')}
                        - Show this code at {result['pharmacy_name']} within 1 hour!
                        """)
                        st.session_state.pharmacy_results = None
                        st.rerun()
                    else:
                        st.error(f"❌ {result.get('message', 'Reservation failed')}")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Clear Results", key="clear_pharmacy"):
            st.session_state.pharmacy_results = None
            st.rerun()
    with col2:
        if st.button("📋 My Reservations", key="view_reservations"):
            st.session_state.show_reservations = True
            st.rerun()


def render_reservations():
    """Show user's reservations"""
    st.markdown("### 📋 My Reservations")
    
    reservations = api_get_reservations(st.session_state.user_id)
    res_list = reservations.get("reservations", [])
    
    if not res_list:
        st.info("No reservations yet.")
        if st.button("← Back"):
            st.session_state.show_reservations = False
            st.rerun()
        return
    
    for res in res_list:
        status_emoji = {
            "pending": "⏳",
            "picked_up": "✅",
            "cancelled": "❌",
            "expired": "⌛"
        }.get(res['status'], "❓")
        
        with st.expander(f"{status_emoji} {res['pharmacy_name']} - ₹{res['total_amount']}", expanded=(res['status'] == 'pending')):
            st.markdown(f"**Status:** {res['status'].upper()}")
            
            if res['status'] == 'pending':
                st.markdown(f"**🔑 Pickup Code: `{res['pickup_code']}`**")
                st.caption(f"⏰ Expires: {res['expires_at'][:16].replace('T', ' ')}")
            
            st.markdown("**Medicines:**")
            for med in res['medicines']:
                st.write(f"- {med['name']} x{med['quantity']} = ₹{med['total']}")
            
            if res['status'] == 'pending':
                if st.button("❌ Cancel", key=f"cancel_{res['reservation_id']}"):
                    result = api_cancel_reservation(res['reservation_id'], st.session_state.user_id)
                    if result.get("success"):
                        st.success("Cancelled!")
                        st.rerun()
                    else:
                        st.error(result.get("message", "Failed"))
    
    if st.button("← Back to Chat"):
        st.session_state.show_reservations = False
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
