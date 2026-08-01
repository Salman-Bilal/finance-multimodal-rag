import os
import html
import requests
import streamlit as st

# --- API Configuration ---
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")

st.set_page_config(
    page_title="Multimodal RAG Platform",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ===================================================================
# 🎨 GLOBAL STYLING
# ===================================================================
def inject_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&family=Inter:wght@400;500;600&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }
        h1, h2, h3, .app-title, .room-title {
            font-family: 'Poppins', sans-serif;
        }

        /* ---- App background ---- */
        .stApp {
            background: radial-gradient(circle at 10% 0%, #1b1035 0%, #0d0b1e 45%, #0a0913 100%);
            color: #EAEAF5;
        }

        /* ---- Hide default streamlit chrome ---- */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {background: transparent !important;}

        /* ---- Hero banner ---- */
        .hero-banner {
            padding: 26px 32px;
            border-radius: 18px;
            background: linear-gradient(120deg, #6C3EF4 0%, #A24BF0 45%, #F45DA8 100%);
            box-shadow: 0 10px 35px rgba(124, 58, 237, 0.35);
            margin-bottom: 22px;
        }
        .hero-banner h1 {
            color: white;
            font-weight: 800;
            font-size: 30px;
            margin: 0;
        }
        .hero-banner p {
            color: rgba(255,255,255,0.9);
            margin: 4px 0 0 0;
            font-size: 15px;
        }

        /* ---- Auth card (native st.container(border=True)) ---- */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(div[data-testid="stTabs"]) {
            background: rgba(255,255,255,0.045);
            border: 1px solid rgba(168,85,247,0.22) !important;
            backdrop-filter: blur(14px);
            border-radius: 20px !important;
            padding: 12px 8px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.45);
        }

        /* ---- Tabs: match the purple/pink theme ---- */
        .stTabs [data-baseweb="tab-list"] {
            gap: 4px;
            background: transparent;
        }
        .stTabs [data-baseweb="tab"] {
            color: #9C8FB5;
            font-weight: 600;
            font-size: 14px;
        }
        .stTabs [aria-selected="true"] {
            color: #E9D5FF !important;
        }
        .stTabs [data-baseweb="tab-highlight"] {
            background: linear-gradient(120deg, #7C3AED, #EC4899) !important;
            height: 3px;
            border-radius: 3px;
        }
        .stTabs [data-baseweb="tab-border"] {
            background: rgba(255,255,255,0.08) !important;
        }

        /* ---- Text inputs ---- */
        .stTextInput input {
            background: rgba(255,255,255,0.04) !important;
            border: 1px solid rgba(255,255,255,0.12) !important;
            border-radius: 10px !important;
            color: #EAEAF5 !important;
        }
        .stTextInput input:focus {
            border-color: #A855F7 !important;
            box-shadow: 0 0 0 3px rgba(168,85,247,0.20) !important;
        }
        .stTextInput label {
            color: #C9B8E0 !important;
            font-weight: 600;
            font-size: 13px;
        }

        /* ---- Buttons ---- */
        .stButton > button {
            border-radius: 10px !important;
            border: none !important;
            font-weight: 600 !important;
            transition: all 0.2s ease-in-out !important;
        }
        .stButton > button[kind="primary"] {
            background: linear-gradient(120deg, #7C3AED, #EC4899) !important;
            color: white !important;
            box-shadow: 0 6px 18px rgba(124, 58, 237, 0.4) !important;
        }
        .stButton > button[kind="primary"]:hover {
            transform: translateY(-1px);
            box-shadow: 0 10px 24px rgba(124, 58, 237, 0.55) !important;
        }
        .stButton > button[kind="secondary"] {
            background: rgba(255,255,255,0.06) !important;
            color: #EAEAF5 !important;
            border: 1px solid rgba(255,255,255,0.12) !important;
        }
        .stButton > button:hover {
            filter: brightness(1.08);
        }

        /* ---- Sidebar ---- */
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #150E2B 0%, #0D0A1D 100%);
            border-right: 1px solid rgba(255,255,255,0.06);
        }
        section[data-testid="stSidebar"] .stSubheader, section[data-testid="stSidebar"] h3 {
            color: #C9A9FF;
        }

        /* ---- User pill in sidebar ---- */
        .user-pill {
            display: flex;
            align-items: center;
            gap: 10px;
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.08);
            padding: 10px 14px;
            border-radius: 14px;
            margin-bottom: 14px;
        }
        .user-pill .avatar {
            width: 36px; height: 36px;
            border-radius: 50%;
            background: linear-gradient(120deg, #7C3AED, #EC4899);
            display: flex; align-items: center; justify-content: center;
            font-weight: 700;
            color: white;
            font-size: 15px;
        }
        .user-pill .uname {
            font-weight: 600;
            color: #EAEAF5;
            font-size: 15px;
        }

        /* ---- Status badges ---- */
        .status-badge {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            padding: 3px 9px;
            border-radius: 999px;
            font-size: 11px;
            font-weight: 600;
            white-space: nowrap;
            flex-shrink: 0;
        }
        .badge-ready { background: rgba(34,197,94,0.18); color: #4ADE80; border: 1px solid rgba(74,222,128,0.35); }
        .badge-failed { background: rgba(239,68,68,0.18); color: #F87171; border: 1px solid rgba(248,113,113,0.35); }
        .badge-processing { background: rgba(234,179,8,0.18); color: #FACC15; border: 1px solid rgba(250,204,21,0.35); }

        .file-row {
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.06);
            border-radius: 10px;
            padding: 9px 12px;
            margin-bottom: 6px;
            width: 100%;
            max-width: 100%;
            box-sizing: border-box;
            overflow: hidden;
        }
        .file-row .fname {
            display: block;
            font-size: 12.5px;
            color: #EAEAF5;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            max-width: 100%;
            margin-bottom: 6px;
        }
        .file-row .fbadge-wrap {
            display: flex;
            justify-content: flex-end;
        }

        /* ---- Sidebar overflow protection ---- */
        section[data-testid="stSidebar"] * {
            min-width: 0;
        }

        /* ---- Room header ---- */
        .room-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 9px 22px;
            border-radius: 12px;
            background: linear-gradient(120deg, rgba(124,58,237,0.18), rgba(236,72,153,0.12));
            border: 1px solid rgba(255,255,255,0.08);
            margin-bottom: 18px;
        }
        .room-header .room-title {
            font-size: 22px;
            font-weight: 700;
            color: #F3E8FF;
            margin: 0;
        }

        /* ---- Block container spacing ---- */
        .block-container {
            padding-top: 1.6rem !important;
            max-width: 980px;
        }

        /* ---- Chat bubbles ---- */
        div[data-testid="stChatMessage"] {
            background: rgba(255,255,255,0.045);
            border: 1px solid rgba(168,85,247,0.18);
            border-radius: 14px;
            padding: 14px 16px !important;
            margin-bottom: 12px;
            box-shadow: 0 4px 16px rgba(0,0,0,0.25);
        }
        div[data-testid="stChatMessage"]:has(div[data-testid="stChatMessageAvatarUser"]) {
            background: rgba(124,58,237,0.10);
            border-color: rgba(124,58,237,0.30);
        }
        div[data-testid="stChatMessage"]:has(div[data-testid="stChatMessageAvatarAssistant"]) {
            background: rgba(236,72,153,0.08);
            border-color: rgba(236,72,153,0.22);
        }

        /* ---- Avatar icons ---- */
        [data-testid="stChatMessageAvatarUser"],
        [data-testid="stChatMessageAvatarAssistant"] {
            border-radius: 10px !important;
        }
        [data-testid="stChatMessageAvatarUser"] {
            background: linear-gradient(135deg, #7C3AED, #A855F7) !important;
        }
        [data-testid="stChatMessageAvatarAssistant"] {
            background: linear-gradient(135deg, #EC4899, #F97316) !important;
        }

        /* ---- Sources expander ---- */
        div[data-testid="stChatMessage"] div[data-testid="stExpander"] {
            background: rgba(0,0,0,0.18);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 12px;
            margin-top: 6px;
            overflow: hidden;
        }
        div[data-testid="stChatMessage"] div[data-testid="stExpander"] summary {
            padding: 10px 14px !important;
            font-weight: 600;
            font-size: 13px;
            color: #E9D5FF;
        }
        div[data-testid="stChatMessage"] div[data-testid="stExpander"] summary:hover {
            background: rgba(168,85,247,0.08);
        }

        /* ---- Sources card ---- */
        .source-card {
            background: rgba(124,58,237,0.10);
            border: 1px solid rgba(168,85,247,0.16);
            border-left: 3px solid #A855F7;
            border-radius: 8px;
            padding: 10px 14px;
            margin-bottom: 8px;
        }
        .source-card:last-child {
            margin-bottom: 0;
        }
        .source-card .src-title {
            font-weight: 600;
            font-size: 13px;
            color: #E9D5FF;
        }
        .source-card .src-meta {
            font-size: 11px;
            color: #B9A6D9;
            margin-bottom: 4px;
        }
        .source-card .src-excerpt {
            font-size: 12.5px;
            color: #D7CCEE;
            font-style: italic;
        }

        /* ---- Divider ---- */
        hr {
            border-color: rgba(255,255,255,0.08) !important;
            margin: 0.9rem 0 !important;
        }

        /* ---- Empty state ---- */
        .empty-state {
            text-align: center;
            padding: 48px 20px;
            color: #B9A6D9;
            background: rgba(255,255,255,0.03);
            border: 1px dashed rgba(168,85,247,0.25);
            border-radius: 16px;
        }
        .empty-state h3 {
            color: #E9D5FF;
            margin-bottom: 6px;
        }
    </style>
    """, unsafe_allow_html=True)


# --- Session State Initialization ---
if "jwt_token" not in st.session_state:
    st.session_state["jwt_token"] = None
if "current_room_id" not in st.session_state:
    st.session_state["current_room_id"] = None
if "current_room_name" not in st.session_state:
    st.session_state["current_room_name"] = None
if "username" not in st.session_state:
    st.session_state["username"] = None
if "display_name" not in st.session_state:
    st.session_state["display_name"] = None


def get_auth_headers():
    """Helper to inject JWT token in request headers."""
    if st.session_state.get("jwt_token"):
        return {"Authorization": f"Bearer {st.session_state['jwt_token']}"}
    return {}


def _decode_jwt_claims(token):
    """Best-effort decode of a JWT payload (no signature check)."""
    import base64
    import json
    try:
        payload_b64 = token.split(".")[1]
        padded = payload_b64 + "=" * (-len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded))
        return payload
    except Exception:
        return {}


def resolve_display_name(fallback_email, headers):
    """Figures out the user's real display name."""
    for endpoint in ("/auth/me", "/users/me", "/me"):
        try:
            r = requests.get(f"{API_BASE_URL}{endpoint}", headers=headers, timeout=3)
            if r.status_code == 200:
                data = r.json()
                name = data.get("username") or data.get("name") or data.get("full_name")
                if name:
                    return name
        except Exception:
            pass

    claims = _decode_jwt_claims(st.session_state.get("jwt_token", ""))
    name = claims.get("username") or claims.get("name")
    if name:
        return name

    if fallback_email and "@" in fallback_email:
        return fallback_email.split("@")[0]
    return fallback_email or "User"


# ===================================================================
# 🔑 AUTH VIEWS (LOGIN & REGISTER)
# ===================================================================
def render_auth_ui():
    st.markdown("""
        <div class="hero-banner" style="text-align:center;">
            <h1>🤖 Multimodal Knowledge Engine</h1>
            <p>Log in or register to access grounded, multimodal AI workspaces.</p>
        </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.4, 1])
    with col2:
        with st.container(border=True):
            tab_login, tab_register = st.tabs(["🔑  Login", "📝  Register"])

            with tab_login:
                st.markdown("#### Welcome back")
                st.caption("Sign in to continue to your workspaces.")
                login_username = st.text_input("Email", key="login_user", placeholder="you@example.com")
                login_password = st.text_input("Password", type="password", key="login_pass", placeholder="••••••••")

                if st.button("Log In", type="primary", use_container_width=True):
                    if not login_username or not login_password:
                        st.error("Please provide both username and password.")
                    else:
                        try:
                            response = requests.post(
                                f"{API_BASE_URL}/auth/login",
                                data={"username": login_username, "password": login_password}
                            )
                            if response.status_code == 200:
                                data = response.json()
                                st.session_state["jwt_token"] = data["access_token"]
                                st.session_state["username"] = login_username
                                st.session_state["display_name"] = resolve_display_name(
                                    login_username,
                                    {"Authorization": f"Bearer {data['access_token']}"}
                                )
                                st.success("Successfully authenticated!")
                                st.rerun()
                            else:
                                st.error(f"Login failed: {response.json().get('detail', 'Invalid credentials')}")
                        except Exception as e:
                            st.error(f"Failed to connect to backend: {e}")

            with tab_register:
                st.markdown("#### Create your account")
                st.caption("Join and start building grounded AI workspaces.")
                reg_username = st.text_input("Username", key="reg_user", placeholder="Choose a username")
                reg_email = st.text_input("Email", key="reg_email", placeholder="you@example.com")
                reg_password = st.text_input("Password", type="password", key="reg_pass", placeholder="••••••••")

                if st.button("Register Account", type="primary", use_container_width=True):
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
# 🏠 MAIN DASHBOARD
# ===================================================================
def render_main_ui():
    headers = get_auth_headers()

    # --- SIDEBAR SETUP ---
    with st.sidebar:
        shown_name = st.session_state.get("display_name") or st.session_state["username"] or "?"
        initials = shown_name[0].upper()
        st.markdown(f"""
            <div class="user-pill">
                <div class="avatar">{initials}</div>
                <div class="uname">{shown_name}</div>
            </div>
        """, unsafe_allow_html=True)

        if st.button("🚪 Logout", type="secondary", use_container_width=True):
            st.session_state["jwt_token"] = None
            st.session_state["current_room_id"] = None
            st.session_state["current_room_name"] = None
            st.session_state["username"] = None
            st.session_state["display_name"] = None
            st.rerun()

        st.divider()

        # --- ROOM DASHBOARD & SELECTION ---
        st.markdown("### 🏠 Workspaces & Rooms")
        rooms = []
        try:
            res = requests.get(f"{API_BASE_URL}/rooms/", headers=headers)
            if res.status_code == 200:
                rooms = res.json()
        except Exception:
            st.error("Unable to load room list.")

        room_map = {f"{r['name']} (ID: {r['id']})": r['id'] for r in rooms}
        room_names_by_id = {r['id']: r['name'] for r in rooms}

        if room_map:
            selected_room_label = st.selectbox(
                "Select Workspace Room:",
                options=list(room_map.keys())
            )
            selected_id = room_map[selected_room_label]
            st.session_state["current_room_id"] = selected_id
            st.session_state["current_room_name"] = room_names_by_id.get(selected_id)
        else:
            st.info("No workspaces available. Create one below!")
            st.session_state["current_room_id"] = None
            st.session_state["current_room_name"] = None

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

        # --- MULTIMODAL FILE UPLOADER & STATUS BADGES ---
        current_room_id = st.session_state["current_room_id"]

        if current_room_id:
            st.markdown("### 📁 Upload Documents")
            # ⚡ Updated allowed extensions list to include all multimodal & media formats
            uploaded_file = st.file_uploader(
                "Supported Formats:",
                type=[
                    "pdf", "csv", "xlsx", "txt", "docx", "pptx", "ppt", "md",
                    "png", "jpg", "jpeg", "bmp", "webp",
                    "mp3", "wav", "mp4", "m4a", "avi",
                    "json", "html"
                ]
            )

            if uploaded_file is not None:
                if st.button("📤 Submit for Vectorization", type="primary", use_container_width=True):
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
            st.markdown("### 📊 Document Status")
            try:
                doc_res = requests.get(f"{API_BASE_URL}/upload/{current_room_id}/files", headers=headers)
                if doc_res.status_code == 200:
                    files_list = doc_res.json()
                    if files_list:
                        for f in files_list:
                            status = f.get("status", "processing")
                            if status == "ready":
                                badge_html = '<span class="status-badge badge-ready">🟢 Ready</span>'
                            elif status == "failed":
                                badge_html = '<span class="status-badge badge-failed">🔴 Failed</span>'
                            else:
                                badge_html = '<span class="status-badge badge-processing">🟡 Processing</span>'
                            safe_name = html.escape(f["filename"])
                            st.markdown(
                                f'''<div class="file-row">
                                        <span class="fname" title="{safe_name}">📄 {safe_name}</span>
                                        <div class="fbadge-wrap">{badge_html}</div>
                                    </div>''',
                                unsafe_allow_html=True
                            )
                    else:
                        st.caption("No files uploaded to this room yet.")
            except Exception:
                st.caption("Could not load file dashboard.")

    # --- MAIN CHAT INTERFACE ---
    current_room_id = st.session_state["current_room_id"]

    if not current_room_id:
        st.markdown("""
            <div class="hero-banner">
                <h1>🤖 Multimodal Knowledge Engine</h1>
                <p>Your grounded AI workspace, powered by your own documents.</p>
            </div>
        """, unsafe_allow_html=True)
        st.markdown("""
            <div class="empty-state">
                <h3>👈 Select or create a Workspace Room</h3>
                <p>Once you pick a room from the sidebar, you can upload documents and start chatting.</p>
            </div>
        """, unsafe_allow_html=True)
        return

    # Header Controls
    current_room_name = st.session_state.get("current_room_name") or f"Room #{current_room_id}"
    col_title, col_action = st.columns([4, 1])
    with col_title:
        st.markdown(f"""
            <div class="room-header">
                <p class="room-title">💬 {current_room_name} <span style="font-size:13px; font-weight:500; color:#B9A6D9;">(ID: {current_room_id})</span></p>
            </div>
        """, unsafe_allow_html=True)
    with col_action:
        if st.button("🗑️ Clear History", type="secondary", use_container_width=True):
            del_res = requests.delete(f"{API_BASE_URL}/chat/{current_room_id}/history", headers=headers)
            if del_res.status_code == 200:
                st.toast("Chat history cleared!")
                st.rerun()
            else:
                st.error("Failed to clear history.")

    # --- CHAT INTERFACE & SAFE SOURCES EXPANDER ---
    def render_sources(sources):
        with st.expander("📚 Sources"):
            if sources:
                for idx, src in enumerate(sources, start=1):
                    filename = src.get("filename", "Unknown File")
                    file_type = src.get("file_type", "Unknown").upper()
                    chunk_idx = src.get("chunk_index", 0)
                    
                    # ⚡ Safe retrieval of excerpt preventing KeyError
                    excerpt = src.get("excerpt") or src.get("content") or "No excerpt available."
                    if len(excerpt) > 200:
                        excerpt = excerpt[:200] + "..."

                    st.markdown(f"""
                        <div class="source-card">
                            <div class="src-title">{idx}. {filename}</div>
                            <div class="src-meta">Type: {file_type} · Chunk Index: {chunk_idx}</div>
                            <div class="src-excerpt">"{html.escape(excerpt)}"</div>
                        </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("No sources cited for this answer.")

    # Load Room History
    chat_history = []
    try:
        hist_res = requests.get(f"{API_BASE_URL}/chat/{current_room_id}/history", headers=headers)
        if hist_res.status_code == 200:
            chat_history = hist_res.json()
    except Exception as e:
        st.error(f"Failed to fetch conversation history: {e}")

    # Render Messages
    if not chat_history:
        st.markdown("""
            <div class="empty-state">
                <h3>💭 No messages yet</h3>
                <p>Ask a question below to get started — answers will be grounded in your uploaded documents.</p>
            </div>
        """, unsafe_allow_html=True)

    for msg in chat_history:
        role = msg["role"]
        content = msg["content"]
        sources = msg.get("sources") or []

        avatar = "🧑‍💻" if role == "user" else "🤖"
        with st.chat_message(role, avatar=avatar):
            st.write(content)
            if role == "assistant":
                render_sources(sources)

    # User Input Box
    user_query = st.chat_input("Ask a question based on uploaded documents...")
    if user_query:
        # Display user prompt instantly
        with st.chat_message("user", avatar="🧑‍💻"):
            st.write(user_query)

        # Trigger RAG Backend API Call
        with st.chat_message("assistant", avatar="🤖"):
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
                        render_sources(sources)

                        st.rerun()
                    else:
                        st.error(f"Error: {chat_res.json().get('detail', 'Failed to generate response')}")
                except Exception as e:
                    st.error(f"Communication error with backend: {e}")


# ===================================================================
# 🚀 ENTRYPOINT
# ===================================================================
if __name__ == "__main__":
    inject_css()
    if st.session_state["jwt_token"] is None:
        render_auth_ui()
    else:
        render_main_ui()