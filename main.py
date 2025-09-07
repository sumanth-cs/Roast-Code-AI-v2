import streamlit as st
import requests
import base64
import io
import time

# Set page configuration
st.set_page_config(
    page_title="Roast Code - AI Code Analyzer & Debugger",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for dark theme
def load_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600&family=Inter:wght@300;400;500;600;700&display=swap');
    
    :root {
        --primary: #8B5CF6;
        --secondary: #EC4899;
        --accent: #10B981;
        --dark-bg: #0F172A;
        --dark-card: #1E293B;
        --dark-text: #F1F5F9;
        --dark-border: #334155;
        --success: #10B981;
        --warning: #F59E0B;
        --error: #EF4444;
        --gray: #94A3B8;
    }
    
    * {
        font-family: 'Inter', sans-serif;
        color: var(--dark-text);
    }
    
    .stApp {
        background-color: var(--dark-bg);
        color: var(--dark-text);
    }
    
    .main-header {
        font-family: 'Fira Code', monospace;
        font-weight: 700;
        font-size: 2.5rem;
        text-align: center;
        margin-bottom: 0.5rem;
        background: linear-gradient(90deg, var(--primary), var(--secondary));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        padding: 1rem 0;
    }
    
    .subheader {
        color: var(--gray);
        text-align: center;
        margin-bottom: 1rem;
        font-weight: 400;
        font-size: 1.1rem;
    }
    
    .card {
        background: var(--dark-card);
        border-radius: 12px;
        padding: 1rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.2);
        border: 1px solid var(--dark-border);
        margin-bottom: 1rem;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: var(--dark-bg);
        border-bottom: 1px solid var(--dark-border);
    }
    
    .stTabs [data-baseweb="tab"] {
        background: var(--dark-card);
        border-radius: 8px 8px 0 0;
        padding: 10px 16px;
        font-weight: 500;
        color: var(--gray);
        border: 1px solid var(--dark-border);
        border-bottom: none;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(90deg, var(--primary), var(--secondary));
        color: white;
    }
    
    .stButton button {
        background: linear-gradient(90deg, var(--primary), var(--secondary));
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1.5rem;
        font-weight: 500;
        transition: all 0.2s ease;
        width: 100%;
    }
    
    .stButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(139, 92, 246, 0.4);
        color: white;
    }
    
    .stTextArea textarea {
        background-color: var(--dark-card) !important;
        color: var(--dark-text) !important;
        border: 1px solid var(--dark-border) !important;
        font-family: 'Fira Code', monospace !important;
    }
    
    .stSelectbox div[data-baseweb="select"] {
        background-color: var(--dark-card) !important;
        color: var(--dark-text) !important;
        border: 1px solid var(--dark-border) !important;
    }
    
    .stTextInput input {
        background-color: var(--dark-card) !important;
        color: var(--dark-text) !important;
        border: 1px solid var(--dark-border) !important;
    }
    
    code {
        font-family: 'Fira Code', monospace !important;
    }
    
    .roast-container {
        background: rgba(239, 68, 68, 0.1);
        border-left: 4px solid var(--error);
        border-radius: 4px;
        padding: 1rem;
        margin: 1rem 0;
    }
    
    .improvement-container {
        background: rgba(16, 185, 129, 0.1);
        border-left: 4px solid var(--success);
        border-radius: 4px;
        padding: 1rem;
        margin: 1rem 0;
    }
    
    .audio-player {
        width: 100%;
        margin: 1rem 0;
        border-radius: 8px;
    }
    
    .metric-card {
        background: var(--dark-card);
        border-radius: 8px;
        padding: 1rem;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        border: 1px solid var(--dark-border);
    }
    
    .metric-value {
        font-size: 24px;
        font-weight: 700;
        color: var(--primary);
        margin: 0.5rem 0;
    }
    
    .metric-label {
        font-size: 14px;
        color: var(--gray);
    }
    
    .footer {
        text-align: center;
        margin-top: 2rem;
        padding: 1rem;
        color: var(--gray);
        font-size: 14px;
    }
    
    /* Custom scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: var(--dark-card);
    }
    
    ::-webkit-scrollbar-thumb {
        background: var(--primary);
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: var(--secondary);
    }
    
    /* Streamlit component overrides */
    .stMarkdown {
        color: var(--dark-text) !important;
    }
    
    .stAlert {
        background-color: var(--dark-card) !important;
        color: var(--dark-text) !important;
        border: 1px solid var(--dark-border) !important;
    }
    
    .stSpinner > div {
        color: var(--primary) !important;
    }
    
    .stDownloadButton button {
        background: linear-gradient(90deg, var(--primary), var(--secondary));
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1.5rem;
        font-weight: 500;
        transition: all 0.2s ease;
        width: 100%;
    }
    
    .stDownloadButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(139, 92, 246, 0.4);
        color: white;
    }
    
    /* Custom loading animation */
    .loading-container {
        display: flex;
        justify-content: center;
        align-items: center;
        flex-direction: column;
        padding: 2rem;
    }
    
    .loading-spinner {
        width: 50px;
        height: 50px;
        border: 5px solid var(--dark-border);
        border-top: 5px solid var(--primary);
        border-radius: 50%;
        animation: spin 1s linear infinite;
        margin-bottom: 1rem;
    }
    
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    
    .loading-text {
        color: var(--gray);
        font-size: 1.1rem;
    }
    
    /* Hidden audio element for autoplay */
    .hidden-audio {
        display: none;
    }
    </style>
    """, unsafe_allow_html=True)

def show_loading_animation():
    """Show custom loading animation."""
    st.markdown("""
    <div class="loading-container">
        <div class="loading-spinner"></div>
        <div class="loading-text">Analyzing your code...</div>
    </div>
    """, unsafe_allow_html=True)

def run_streamlit():
    load_css()
    
    # Header section - simplified
    st.markdown('<h1 class="main-header">🔥 R0AST C0DE AI 🔥</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subheader">AI-powered code analysis with a sarcastic twist</p>', unsafe_allow_html=True)
    
    # Create tabs for different functionalities
    tab1, tab2 = st.tabs(["Code Analysis & Roasting", "Code Generation"])
    
    with tab1:
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("Your Code")
            code_input = st.text_area(
                "Paste your Python code here:",
                height=300,
                placeholder="Paste your code here and prepare to be roasted...",
                label_visibility="collapsed"
            )
            
            roast_level = st.selectbox(
                "Roast Intensity:",
                ["mild", "medium", "brutal"],
                index=1,
                help="Choose how harsh you want the feedback to be"
            )
            
            if st.button("Analyze & Roast My Code!", use_container_width=True):
                st.session_state.analyze_clicked = True
                st.session_state.show_loading = True
                # Clear previous audio state
                if 'audio_data' in st.session_state:
                    del st.session_state.audio_data
        
        with col2:
            if 'analyze_clicked' in st.session_state and st.session_state.analyze_clicked:
                if code_input:
                    if st.session_state.get('show_loading', False):
                        # Show custom loading animation
                        show_loading_animation()
                        # Force a rerun to display the loading animation
                        st.session_state.show_loading = False
                        st.rerun()
                    
                    try:
                        response = requests.post(
                            "http://localhost:5001/api/roast",
                            json={"code": code_input, "roast_level": roast_level},
                            timeout=30
                        )
                        
                        if response.status_code == 200:
                            result = response.json()
                            st.session_state.result = result
                            
                            # Store audio data in session state for autoplay
                            if "audio" in result and result["audio"]:
                                st.session_state.audio_data = result["audio"]
                            
                            # Display roasts
                            st.subheader("Analysis Results")
                            
                            if "roasts" in result and result["roasts"]:
                                st.markdown("### 🔥 Roasts")
                                for roast in result["roasts"]:
                                    st.markdown(f'<div class="roast-container">💬 {roast}</div>', unsafe_allow_html=True)
                            
                            # Play audio if available
                            if "audio" in result and result["audio"]:
                                try:
                                    audio_bytes = base64.b64decode(result["audio"])
                                    
                                    # Create a hidden audio element that autoplays (works in some browsers)
                                    st.markdown(f"""
                                    <audio class="hidden-audio" controls autoplay>
                                        <source src="data:audio/mp3;base64,{result['audio']}" type="audio/mp3">
                                        Your browser does not support the audio element.
                                    </audio>
                                    """, unsafe_allow_html=True)
                                    
                                    # Also show the visible audio player (not on loop)
                                    st.audio(audio_bytes, format="audio/mp3")
                                    
                                    # Add JavaScript to ensure audio plays and doesn't loop
                                    st.markdown(f"""
                                    <script>
                                    document.addEventListener('DOMContentLoaded', function() {{
                                        // Find the audio element
                                        var audioElement = document.querySelector('audio');
                                        if (audioElement) {{
                                            // Ensure it doesn't loop
                                            audioElement.loop = false;
                                            // Try to play automatically
                                            var playPromise = audioElement.play();
                                            if (playPromise !== undefined) {{
                                                playPromise.catch(function(error) {{
                                                    console.log('Autoplay prevented:', error);
                                                    // If autoplay is blocked, show a play button
                                                    var playButton = document.createElement('button');
                                                    playButton.textContent = '🔊 Play Roast';
                                                    playButton.style.cssText = 'background: linear-gradient(90deg, #8B5CF6, #EC4899); color: white; border: none; border-radius: 8px; padding: 10px 15px; margin: 10px 0; cursor: pointer;';
                                                    playButton.onclick = function() {{
                                                        audioElement.play();
                                                        this.style.display = 'none';
                                                    }};
                                                    audioElement.parentNode.insertBefore(playButton, audioElement.nextSibling);
                                                }});
                                            }}
                                        }}
                                    }});
                                    </script>
                                    """, unsafe_allow_html=True)
                                except Exception as e:
                                    st.warning("Audio playback failed. This might be due to browser restrictions or audio format issues.")
                            else:
                                st.info("Audio generation requires a valid ElevenLabs API key or there was an issue with the TTS service.")
                            
                            # Show metrics if available
                            if "metrics" in result and result["metrics"]:
                                st.markdown("### 📊 Metrics")
                                metrics = result["metrics"]
                                mcol1, mcol2, mcol3 = st.columns(3)
                                
                                with mcol1:
                                    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                                    st.markdown(f'<div class="metric-value">{metrics.get("line_count", 0)}</div>', unsafe_allow_html=True)
                                    st.markdown('<div class="metric-label">Lines of Code</div>', unsafe_allow_html=True)
                                    st.markdown('</div>', unsafe_allow_html=True)
                                
                                with mcol2:
                                    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                                    st.markdown(f'<div class="metric-value">{metrics.get("cyclomatic_complexity", 0)}</div>', unsafe_allow_html=True)
                                    st.markdown('<div class="metric-label">Complexity</div>', unsafe_allow_html=True)
                                    st.markdown('</div>', unsafe_allow_html=True)
                                
                                with mcol3:
                                    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                                    st.markdown(f'<div class="metric-value">{metrics.get("maintainability_index", 0)}</div>', unsafe_allow_html=True)
                                    st.markdown('<div class="metric-label">Maintainability</div>', unsafe_allow_html=True)
                                    st.markdown('</div>', unsafe_allow_html=True)
                            
                            # Show improved code
                            # if "corrected_code" in result and result["corrected_code"]:
                            #     st.markdown("### ✅ Improved Code")
                            #     st.markdown('<div class="improvement-container">', unsafe_allow_html=True)
                            #     st.code(result["corrected_code"], language="python")
                            #     st.markdown('</div>', unsafe_allow_html=True)
                                
                            #     # Download option for fixed code
                            #     st.download_button(
                            #         label="Download Improved Code",
                            #         data=result["corrected_code"],
                            #         file_name="improved_code.py",
                            #         mime="text/python",
                            #         use_container_width=True
                            #     )
                        else:
                            st.error(f"Backend error: {response.status_code} - {response.text}")
                    except requests.exceptions.Timeout:
                        st.error("Request timed out. The backend might be processing slowly.")
                    except requests.exceptions.ConnectionError:
                        st.error("Could not connect to backend. Make sure the Flask server is running.")
                    except Exception as e:
                        st.error(f"Error analyzing code: {e}")
                else:
                    st.error("Please provide some code to analyze!")
    
    with tab2:
        st.subheader("Generate Code")
        prompt = st.text_input(
            "What do you want me to generate?",
            placeholder="e.g., 'Write a function to calculate fibonacci sequence'"
        )
        
        if st.button("Generate Code", use_container_width=True):
            if prompt:
                with st.spinner("Generating code... (and preparing a sarcastic remark)"):
                    try:
                        response = requests.post(
                            "http://localhost:5001/api/generate",
                            json={"prompt": prompt},
                            timeout=30
                        )
                        if response.status_code == 200:
                            result = response.json()
                            
                            # Display roast
                            if "roast" in result:
                                st.markdown(f'<div class="roast-container">💬 {result["roast"]}</div>', unsafe_allow_html=True)
                            
                            # Display generated code
                            if "code" in result:
                                st.markdown("### Generated Code")
                                st.code(result["code"], language="python")
                                
                                # Download option for generated code
                                st.download_button(
                                    label="Download Generated Code",
                                    data=result["code"],
                                    file_name="generated_code.py",
                                    mime="text/python",
                                    use_container_width=True
                                )
                            
                            # Play audio if available
                            if "audio_file" in result and result["audio_file"]:
                                audio_bytes = base64.b64decode(result["audio_file"])
                                
                                # Create a hidden audio element that autoplays
                                st.markdown(f"""
                                <audio class="hidden-audio" controls autoplay>
                                    <source src="data:audio/mp3;base64,{result['audio_file']}" type="audio/mp3">
                                    Your browser does not support the audio element.
                                </audio>
                                """, unsafe_allow_html=True)
                                
                                # Also show the visible audio player
                                st.audio(audio_bytes, format="audio/mp3")
                            else:
                                st.info("Audio generation requires a valid ElevenLabs API key")
                        else:
                            st.error(f"Backend error: {response.status_code} - {response.text}")
                    except requests.exceptions.Timeout:
                        st.error("Request timed out. The backend might be processing slowly.")
                    except requests.exceptions.ConnectionError:
                        st.error("Could not connect to backend. Make sure the Flask server is running.")
                    except Exception as e:
                        st.error(f"Error generating code: {e}")
            else:
                st.error("Please provide a prompt!")
    
    # Footer
    st.markdown("""
    <div class="footer">
        <p>Roast AI - Because sometimes your code needs a reality check 🔥</p>
        <p>Built with Streamlit, Flask, and sarcasm</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    run_streamlit()