import streamlit as st
import requests
import json
import base64
from io import BytesIO
from components.code_editor import CodeEditor
from components.voice_player import VoicePlayer
from components.metrics_display import MetricsDisplay

def render():
    st.title("🔍 Code Analysis & Roasting")
    st.markdown("Analyze your code across multiple languages with AI-powered feedback")
    
    # Initialize session state
    if 'analysis_result' not in st.session_state:
        st.session_state.analysis_result = None
    
    # Create two columns
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📝 Input Code")
        
        # Language selection
        language = st.selectbox(
            "Select Language",
            ["python", "javascript", "java", "cpp", "typescript", "go", "rust"],
            index=0
        )
        
        # Code editor
        default_code = get_default_code(language)
        code = CodeEditor(
            value=default_code,
            language=language,
            height=400
        ).render()
        
        # Roast intensity
        intensity = st.radio(
            "Roast Intensity",
            ["mild", "medium", "brutal"],
            horizontal=True,
            help="How harsh should the feedback be?"
        )
        
        # Analyze button
        if st.button("🚀 Analyze & Roast", use_container_width=True):
            if code.strip():
                with st.spinner("Analyzing code..."):
                    result = analyze_code(code, language, intensity)
                    if result:
                        st.session_state.analysis_result = result
                        st.rerun()
            else:
                st.warning("Please enter some code to analyze")
    
    with col2:
        st.subheader("📊 Analysis Results")
        
        if st.session_state.analysis_result:
            result = st.session_state.analysis_result
            
            # Display roasts
            st.markdown("### 🔥 Roasts")
            if 'roast' in result and 'text' in result['roast']:
                st.markdown(f"""
                <div class="roast-card">
                    <div class="roast-content">{result['roast']['text']}</div>
                    <div class="roast-intensity">{result['roast']['intensity'].upper()}</div>
                </div>
                """, unsafe_allow_html=True)
            
            # Play audio
            if 'audio' in result and result['audio']:
                VoicePlayer(result['audio']).render()
            
            # Display metrics
            if 'metrics' in result:
                st.markdown("### 📈 Code Metrics")
                MetricsDisplay(result['metrics']).render()
            
            # Display issues
            if 'analysis' in result and 'issues' in result['analysis']:
                st.markdown("### ⚠️ Issues Found")
                issues = result['analysis']['issues']
                if issues:
                    for i, issue in enumerate(issues[:10]):  # Limit to 10 issues
                        st.markdown(f"**{i+1}.** {issue}")
                else:
                    st.success("🎉 No major issues found!")
            
            # Display suggestions
            if 'suggestions' in result:
                st.markdown("### 💡 Suggestions")
                for i, suggestion in enumerate(result['suggestions'][:5]):
                    st.markdown(f"**{i+1}.** {suggestion}")
            
            # Display corrected code
            if 'corrected_code' in result and result['corrected_code']:
                with st.expander("✨ Improved Code", expanded=False):
                    st.code(result['corrected_code'], language=language)
                    
                    # Download button
                    st.download_button(
                        label="📥 Download Improved Code",
                        data=result['corrected_code'],
                        file_name=f"improved_code.{get_file_extension(language)}",
                        mime="text/plain"
                    )
            
            # Share results
            st.markdown("---")
            if st.button("📤 Share Analysis", use_container_width=True):
                share_analysis(result)
        
        else:
            st.info("👈 Enter code and click 'Analyze & Roast' to see results")

def analyze_code(code, language, intensity):
    """Send code to backend for analysis"""
    try:
        response = requests.post(
            "http://localhost:5001/api/analyze",
            json={
                "code": code,
                "language": language,
                "roast_level": intensity,
                "user_id": st.session_state.get("user_id", "anonymous")
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            
            # Track in session state
            if 'stats' not in st.session_state:
                st.session_state.stats = {'analyses': 0, 'generations': 0}
            st.session_state.stats['analyses'] += 1
            
            return result
        else:
            st.error(f"Analysis failed: {response.text}")
            return None
            
    except Exception as e:
        st.error(f"Connection error: {str(e)}")
        return None

def get_default_code(language):
    """Get default code example for language"""
    examples = {
        "python": """def calculate_average(numbers):
    # Calculate average of numbers
    total = 0
    count = 0
    for n in numbers:
        total += n
        count += 1
    return total / count

# Test the function
data = [85, 90, 78, 92, 88]
avg = calculate_average(data)
print(f"Average: {avg}")""",
        
        "javascript": """function calculateAverage(numbers) {
    // Calculate average of numbers
    let total = 0;
    let count = 0;
    for (let n of numbers) {
        total += n;
        count++;
    }
    return total / count;
}

// Test the function
const data = [85, 90, 78, 92, 88];
const avg = calculateAverage(data);
console.log("Average:", avg);""",
        
        "java": """public class Main {
    public static double calculateAverage(int[] numbers) {
        // Calculate average of numbers
        int total = 0;
        int count = 0;
        for (int n : numbers) {
            total += n;
            count++;
        }
        return (double) total / count;
    }
    
    public static void main(String[] args) {
        int[] data = {85, 90, 78, 92, 88};
        double avg = calculateAverage(data);
        System.out.println("Average: " + avg);
    }
}"""
    }
    
    return examples.get(language, examples["python"])

def get_file_extension(language):
    """Get file extension for language"""
    extensions = {
        "python": "py",
        "javascript": "js",
        "java": "java",
        "cpp": "cpp",
        "typescript": "ts",
        "go": "go",
        "rust": "rs"
    }
    return extensions.get(language, "txt")

def share_analysis(result):
    """Share analysis results"""
    # This could be extended to save to database or generate shareable link
    st.success("Analysis saved! (Share functionality coming soon)")