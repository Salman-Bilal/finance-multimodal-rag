import os
import requests
import streamlit as st

# --- API Configuration ---
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")

st.set_page_config(
    page_title="Multimodal RAG Platform",
    page_icon="🤖",
    layout="wide"
)

# --- Session State Initialization ---
if "jwt_token" not in st.session_state:
    st.session_state["jwt_token"] = None
if "current_room_id" not in st.session_state:
    st.session_state["current_room_id"] = None
if "username" not in st.session_state:
    st.session_state["username"] = None


def get_auth_headers():
    """Helper to inject JWT token in request headers."""
    if st.session_state.get("jwt_token"):
        return {"Authorization": f"Bearer {st.session_state['jwt_token']}"}
    return {}


# ===================================================================
# 🔑 TASK 4.1 — AUTH VIEWS (LOGIN & REGISTER)
# ===================================================================
def render_auth_ui():
    st.title("🤖 Multimodal Knowledge Engine")
    st.caption("Log in or register to access grounded AI workspaces.")

    tab_login, tab_register = st.tabs(["🔑 Login", "📝 Register"])

    with tab_login:
        st.subheader("Login to your Account")
        login_username = st.text_input("Username", key="login_user")
        login_password = st.text_input("Password", type="password", key="login_pass")

        if st.button("Log In", type="primary", use_container_width=True):
            if not login_username or not login_password:
                st.error("Please provide both username and password.")
            else:
                try:
                    # Form-data post for OAuth2 compliance
                    response = requests.post(
                        f"{API_BASE_URL}/auth/login",
                        data={"username": login_username, "password": login_password}
                    )
                    if response.status_code == 200:
                        data = response.json()
                        st.session_state["jwt_token"] = data["access_token"]
                        st.session_state["username"] = login_username
                        st.success("Successfully authenticated!")
                        st.rerun()
                    else:
                        st.error(f"Login failed: {response.json().get('detail', 'Invalid credentials')}")
                except Exception as e:
                    st.error(f"Failed to connect to backend: {e}")

    with tab_register:
        st.subheader("Create a New Account")
        reg_username = st.text_input("Username", key="reg_user")
        reg_email = st.text_input("Email", key="reg_email")
        reg_password = st.text_input("Password", type="password", key="reg_pass")

        if st.button("Register Account", use_container_width=True):
            if not reg_username or not reg_email or not reg_password:
                st.error("All fields are required.")
            else:
                try:
                    response = requests.post(
                        f"{API_BASE_URL}/auth/register",
                        json={"username": reg_username, "email": reg_email, "password": reg_password}
                    )
                    if response.status_code in (200, 201):
                        st.success("Registration successful! You can now log in.")
                    else:
                        st.error(f"Registration failed: {response.json().get('detail', 'Error occurred')}")
                except Exception as e:
                    st.error(f"Failed to connect to backend: {e}")


