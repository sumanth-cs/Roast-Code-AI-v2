import streamlit as st
import requests
import base64

def run_streamlit():
    st.set_page_config(page_title="Roast Code Advanced", layout="wide")
    st.title("🔥 Roast Code Advanced 🔥")
    st.write("Upload your Python code and get roasted with Indian-style sarcasm!")
    
    roast_level = st.selectbox("Select Roast Level:", ["mild", "medium", "brutal"])
    code_input = st.text_area("Paste your Python code here:", height=300)
    uploaded_file = st.file_uploader("Or upload a .py file:", type=["py"])
    
    if uploaded_file:
        code_input = uploaded_file.read().decode('utf-8')
    
    if st.button("Roast My Code!"):
        if code_input:
            try:
                response = requests.post(
                    "http://localhost:5001/api/roast",
                    json={"code": code_input, "roast_level": roast_level}
                )
                response.raise_for_status()
                result = response.json()
                for roast, audio_b64 in zip(result["roasts"], result["audio_files"]):
                    st.write(roast)
                    if audio_b64:
                        st.audio(base64.b64decode(audio_b64), format="audio/mp3")
            except Exception as e:
                st.error(f"Error roasting code: {e}. Ensure the Flask server is running at http://localhost:5001.")
        else:
            st.error("Please provide some code to roast!")

if __name__ == "__main__":
    run_streamlit()