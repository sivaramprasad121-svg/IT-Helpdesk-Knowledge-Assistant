
import json
import bcrypt
import pandas as pd
import streamlit as st

from database import (
    init_db,
    save_chat,
    get_all_chats,
    get_user_by_username,
    create_user,
    list_users,
    set_user_active,
    update_user_password,
    log_admin_action,
    set_admin_security_question,
    get_admin_recovery_data,
    reset_admin_password
)

from pdf_loader import load_pdf
from chunking import create_chunks
from embeddings import create_embeddings
from vector_store import create_vector_store
from retrieval import retrieve_relevant_chunks
from gemini_llm import generate_answer, get_gemini_api_key


# ==========================================
# PAGE CONFIGURATION
# ==========================================

st.set_page_config(
    page_title="PDF Knowledge Assistant",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

init_db()


# ==========================================
# DARK THEME
# ==========================================

st.markdown("""
<style>
.stApp {
    background-color: #0B0F19;
    color: #F9FAFB;
}

[data-testid="stSidebar"] {
    background-color: #111827;
}

h1, h2, h3, h4, p, label {
    color: #F9FAFB;
}

.welcome-card {
    background-color: #111827;
    border: 1px solid #263244;
    border-radius: 16px;
    padding: 25px;
    margin-bottom: 20px;
}

.info-card {
    background-color: #1F2937;
    border: 1px solid #374151;
    border-radius: 12px;
    padding: 15px;
    margin-bottom: 10px;
}

[data-testid="stChatMessage"] {
    background-color: #151C2B;
    border: 1px solid #263244;
    border-radius: 14px;
    padding: 16px;
}

.stButton > button {
    background-color: #2563EB;
    color: white;
    border-radius: 9px;
    border: none;
    min-height: 45px;
}
</style>
""", unsafe_allow_html=True)


# ==========================================
# SESSION STATE
# ==========================================

defaults = {
    "auth_user": None,
    "login_role": None,
    "messages": [],
    "processed": False,
    "vector_store": None,
    "embedding_model": None,
    "chunks": [],
    "uploaded_filename": None,
    "forgot_mode": False,
    "recovery_username": None,
    "recovery_verified": False,
    "recovery_question": None,
    "login_notice": None
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ==========================================
# PASSWORD VERIFICATION
# ==========================================

def verify_password(password, stored_hash):

    if isinstance(stored_hash, str):
        stored_hash = stored_hash.encode("utf-8")

    return bcrypt.checkpw(
        password.encode("utf-8"),
        stored_hash
    )


# ==========================================
# LOGOUT
# ==========================================

def logout():

    for key in list(st.session_state.keys()):
        del st.session_state[key]

    st.rerun()


# ==========================================
# LOGIN PAGE
# ==========================================

def login_page():

    if st.session_state.login_notice:

        st.success(st.session_state.login_notice)
        st.session_state.login_notice = None

    st.markdown("""
    <div class="welcome-card">
        <h1>📚 PDF Knowledge Assistant</h1>
        <p>Welcome to the AI-powered PDF Question Answering System.</p>
        <p>Please select your login type to continue.</p>
    </div>
    """, unsafe_allow_html=True)

    # SELECT LOGIN TYPE

    if st.session_state.login_role is None:

        st.markdown("## Select Login Type")

        col1, col2 = st.columns(2)

        with col1:

            if st.button(
                "🔐 Admin Login",
                use_container_width=True
            ):

                st.session_state.login_role = "admin"
                st.session_state.forgot_mode = False
                st.rerun()

        with col2:

            if st.button(
                "👤 User Login",
                use_container_width=True
            ):

                st.session_state.login_role = "user"
                st.session_state.forgot_mode = False
                st.rerun()

        return

    role = st.session_state.login_role

    # ======================================
    # FORGOT ADMIN PASSWORD
    # ======================================

    if role == "admin" and st.session_state.forgot_mode:

        st.subheader("🔑 Admin Password Recovery")

        if not st.session_state.recovery_username:

            with st.form("recovery_username_form"):

                recovery_username = st.text_input(
                    "Admin User ID",
                    placeholder="Enter your admin username"
                )

                find_question = st.form_submit_button(
                    "Continue",
                    use_container_width=True
                )

            if find_question:

                if not recovery_username.strip():

                    st.warning("Please enter your admin username.")

                else:

                    try:

                        recovery_data = get_admin_recovery_data(
                            recovery_username.strip()
                        )

                        if not recovery_data:

                            st.error(
                                "Admin account not found or inactive."
                            )

                        elif (
                            not recovery_data.get("security_question")
                            or not recovery_data.get("security_answer_hash")
                        ):

                            st.error(
                                "Security question is not configured. "
                                "Please contact the system administrator."
                            )

                        else:

                            st.session_state.recovery_username = (
                                recovery_data["username"]
                            )

                            st.session_state.recovery_question = (
                                recovery_data["security_question"]
                            )

                            st.rerun()

                    except Exception as error:

                        st.error(f"Recovery error: {error}")

        elif not st.session_state.recovery_verified:

            st.info(
                f"Security Question: "
                f"{st.session_state.recovery_question}"
            )

            with st.form("security_answer_form"):

                security_answer = st.text_input(
                    "Your Answer",
                    placeholder="Enter your security answer"
                )

                verify_button = st.form_submit_button(
                    "Verify Answer",
                    use_container_width=True
                )

            if verify_button:

                if not security_answer.strip():

                    st.warning("Please enter your answer.")

                else:

                    try:

                        recovery_data = get_admin_recovery_data(
                            st.session_state.recovery_username
                        )

                        if (
                            recovery_data
                            and verify_password(
                                security_answer.strip().casefold(),
                                recovery_data["security_answer_hash"]
                            )
                        ):

                            st.session_state.recovery_verified = True

                            st.success(
                                "Security answer verified!"
                            )

                            st.rerun()

                        else:

                            st.error("Incorrect security answer.")

                    except Exception as error:

                        st.error(
                            f"Verification error: {error}"
                        )

        else:

            st.success(
                "Identity verified. Set your new password."
            )

            with st.form("new_admin_password_form"):

                new_password = st.text_input(
                    "New Password",
                    type="password"
                )

                confirm_password = st.text_input(
                    "Confirm New Password",
                    type="password"
                )

                reset_button = st.form_submit_button(
                    "Reset Password",
                    use_container_width=True
                )

            if reset_button:

                if len(new_password) < 8:

                    st.warning(
                        "Password must contain at least 8 characters."
                    )

                elif new_password != confirm_password:

                    st.error("Passwords do not match.")

                else:

                    try:

                        password_hash = bcrypt.hashpw(
                            new_password.encode("utf-8"),
                            bcrypt.gensalt()
                        ).decode("utf-8")

                        reset_admin_password(
                            st.session_state.recovery_username,
                            password_hash
                        )

                        st.session_state.forgot_mode = False
                        st.session_state.recovery_username = None
                        st.session_state.recovery_question = None
                        st.session_state.recovery_verified = False

                        st.session_state.login_notice = (
                            "Admin password reset successfully. "
                            "Please login with your new password."
                        )

                        st.rerun()

                    except Exception as error:

                        st.error(
                            f"Password reset failed: {error}"
                        )

        if st.button(
            "⬅️ Back to Admin Login",
            use_container_width=True
        ):

            st.session_state.forgot_mode = False
            st.session_state.recovery_username = None
            st.session_state.recovery_question = None
            st.session_state.recovery_verified = False
            st.rerun()

        return

    # ======================================
    # NORMAL LOGIN
    # ======================================

    if role == "admin":

        st.subheader("🔐 Admin Login")

    else:

        st.subheader("👤 User Login")

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:

        with st.form("login_form"):

            username = st.text_input(
                "User ID",
                placeholder="Enter your User ID"
            )

            password = st.text_input(
                "Password",
                type="password",
                placeholder="Enter your password"
            )

            submitted = st.form_submit_button(
                "Login",
                use_container_width=True
            )

        # FORGOT PASSWORD - ADMIN ONLY

        if role == "admin":

            if st.button(
                "Forgot Password?",
                use_container_width=True
            ):

                st.session_state.forgot_mode = True
                st.session_state.recovery_username = None
                st.session_state.recovery_question = None
                st.session_state.recovery_verified = False
                st.rerun()

        if st.button(
            "⬅️ Back to Login Selection",
            use_container_width=True
        ):

            st.session_state.login_role = None
            st.session_state.forgot_mode = False
            st.rerun()

        if submitted:

            if not username.strip() or not password:

                st.warning(
                    "Please enter User ID and password."
                )

            else:

                try:

                    user = get_user_by_username(
                        username.strip()
                    )

                    if (
                        user
                        and user["role"] == role
                        and user["is_active"]
                        and verify_password(
                            password,
                            user["password_hash"]
                        )
                    ):

                        st.session_state.auth_user = {
                            "id": user["id"],
                            "username": user["username"],
                            "role": user["role"]
                        }

                        st.session_state.login_role = None
                        st.session_state.forgot_mode = False
                        st.session_state.messages = []
                        st.session_state.processed = False
                        st.session_state.vector_store = None
                        st.session_state.embedding_model = None
                        st.session_state.chunks = []
                        st.session_state.uploaded_filename = None

                        st.success("Login successful!")
                        st.rerun()

                    else:

                        st.error(
                            "Invalid credentials, incorrect login type, "
                            "or account is inactive."
                        )

                except Exception as error:

                    st.error(f"Login error: {error}")


# ==========================================
# ADMIN DASHBOARD
# ==========================================

def admin_dashboard():

    admin = st.session_state.auth_user

    st.title("🔐 Admin Dashboard")

    col1, col2 = st.columns([5, 1])

    with col1:

        st.success(
            f"Logged in as Admin: {admin['username']}"
        )

    with col2:

        if st.button("Logout"):
            logout()

    st.divider()

    tab1, tab2, tab3 = st.tabs([
        "👥 User Management",
        "📊 Chat Monitoring",
        "🔐 Security Settings"
    ])

    # ======================================
    # USER MANAGEMENT
    # ======================================

    with tab1:

        st.subheader("Create New User")

        with st.form("create_user_form"):

            new_username = st.text_input(
                "New User ID",
                placeholder="Example: user01"
            )

            new_password = st.text_input(
                "New User Password",
                type="password"
            )

            confirm_password = st.text_input(
                "Confirm Password",
                type="password"
            )

            create_button = st.form_submit_button(
                "Create User",
                use_container_width=True
            )

        if create_button:

            if not new_username.strip() or not new_password:

                st.warning("Please fill all fields.")

            elif len(new_password) < 8:

                st.warning(
                    "Password must contain at least 8 characters."
                )

            elif new_password != confirm_password:

                st.error("Passwords do not match.")

            else:

                try:

                    password_hash = bcrypt.hashpw(
                        new_password.encode("utf-8"),
                        bcrypt.gensalt()
                    ).decode("utf-8")

                    create_user(
                        new_username.strip(),
                        password_hash,
                        "user"
                    )

                    log_admin_action(
                        admin["id"],
                        "CREATE USER",
                        f"Created user: {new_username.strip()}"
                    )

                    st.success(
                        f"User {new_username.strip()} created successfully!"
                    )

                    st.rerun()

                except Exception as error:

                    st.error(
                        f"Unable to create user: {error}"
                    )

        st.divider()

        # DISPLAY USERS

        st.subheader("Existing Users")

        try:

            users = list_users()

            if users:

                users_df = pd.DataFrame(users)

                st.dataframe(
                    users_df,
                    use_container_width=True,
                    hide_index=True
                )

                normal_users = [
                    u for u in users
                    if u["role"] == "user"
                ]

                if normal_users:

                    st.divider()

                    st.subheader("Activate / Deactivate User")

                    selected_user = st.selectbox(
                        "Select User",
                        [u["username"] for u in normal_users]
                    )

                    selected_record = next(
                        u for u in normal_users
                        if u["username"] == selected_user
                    )

                    if selected_record["is_active"]:

                        if st.button("Deactivate Selected User"):

                            set_user_active(
                                selected_record["id"],
                                False
                            )

                            log_admin_action(
                                admin["id"],
                                "DEACTIVATE USER",
                                f"Deactivated: {selected_user}"
                            )

                            st.success("User deactivated.")
                            st.rerun()

                    else:

                        if st.button("Activate Selected User"):

                            set_user_active(
                                selected_record["id"],
                                True
                            )

                            log_admin_action(
                                admin["id"],
                                "ACTIVATE USER",
                                f"Activated: {selected_user}"
                            )

                            st.success("User activated.")
                            st.rerun()

                    st.divider()

                    st.subheader("Reset User Password")

                    with st.form("reset_password_form"):

                        reset_username = st.selectbox(
                            "Select User for Password Reset",
                            [u["username"] for u in normal_users],
                            key="reset_username"
                        )

                        new_reset_password = st.text_input(
                            "New Password",
                            type="password"
                        )

                        reset_confirm_password = st.text_input(
                            "Confirm New Password",
                            type="password"
                        )

                        reset_button = st.form_submit_button(
                            "Reset Password"
                        )

                    if reset_button:

                        if len(new_reset_password) < 8:

                            st.warning(
                                "Password must contain at least 8 characters."
                            )

                        elif new_reset_password != reset_confirm_password:

                            st.error("Passwords do not match.")

                        else:

                            password_hash = bcrypt.hashpw(
                                new_reset_password.encode("utf-8"),
                                bcrypt.gensalt()
                            ).decode("utf-8")

                            update_user_password(
                                reset_username,
                                password_hash
                            )

                            log_admin_action(
                                admin["id"],
                                "RESET PASSWORD",
                                f"Password reset for: {reset_username}"
                            )

                            st.success(
                                "Password reset successfully!"
                            )

                            st.rerun()

                else:

                    st.info("No normal users created yet.")

            else:

                st.info("No users found.")

        except Exception as error:

            st.error(
                f"User management error: {error}"
            )

    # ======================================
    # CHAT MONITORING
    # ======================================

    with tab2:

        st.subheader("📊 All User Chat Records")

        try:

            records = get_all_chats()

            if records:

                df = pd.DataFrame(records)

                df = df.rename(columns={
                    "username": "Username",
                    "pdf_name": "PDF Name",
                    "question": "Question",
                    "answer": "Answer",
                    "sources": "Sources",
                    "status": "Status",
                    "created_at": "Timestamp"
                })

                col1, col2, col3 = st.columns(3)

                col1.metric(
                    "Total Questions",
                    len(df)
                )

                col2.metric(
                    "Total Users",
                    df["Username"].nunique()
                )

                col3.metric(
                    "Successful Responses",
                    (df["Status"] == "Success").sum()
                )

                st.divider()

                st.subheader("All Chat Records")

                st.dataframe(
                    df,
                    use_container_width=True,
                    hide_index=True
                )

                st.download_button(
                    "⬇️ Download Chat Logs CSV",
                    data=df.to_csv(
                        index=False
                    ).encode("utf-8"),
                    file_name="chat_logs.csv",
                    mime="text/csv"
                )

                st.divider()

                st.subheader("Individual Conversation Details")

                for _, row in df.iterrows():

                    label = (
                        f"{row['Timestamp']} | "
                        f"{row['Username']} | "
                        f"{str(row['Question'])[:60]}"
                    )

                    with st.expander(label):

                        st.write(
                            "**Username:**",
                            row["Username"]
                        )

                        st.write(
                            "**PDF Name:**",
                            row["PDF Name"]
                        )

                        st.write(
                            "**Question:**",
                            row["Question"]
                        )

                        st.write(
                            "**Generated Answer:**",
                            row["Answer"]
                        )

                        st.write(
                            "**Sources:**",
                            row["Sources"]
                        )

                        st.write(
                            "**Status:**",
                            row["Status"]
                        )

                        st.write(
                            "**Timestamp:**",
                            row["Timestamp"]
                        )

            else:

                st.info("No chat records available yet.")

        except Exception as error:

            st.error(
                f"Unable to load chat records: {error}"
            )

    # ======================================
    # ADMIN SECURITY SETTINGS
    # ======================================

    with tab3:

        st.subheader("🔐 Admin Account Recovery")

        st.write(
            "Set a security question and answer. "
            "You can use these details if you forget your admin password."
        )

        try:

            recovery_data = get_admin_recovery_data(
                admin["username"]
            )

            if recovery_data and recovery_data.get("security_question"):

                st.info(
                    f"Current Security Question: "
                    f"{recovery_data['security_question']}"
                )

            else:

                st.warning(
                    "Security question is not configured yet. "
                    "Please set it now."
                )

            questions = [
                "What is your childhood nickname?",
                "What is the name of your first school?",
                "What is your favourite food?",
                "What is the name of your best friend?",
                "What is your favourite place?"
            ]

            with st.form("admin_security_form"):

                selected_question = st.selectbox(
                    "Choose a Security Question",
                    questions
                )

                security_answer = st.text_input(
                    "Security Answer",
                    type="password",
                    placeholder="Enter your answer"
                )

                confirm_answer = st.text_input(
                    "Confirm Security Answer",
                    type="password"
                )

                save_security = st.form_submit_button(
                    "Save Security Settings",
                    use_container_width=True
                )

            if save_security:

                if not security_answer.strip():

                    st.warning(
                        "Please enter a security answer."
                    )

                elif (
                    security_answer.strip().casefold()
                    != confirm_answer.strip().casefold()
                ):

                    st.error(
                        "Security answers do not match."
                    )

                else:

                    answer_hash = bcrypt.hashpw(
                        security_answer.strip().casefold().encode("utf-8"),
                        bcrypt.gensalt()
                    ).decode("utf-8")

                    set_admin_security_question(
                        admin["username"],
                        selected_question,
                        answer_hash
                    )

                    log_admin_action(
                        admin["id"],
                        "UPDATE SECURITY QUESTION",
                        "Admin recovery security question updated."
                    )

                    st.success(
                        "Security question and answer saved successfully!"
                    )

                    st.rerun()

        except Exception as error:

            st.error(
                f"Security settings error: {error}"
            )


# ==========================================
# USER DASHBOARD
# ==========================================

def user_dashboard():

    user = st.session_state.auth_user

    # SIDEBAR

    with st.sidebar:

        st.markdown("# 📚 PDF Assistant")

        st.success(
            f"Logged in: {user['username']}"
        )

        if st.button(
            "Logout",
            use_container_width=True
        ):

            logout()

        st.divider()

        st.markdown("### 📄 Upload Document")

        uploaded_file = st.file_uploader(
            "Choose a PDF file",
            type=["pdf"]
        )

        if st.button(
            "⚙️ Process PDF",
            use_container_width=True
        ):

            if uploaded_file is None:

                st.warning("Please upload a PDF file.")

            elif not get_gemini_api_key():

                st.error(
                    "GEMINI_API_KEY is not configured."
                )

            else:

                try:

                    with st.spinner("Reading PDF..."):

                        documents = load_pdf(uploaded_file)

                    with st.spinner("Splitting into chunks..."):

                        chunks = create_chunks(documents)

                    if not chunks:

                        st.error(
                            "No text chunks were created."
                        )

                    else:

                        texts = [
                            chunk["text"]
                            for chunk in chunks
                        ]

                        with st.spinner("Creating embeddings..."):

                            embeddings, embedding_model = (
                                create_embeddings(texts)
                            )

                        with st.spinner("Building vector store..."):

                            vector_store = create_vector_store(
                                embeddings
                            )

                        st.session_state.chunks = chunks

                        st.session_state.embedding_model = (
                            embedding_model
                        )

                        st.session_state.vector_store = (
                            vector_store
                        )

                        st.session_state.processed = True

                        st.session_state.uploaded_filename = (
                            uploaded_file.name
                        )

                        st.session_state.messages = []

                        st.success(
                            "PDF processed successfully!"
                        )

                        st.rerun()

                except Exception as error:

                    st.error(
                        f"Error processing PDF: {error}"
                    )

        st.divider()

        st.markdown("### 📊 Document Status")

        if st.session_state.processed:

            st.success("✅ Document Ready")

            st.write(
                f"File: {st.session_state.uploaded_filename}"
            )

            st.write(
                f"Total Chunks: {len(st.session_state.chunks)}"
            )

        else:

            st.info(
                "Upload and process a PDF to begin."
            )

        st.divider()

        if st.button(
            "🗑️ Clear Conversation",
            use_container_width=True
        ):

            st.session_state.messages = []
            st.rerun()

    # MAIN HEADER

    st.markdown("""
    <div class="welcome-card">
        <h1>🤖 PDF Knowledge Assistant</h1>
        <p>Your AI-powered assistant for PDF question answering.</p>
        <p>Upload a document, process it, and ask questions
        based on its content.</p>
    </div>
    """, unsafe_allow_html=True)

    if not st.session_state.processed:

        st.info(
            "Upload a PDF from the left sidebar "
            "and click Process PDF to start."
        )

        col1, col2, col3 = st.columns(3)

        with col1:

            st.markdown("""
            <div class="info-card">
                <h3>📄 Upload</h3>
                <p>Upload your PDF document.</p>
            </div>
            """, unsafe_allow_html=True)

        with col2:

            st.markdown("""
            <div class="info-card">
                <h3>🔍 Retrieve</h3>
                <p>Find relevant information.</p>
            </div>
            """, unsafe_allow_html=True)

        with col3:

            st.markdown("""
            <div class="info-card">
                <h3>💬 Ask</h3>
                <p>Ask questions and get answers.</p>
            </div>
            """, unsafe_allow_html=True)

        return

    # EXAMPLE QUESTIONS

    st.markdown("### 💡 Example Questions")

    col1, col2, col3 = st.columns(3)

    with col1:

        if st.button(
            "What is this document about?",
            use_container_width=True
        ):

            st.session_state.pending_question = (
                "What is this document about?"
            )

    with col2:

        if st.button(
            "Summarize the main points.",
            use_container_width=True
        ):

            st.session_state.pending_question = (
                "Summarize the main points."
            )

    with col3:

        if st.button(
            "Explain important information.",
            use_container_width=True
        ):

            st.session_state.pending_question = (
                "Explain the important information in this PDF."
            )

    # CHAT HISTORY

    st.markdown("### 💬 Conversation")

    for message in st.session_state.messages:

        with st.chat_message(message["role"]):

            st.markdown(message["content"])

            if message.get("sources"):

                with st.expander("📚 View Sources"):

                    for source in message["sources"]:

                        st.markdown(source)

    # CHAT INPUT

    user_question = st.chat_input(
        "Ask a question about your PDF..."
    )

    if "pending_question" in st.session_state:

        user_question = st.session_state.pop(
            "pending_question"
        )

    # ANSWER GENERATION AND DATABASE LOGGING

    if user_question:

        st.session_state.messages.append({
            "role": "user",
            "content": user_question
        })

        with st.chat_message("user"):

            st.markdown(user_question)

        with st.chat_message("assistant"):

            answer = ""
            sources = []
            status = "Failed"

            try:

                with st.spinner("Searching the document..."):

                    relevant_chunks = retrieve_relevant_chunks(
                        user_question,
                        st.session_state.embedding_model,
                        st.session_state.vector_store,
                        st.session_state.chunks
                    )

                if not relevant_chunks:

                    answer = (
                        "I couldn't find relevant information "
                        "in the uploaded PDF."
                    )

                else:

                    with st.spinner("Generating answer..."):

                        answer = generate_answer(
                            user_question,
                            relevant_chunks
                        )

                    seen_sources = set()

                    for chunk in relevant_chunks:

                        if not isinstance(chunk, dict):
                            continue

                        filename = chunk.get(
                            "source",
                            st.session_state.uploaded_filename
                        )

                        page = chunk.get("page")

                        if page is None:

                            source_text = (
                                f"{filename} - Page number unavailable"
                            )

                        else:

                            source_text = (
                                f"{filename} - Page {page}"
                            )

                        if source_text not in seen_sources:

                            sources.append(source_text)
                            seen_sources.add(source_text)

                status = "Success"

                st.markdown(answer)

                if sources:

                    with st.expander(
                        "📚 View Sources",
                        expanded=True
                    ):

                        for source in sources:
                            st.markdown(source)

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer,
                    "sources": sources
                })

            except Exception as error:

                answer = (
                    f"Sorry, something went wrong: {error}"
                )

                status = "Failed"

                st.error(answer)

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer,
                    "sources": []
                })

            # SAVE CHAT TO MYSQL

            try:

                save_chat(
                    username=user["username"],
                    question=user_question,
                    answer=answer,
                    pdf_name=(
                        st.session_state.uploaded_filename
                        or "Not uploaded"
                    ),
                    sources=json.dumps(
                        sources,
                        ensure_ascii=False
                    ),
                    status=status
                )

            except Exception as db_error:

                st.error(
                    f"Could not save chat history: {db_error}"
                )


# ==========================================
# APPLICATION ROUTING
# ==========================================

if st.session_state.auth_user is None:

    login_page()

elif st.session_state.auth_user["role"] == "admin":

    admin_dashboard()

else:

    user_dashboard()