# import streamlit as st
# import requests
# import base64
# import pandas as pd
# import latex

# st.set_page_config(page_title="Roast Code AI", layout="wide")

# def generate_pdf_report(roasts, suggestions, corrected_code, metrics):
#     """Generate a LaTeX-based PDF report."""
#     latex_content = r"""
#     \documentclass{article}
#     \usepackage{geometry}
#     \geometry{a4paper, margin=1in}
#     \usepackage{listings}
#     \usepackage{xcolor}
#     \lstset{
#         basicstyle=\ttfamily\small,
#         breaklines=true,
#         frame=single
#     }
#     \begin{document}
#     \title{Roast Code AI Report}
#     \author{}
#     \maketitle
#     \section{Roasts}
#     \begin{itemize}
#     """
#     for roast in roasts:
#         latex_content += f"    \\item {roast}\n"
#     latex_content += r"""
#     \end{itemize}
#     \section{Suggestions}
#     \begin{itemize}
#     """
#     for suggestion in suggestions:
#         latex_content += f"    \\item {suggestion}\n"
#     latex_content += r"""
#     \end{itemize}
#     \section{Corrected Code}
#     \begin{lstlisting}
#     """
#     latex_content += corrected_code.replace('\\', '\\\\').replace('$', '\\$')
#     latex_content += r"""
#     \end{lstlisting}
#     \section{Metrics}
#     \begin{itemize}
#         \item Line Count: """ + str(metrics.get("line_count", 0)) + r"""
#         \item Cyclomatic Complexity: """ + str(metrics.get("cyclomatic_complexity", 0)) + r"""
#         \item Maintainability Index: """ + str(metrics.get("maintainability_index", 0)) + r"""
#     \end{itemize}
#     \end{document}
#     """
#     return latex_content

# def run_streamlit():
#     st.title("🔥 Roast Code AI 🔥")
#     st.write("Analyze, roast, or generate code with a sarcastic twist!")
    
#     tab1, tab2 = st.tabs(["Roast Code", "Generate Code"])
    
#     with tab1:
#         st.header("Roast Your Code")
#         language = st.selectbox("Select Language:", ["python", "javascript", "java"])
#         roast_level = st.selectbox("Select Roast Level:", ["mild", "medium", "brutal"])
#         code_input = st.text_area("Paste your code here:", height=300)
#         uploaded_file = st.file_uploader("Or upload a file:", type=["py", "js", "java"])
        
#         if uploaded_file:
#             code_input = uploaded_file.read().decode('utf-8')
        
#         if st.button("Roast My Code!"):
#             if code_input:
#                 try:
#                     response = requests.post(
#                         "http://localhost:5001/api/roast",
#                         json={"code": code_input, "roast_level": roast_level, "language": language}
#                     )
#                     response.raise_for_status()
#                     result = response.json()
#                     for roast in result["roasts"]:
#                         st.write(roast)
#                     for suggestion in result["suggestions"]:
#                         st.write(suggestion)
#                     st.subheader("Corrected Code")
#                     st.code(result["corrected_code"], language=language)
#                     st.subheader("Metrics")
#                     metrics_df = pd.DataFrame([result["metrics"]])
#                     st.bar_chart(metrics_df)
#                     if result["audio_file"]:
#                         st.audio(base64.b64decode(result["audio_file"]), format="audio/mp3")
#                     st.download_button(
#                         label="Download Report",
#                         data=generate_pdf_report(result["roasts"], result["suggestions"], result["corrected_code"], result["metrics"]),
#                         file_name="code_report.tex",
#                         mime="text/plain"
#                     )
#                 except Exception as e:
#                     st.error(f"Error roasting code: {e}. Ensure the Flask server is running.")
#             else:
#                 st.error("Please provide some code to roast!")
    
#     with tab2:
#         st.header("Generate Code")
#         prompt = st.text_area("Enter your prompt (e.g., 'Write a program to add two numbers'):", height=100)
#         if st.button("Generate Code"):
#             if prompt:
#                 try:
#                     response = requests.post(
#                         "http://localhost:5001/api/generate",
#                         json={"prompt": prompt}
#                     )
#                     response.raise_for_status()
#                     result = response.json()
#                     st.write(result["roast"])
#                     st.code(result["code"], language="python")
#                     if result["audio_file"]:
#                         st.audio(base64.b64decode(result["audio_file"]), format="audio/mp3")
#                 except Exception as e:
#                     st.error(f"Error generating code: {e}. Ensure the Flask server is running.")
#             else:
#                 st.error("Please provide a prompt!")

