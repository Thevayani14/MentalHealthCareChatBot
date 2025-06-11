import streamlit as st
import hashlib
from database import get_user, add_user # Import database functions

# --- PASSWORD HASHING ---
def hash_password(password):
    """Hashes a password using SHA-256."""
    return hashlib.sha256(str.encode(password)).hexdigest()

def verify_password(stored_hash, provided_password):
    """Verifies a provided password against a stored hash."""
    return stored_hash == hash_password(provided_password)

# --- LOGIN & SIGN UP PAGE UI ---
def login_page():
    """Displays the login and sign-up interface using the database."""
    st.title("Welcome to your Mental Health Companion 🌱")
    st.write("Please log in or create an account to continue.")

    login_tab, signup_tab = st.tabs(["🔒 Login", "✍️ Sign Up"])

    # --- Login Tab ---
    with login_tab:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")

            if submitted:
                user_data = get_user(username)
                if user_data and verify_password(user_data['hashed_password'], password):
                    st.session_state["logged_in"] = True
                    st.session_state["username"] = user_data['username']
                    st.session_state["user_id"] = user_data['id'] # <-- THIS IS THE FIX
                    st.success("Logged in successfully!")
                    st.rerun()
                else:
                    st.error("Invalid username or password.")

    # --- Sign Up Tab ---
    with signup_tab:
        with st.form("signup_form"):
            new_username = st.text_input("Choose a Username", key="signup_username")
            new_password = st.text_input("Choose a Password", type="password", key="signup_pass1")
            confirm_password = st.text_input("Confirm Password", type="password", key="signup_pass2")
            signup_submitted = st.form_submit_button("Sign Up")

            if signup_submitted:
                if not new_username or not new_password:
                    st.error("Please fill in all fields.")
                elif new_password != confirm_password:
                    st.error("Passwords do not match.")
                else:
                    hashed_new_password = hash_password(new_password)
                    if add_user(new_username, hashed_new_password):
                        st.success(f"Account created for {new_username}! Please go to the Login tab to log in.")
                    else:
                        st.error("Username already exists. Please choose another.")
