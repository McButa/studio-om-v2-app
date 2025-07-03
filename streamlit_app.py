# streamlit_app.py (Final Corrected Version)

import streamlit as st
import app_pages
import baseline_validator_page

# --- SESSION STATE INITIALIZATION ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'baseline_confirmed' not in st.session_state:
    st.session_state['baseline_confirmed'] = False

# --- LOGIN FUNCTION (REVISED FOR BETTER LAYOUT & CORRECTED PARAMETER) ---
def login_form():
    """Displays a simple login form with a better layout."""
    st.set_page_config(
        page_title="Login - Studio OM Solar Analysis",
        page_icon="🔆",
        layout="wide"
    )

    # --- Custom CSS to hide sidebar and other elements on login page ---
    st.markdown("""
        <style>
            [data-testid="stSidebar"] {
                display: none;
            }
            .main .block-container {
                padding-top: 5rem;
                padding-bottom: 5rem;
            }
        </style>
    """, unsafe_allow_html=True)

    st.title("🔆 Solar PV Analysis Tool")
    st.markdown("---")

    # Use columns to create a centered, fixed-width login box
    col1, col2, col3 = st.columns([1, 1.2, 1])

    with col2:
        with st.container(border=True):
            # CORRECTED: Changed use_column_width='auto' to use_container_width=True
            st.image("images/studio_om_logo.png", use_container_width=True)
            st.subheader("Please Log In")

            with st.form("login_form_main"):
                # ใน streamlit_app.py, ภายใน login_form()
                username = st.text_input("Username", key="login_username", autocomplete="off")
                password = st.text_input("Password", type="password", key="login_password", autocomplete="off")

                submitted = st.form_submit_button("Log In", type="primary", use_container_width=True)

                if submitted:
                    try:
                        valid_username = st.secrets["LOGIN_USERNAME"]
                        valid_password = st.secrets["LOGIN_PASSWORD"]
                    except KeyError:
                        st.warning("Secrets not found. Using default credentials ('admin'/'password123').")
                        valid_username = "admin"
                        valid_password = "password123"

                    if username == valid_username and password == valid_password:
                        st.session_state['logged_in'] = True
                        st.rerun()
                    else:
                        st.error("Invalid username or password.")

# --- MAIN APP FUNCTION ---
def main_app():
    """Displays the main application after successful login and baseline confirmation."""
    st.set_page_config(
        page_title="Studio OM - Solar PV Analysis",
        page_icon="🔆",
        layout="wide"
    )
    
    def logout():
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

    with st.sidebar:
        st.title("Studio OM")
        st.write("---")
        
        PAGES = {
            "🏠 Home & Input": app_pages.show_home_input_page,
            "📊 Analysis Report": app_pages.show_analysis_report_page,
            "🛠️ Simulator": app_pages.show_simulator_page,
            "ℹ️ About": app_pages.show_about_page,
        }
        
        selection = st.radio("Navigation", list(PAGES.keys()), key="page_selection")
        
        st.write("---")
        if st.button("🚪 Logout & Start Over"):
            logout()

    page_function = PAGES[selection]
    page_function()

# --- Main Execution Logic ---
if not st.session_state['logged_in']:
    login_form()
elif not st.session_state['baseline_confirmed']:
    baseline_validator_page.show_page()
else:
    main_app()