# ===================================================================
# 🏠 MAIN DASHBOARD (TASKS 4.2, 4.3, 4.4)
# ===================================================================
def render_main_ui():
    headers = get_auth_headers()

    # --- SIDEBAR SETUP ---
    with st.sidebar:
        st.title(f"👤 {st.session_state['username']}")
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state["jwt_token"] = None
            st.session_state["current_room_id"] = None
            st.session_state["username"] = None
            st.rerun()

        st.divider()

        # -----------------------------------------------------------
        # TASK 4.2 — ROOM DASHBOARD & SELECTION
        # -----------------------------------------------------------
        st.subheader("🏠 Workspaces & Rooms")
        rooms = []
        try:
            res = requests.get(f"{API_BASE_URL}/rooms/", headers=headers)
            if res.status_code == 200:
                rooms = res.json()
        except Exception:
            st.error("Unable to load room list.")

        room_map = {f"{r['name']} (ID: {r['id']})": r['id'] for r in rooms}

        if room_map:
            selected_room_label = st.selectbox(
                "Select Workspace Room:",
                options=list(room_map.keys())
            )
            st.session_state["current_room_id"] = room_map[selected_room_label]
        else:
            st.info("No workspaces available. Create one below!")
            st.session_state["current_room_id"] = None

        # Form to Create New Room
        with st.expander("➕ Create New Room"):
            new_room_name = st.text_input("Room Name")
            new_room_desc = st.text_input("Description (optional)")
            if st.button("Create Room", type="primary", use_container_width=True):
                if new_room_name.strip():
                    r_res = requests.post(
                        f"{API_BASE_URL}/rooms/",
                        headers=headers,
                        json={"name": new_room_name.strip(), "description": new_room_desc.strip()}
                    )
                    if r_res.status_code in (200, 201):
                        st.success("Room created!")
                        st.rerun()
                    else:
                        st.error("Failed to create room.")
                else:
                    st.warning("Room name cannot be empty.")

        st.divider()

        # -----------------------------------------------------------
        # TASK 4.3 — ROOM SIDEBAR (FILE UPLOADER & STATUS BADGES)
        # -----------------------------------------------------------
        current_room_id = st.session_state["current_room_id"]

        if current_room_id:
            st.subheader("📁 Upload Documents")
            # Supporting all 9 requested formats
            uploaded_file = st.file_uploader(
                "Supported Formats:",
                type=["pdf", "txt", "csv", "docx", "xlsx", "pptx", "md", "json", "html"]
            )

            if uploaded_file is not None:
                if st.button("📤 Submit for Vectorization", use_container_width=True):
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                    with st.spinner("Processing & indexing embeddings..."):
                        up_res = requests.post(
                            f"{API_BASE_URL}/upload/{current_room_id}",
                            headers=headers,
                            files=files
                        )
                        if up_res.status_code in (200, 201):
                            st.success(f"'{uploaded_file.name}' processed successfully!")
                            st.rerun()
                        else:
                            st.error(f"Upload failed: {up_res.json().get('detail', 'Error processing file')}")

            st.divider()
            st.subheader("📊 Document Status")
            try:
                doc_res = requests.get(f"{API_BASE_URL}/upload/{current_room_id}/files", headers=headers)
                if doc_res.status_code == 200:
                    files_list = doc_res.json()
                    if files_list:
                        for f in files_list:
                            status = f.get("status", "processing")
                            if status == "ready":
                                badge = "🟢 **Ready**"
                            elif status == "failed":
                                badge = "🔴 **Failed**"
                            else:
                                badge = "🟡 **Processing**"
                            st.markdown(f"📄 `{f['filename']}` — {badge}")
                    else:
                        st.caption("No files uploaded to this room yet.")
            except Exception:
                st.caption("Could not load file dashboard.")

    # --- MAIN CHAT INTERFACE ---
    current_room_id = st.session_state["current_room_id"]

    if not current_room_id:
        st.info("👈 Please select or create a Workspace Room from the sidebar to start chatting.")
        return

    # Header Controls
    col_title, col_action = st.columns([4, 1])
    with col_title:
        st.title(f"💬 Room Workspace #{current_room_id}")
    with col_action:
        if st.button("🗑️ Clear History", type="secondary", use_container_width=True):
            del_res = requests.delete(f"{API_BASE_URL}/chat/{current_room_id}/history", headers=headers)
            if del_res.status_code == 200:
                st.toast("Chat history cleared!")
                st.rerun()
            else:
                st.error("Failed to clear history.")

    # -----------------------------------------------------------
    # TASK 4.4 — CHAT INTERFACE & MANDATORY SOURCES EXPANDER
    # -----------------------------------------------------------
    # Load Room History on App Start / Rerun
    chat_history = []
    try:
        hist_res = requests.get(f"{API_BASE_URL}/chat/{current_room_id}/history", headers=headers)
        if hist_res.status_code == 200:
            chat_history = hist_res.json()
    except Exception as e:
        st.error(f"Failed to fetch conversation history: {e}")

    # Render Chronological Messages
    for msg in chat_history:
        role = msg["role"]
        content = msg["content"]
        sources = msg.get("sources") or []

        with st.chat_message(role):
            st.write(content)

            # Mandatory Sources Expander for Assistant Turns
            if role == "assistant":
                with st.expander("📚 Sources"):
                    if sources:
                        for idx, src in enumerate(sources, start=1):
                            st.markdown(
                                f"**{idx}. `{src['filename']}`** | Type: `{src['file_type']}` | Chunk Index: `{src['chunk_index']}`"
                            )
                            st.caption(f"Excerpt: \"{src['excerpt']}\"")
                    else:
                        st.info("No sources cited for this answer.")

    # User Input Box
    user_query = st.chat_input("Ask a question based on uploaded documents...")
    if user_query:
        # Display user prompt instantly
        with st.chat_message("user"):
            st.write(user_query)

        # Trigger RAG Backend API Call
        with st.chat_message("assistant"):
            with st.spinner("Searching documents & retrieving grounded context..."):
                try:
                    chat_res = requests.post(
                        f"{API_BASE_URL}/chat/{current_room_id}",
                        headers=headers,
                        json={"query": user_query}
                    )
                    if chat_res.status_code == 200:
                        data = chat_res.json()
                        answer = data["answer"]
                        sources = data.get("sources", [])

                        st.write(answer)

                        # Mandatory Sources Expander
                        with st.expander("📚 Sources"):
                            if sources:
                                for idx, src in enumerate(sources, start=1):
                                    st.markdown(
                                        f"**{idx}. `{src['filename']}`** | Type: `{src['file_type']}` | Chunk Index: `{src['chunk_index']}`"
                                    )
                                    st.caption(f"Excerpt: \"{src['excerpt']}\"")
                            else:
                                st.info("No sources cited for this answer.")

                        st.rerun()
                    else:
                        st.error(f"Error: {chat_res.json().get('detail', 'Failed to generate response')}")
                except Exception as e:
                    st.error(f"Communication error with backend: {e}")


# ===================================================================
# 🚀 ENTRYPOINT
# ===================================================================
if __name__ == "__main__":
    if st.session_state["jwt_token"] is None:
        render_auth_ui()
    else:
        render_main_ui()