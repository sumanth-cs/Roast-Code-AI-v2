import ast
import pylint.lint
import pyttsx3
import sys
import json
import random
import tempfile
import os
import requests
try:
    from transformers import pipeline, GPT2Tokenizer, GPT2LMHeadModel
except ImportError as e:
    print(f"Error importing transformers: {e}. Please reinstall with: pip install transformers==4.38.2")
    sys.exit(1)
from radon.complexity import cc_visit
from radon.metrics import mi_visit
from flask import Flask, request, jsonify
from io import StringIO
import base64
import time

app = Flask(__name__)

# Load fine-tuned DistilGPT-2 model
model_path = "./fine_tuned_distilgpt2"
try:
    tokenizer = GPT2Tokenizer.from_pretrained(model_path)
    tokenizer.pad_token = tokenizer.eos_token
    model = GPT2LMHeadModel.from_pretrained(model_path)
    generator = pipeline('text-generation', model=model, tokenizer=tokenizer)
except Exception as e:
    print(f"Failed to load fine-tuned model: {e}. Falling back to pre-trained distilgpt2.")
    tokenizer = GPT2Tokenizer.from_pretrained('distilgpt2')
    tokenizer.pad_token = tokenizer.eos_token
    model = GPT2LMHeadModel.from_pretrained('distilgpt2')
    generator = pipeline('text-generation', model='distilgpt2', tokenizer='distilgpt2')

# ElevenLabs API configuration
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "sk_d5f7149c8cec460c474eb8689acd089ca0d029b7a85951fb")
ELEVENLABS_VOICE_ID = "pNInz6obpgDQGcFmaJgB"  # Indian-accented voice (Antoni)

def analyze_code(code):
    """Analyze code using AST, pylint, and complexity metrics."""
    issues = []
    
    try:
        tree = ast.parse(code)
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.Module)):
                if not ast.get_docstring(node):
                    issues.append(f"No docstring for {node.__class__.__name__.lower()} '{getattr(node, 'name', 'module')}'")
            
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                if len(node.id) == 1:
                    issues.append(f"Single-letter variable name '{node.id}'")
                elif node.id.lower() in ['foo', 'bar', 'baz', 'temp', 'data']:
                    issues.append(f"Generic variable name '{node.id}'")
            
            if isinstance(node, ast.FunctionDef):
                body_lines = sum(len(getattr(n, 'body', [])) for n in ast.walk(node))
                if body_lines > 20:
                    issues.append(f"Overly long function '{node.name}'")
        
        def count_nesting(node, depth=0):
            if isinstance(node, (ast.For, ast.While)):
                depth += 1
                for child in ast.iter_child_nodes(node):
                    depth = max(depth, count_nesting(child, depth))
            return depth
        max_nesting = max(count_nesting(node) for node in ast.walk(tree))
        if max_nesting > 3:
            issues.append(f"Excessive nesting with depth {max_nesting}")
    
    except SyntaxError:
        issues.append("Syntax error in code")
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
        temp_file.write(code)
        temp_file_path = temp_file.name
    
    pylint_output = []
    try:
        from pylint.reporters.text import TextReporter
        output = StringIO()
        pylint.lint.Run([temp_file_path, '--disable=all', '--enable=W0612,E0602,W0703'], reporter=TextReporter(output), exit=False)
        pylint_output = output.getvalue().splitlines()
        for line in pylint_output:
            if any(err in line for err in ["Unused variable", "Undefined variable", "Broad-except"]):
                issues.append(line.strip())
    finally:
        os.unlink(temp_file_path)
    
    complexity = cc_visit(code)
    for func in complexity:
        if func.complexity > 10:
            issues.append(f"High cyclomatic complexity {func.complexity} in function '{func.name}'")
    
    mi_score = mi_visit(code, multi=True)
    if mi_score < 70:
        issues.append(f"Low maintainability index {mi_score:.1f}")
    
    return issues

def generate_ml_roast(issues, roast_level="medium"):
    """Generate sarcastic roasts using fine-tuned DistilGPT-2 with Indian context."""
    temperature_map = {"mild": 0.7, "medium": 0.9, "brutal": 1.2}
    temperature = temperature_map.get(roast_level, 0.9)
    
    indian_context = [
        "like a street vendor hawking buggy code in a Mumbai bazaar",
        "as chaotic as a Delhi traffic jam during Diwali",
        "straight out of a Bollywood script with zero logic",
        "like a chai stall's code: small, messy, but somehow functional",
        "worthy of a 500 error on an Indian Railways booking site"
    ]
    
    roasts = []
    for issue in issues:
        prompt = f"Generate a {roast_level} sarcastic roast in 20-30 words for a coding issue: '{issue}'. Include a funny Indian cultural reference."
        try:
            ml_roast = generator(prompt, max_new_tokens=30, num_return_sequences=1, temperature=temperature, truncation=True)[0]['generated_text']
            roast = ml_roast.split('\n')[0]
            if len(roast) < 10 or "Generate" in roast:
                roast = generate_template_roast(issue, roast_level)
            else:
                roast += f" {random.choice(indian_context)}."
        except Exception as e:
            print(f"ML roast generation failed: {e}. Using template roast.")
            roast = generate_template_roast(issue, roast_level)
        roasts.append(roast)
    
    return roasts

