import streamlit as st
from streamlit_option_menu import option_menu

# Import pages
from pages import (
    code_analysis,
    code_generation,
    collaboration,
    metrics_dashboard
)

def main():
    st.set_page_config(
        page_title="Roast Code AI - Advanced Code Companion",
        page_icon="🔥",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS
    with open("frontend/static/css/styles.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    
    # Sidebar navigation
    with st.sidebar:
        st.image("https://img.icons8.com/color/96/000000/python.png", width=100)
        st.title("🔥 Roast Code AI")
        st.markdown("---")
        
        selected = option_menu(
            menu_title="Navigation",
            options=["Code Analysis", "Code Generation", "Collaboration", "Metrics Dashboard"],
            icons=["search", "code-slash", "people", "graph-up"],
            menu_icon="cast",
            default_index=0,
            styles={
                "container": {"padding": "0!important"},
                "icon": {"color": "orange", "font-size": "18px"},
                "nav-link": {"font-size": "16px", "text-align": "left", "margin": "0px"},
                "nav-link-selected": {"background-color": "#ff4b4b"},
            }
        )
        
        st.markdown("---")
        st.markdown("### 🤖 Features")
        st.markdown("""
        - Multi-language Support
        - Real-time Collaboration
        - AI-powered Code Analysis
        - Voice Feedback
        - Code Quality Metrics
        """)
        
        st.markdown("---")
        st.markdown("### 📊 Stats")
        if 'stats' in st.session_state:
            cols = st.columns(2)
            cols[0].metric("Analyses", st.session_state.stats.get('analyses', 0))
            cols[1].metric("Generations", st.session_state.stats.get('generations', 0))
    
    # Page routing
    if selected == "Code Analysis":
        code_analysis.render()
    elif selected == "Code Generation":
        code_generation.render()
    elif selected == "Collaboration":
        collaboration.render()
    elif selected == "Metrics Dashboard":
        metrics_dashboard.render()

if __name__ == "__main__":
    main()