# if __name__ == "__main__":
#     run_streamlit()

import streamlit as st
import requests
import base64
import io
import time

def run_streamlit():
    st.set_page_config(page_title="Code Roaster & Analyzer", layout="wide")
    
    st.title("🔥 Code Roaster & Analyzer 🔥")
    st.write("Get your code roasted, analyzed, and improved with sarcastic feedback!")
    
    # Check if backend is running
    try:
        response = requests.get("http://localhost:5001/api/health", timeout=2)
        backend_status = "✅ Backend connected" if response.status_code == 200 else "❌ Backend not responding"
    except:
        backend_status = "❌ Backend not running"
    
    st.sidebar.markdown(f"**{backend_status}**")
    st.sidebar.info("Make sure the Flask server is running on port 5001")
    
    # Create tabs for different functionalities
    tab1, tab2, tab3 = st.tabs(["Code Roaster", "Code Generator", "About"])
    
    with tab1:
        st.header("Roast My Code")
        roast_level = st.selectbox("Select Roast Level:", ["mild", "medium", "brutal"])
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Your Code")
            code_input = st.text_area("Paste your Python code here:", height=300, key="code_input")
            uploaded_file = st.file_uploader("Or upload a .py file:", type=["py"])
            
            if uploaded_file:
                code_input = uploaded_file.read().decode('utf-8')
                st.session_state.code_input = code_input
            
        with col2:
            st.subheader("Analysis Results")
            if st.button("Analyze & Roast My Code!"):
                if code_input:
                    with st.spinner("Analyzing your code..."):
                        try:
                            response = requests.post(
                                "http://localhost:5001/api/roast",
                                json={"code": code_input, "roast_level": roast_level},
                                timeout=30
                            )
                            
                            if response.status_code == 200:
                                result = response.json()
                                
                                st.success("Analysis Complete!")
                                
                                # Display roasts
                                st.subheader("Roasts:")
                                for roast in result["roasts"]:
                                    st.write(f"🔥 {roast}")
                                
                                # Play audio if available
                                if result["audio"]:
                                    audio_bytes = base64.b64decode(result["audio"])
                                    st.audio(audio_bytes, format="audio/mp3")
                                else:
                                    st.info("Audio generation requires a valid ElevenLabs API key")
                                
                                # Show fixed code
                                st.subheader("Improved Code:")
                                st.code(result["fixed_code"], language="python")
                                
                                # Download option for fixed code
                                st.download_button(
                                    label="Download Improved Code",
                                    data=result["fixed_code"],
                                    file_name="improved_code.py",
                                    mime="text/python"
                                )
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
        st.header("Generate Code")
        prompt = st.text_input("What code do you want me to generate?")
        
        if st.button("Generate Code"):
            if prompt:
                with st.spinner("Generating code..."):
                    try:
                        response = requests.post(
                            "http://localhost:5001/api/generate_code",
                            json={"prompt": prompt},
                            timeout=30
                        )
                        
                        if response.status_code == 200:
                            result = response.json()
                            
                            st.subheader("Generated Code:")
                            st.code(result["code"], language="python")
                            
                            # Download option for generated code
                            st.download_button(
                                label="Download Generated Code",
                                data=result["code"],
                                file_name="generated_code.py",
                                mime="text/python"
                            )
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
    
    with tab3:
        st.header("About This Project")
        st.markdown("""
        This Code Roaster & Analyzer provides:
        
        - **Code Analysis**: Identifies issues in your Python code
        - **Sarcastic Roasts**: Provides humorous feedback on code quality
        - **Code Improvement**: Suggests and implements fixes
        - **Code Generation**: Creates code based on your prompts
        
        Built with:
        - Streamlit for the frontend
        - Flask for the backend API
        - Transformers for NLP-based roasts
        - Pylint and Radon for code analysis
        - ElevenLabs for text-to-speech (optional)
        
        **Note**: For audio features, you need to set up an ElevenLabs API key.
        """)

if __name__ == "__main__":
    run_streamlit()