def generate_template_roast(issue, roast_level):
    """Fallback rule-based roast generation with roast level adjustment."""
    with open('roast_templates.json', 'r') as f:
        templates = json.load(f)
    
    indian_flavor = random.choice([
        "like a dosa flipped by a sleepy cook",
        "as messy as a Bangalore auto rickshaw race",
        "straight from a Vadapav stall's greasy counter"
    ])
    
    severity = {
        "mild": ["Oops, {issue}. Did you forget your coding basics at the chai stall?"],
        "medium": ["Really, {issue}? Even a roadside coder in Bangalore would blush."],
        "brutal": ["{issue}? This code is a disaster worse than a Mumbai monsoon flood!"]
    }
    
    if "No docstring" in issue:
        roast = random.choice(templates["no_docstring"][roast_level]).format(name=issue.split("'")[-2])
    elif "Single-letter variable" in issue:
        roast = random.choice(templates["single_letter_var"][roast_level]).format(name=issue.split("'")[1])
    elif "Generic variable name" in issue:
        roast = random.choice(templates["generic_var"][roast_level]).format(name=issue.split("'")[1])
    elif "Overly long function" in issue:
        roast = random.choice(templates["long_function"][roast_level]).format(name=issue.split("'")[1])
    elif "Excessive nesting" in issue:
        roast = random.choice(templates["excessive_nesting"][roast_level]).format(depth=issue.split()[-1])
    elif "High cyclomatic complexity" in issue:
        roast = random.choice(templates["high_complexity"][roast_level]).format(name=issue.split("'")[1], score=issue.split()[3])
    elif "Low maintainability index" in issue:
        roast = random.choice(templates["low_maintainability"][roast_level]).format(score=issue.split()[-1])
    elif any(err in issue for err in ["Unused variable", "Undefined variable", "Broad-except"]):
        roast = random.choice(templates["pylint"][roast_level]).format(issue=issue)
    else:
        roast = random.choice(severity[roast_level]).format(issue=issue)
    
    return f"{roast} {indian_flavor}."

def roast_to_speech(roasts, roast_level):
    """Convert roast text to speech using ElevenLabs with Indian-accented voice."""
    audio_files = []
    for roast in roasts:
        pause_duration = {"mild": 0.5, "medium": 1.0, "brutal": 1.5}
        time.sleep(pause_duration[roast_level])
        
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": ELEVENLABS_API_KEY
        }
        data = {
            "text": roast,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75
            }
        }
        
        try:
            response = requests.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}",
                json=data,
                headers=headers
            )
            response.raise_for_status()
            audio_path = f"roast_{random.randint(1000, 9999)}.mp3"
            with open(audio_path, 'wb') as f:
                f.write(response.content)
            audio_files.append(audio_path)
        except Exception as e:
            print(f"ElevenLabs failed: {e}. Falling back to pyttsx3.")
            engine = pyttsx3.init()
            engine.setProperty('rate', 160)
            engine.setProperty('volume', 0.9)
            voices = engine.getProperty('voices')
            for voice in voices:
                if 'english' in voice.name.lower() or 'default' in voice.name.lower():
                    engine.setProperty('voice', voice.id)
                    break
            print(roast)
            engine.say(roast)
            engine.runAndWait()
    
    return audio_files

@app.route('/api/roast', methods=['POST'])
def roast_code():
    data = request.json
    code = data.get('code', '')
    roast_level = data.get('roast_level', 'medium')
    
    if not code:
        return jsonify({"error": "No code provided"}), 400
    
    issues = analyze_code(code)
    if not issues:
        return jsonify({"roasts": ["No issues found. Did you write this in a Himalayan coding retreat? Too clean!"], "audio_files": []})
    
    roasts = generate_ml_roast(issues, roast_level)
    audio_files = roast_to_speech(roasts, roast_level)
    audio_b64 = []
    for audio_file in audio_files:
        with open(audio_file, 'rb') as f:
            audio_b64.append(base64.b64encode(f.read()).decode('utf-8'))
        os.remove(audio_file)
    
    return jsonify({"roasts": roasts, "audio_files": audio_b64})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)