import ast
import sys
import json
import random
import tempfile
import os
import requests
from pylint.lint import Run
from pylint.reporters.text import TextReporter
from radon.complexity import cc_visit
from radon.metrics import mi_visit
from flask import Flask, request, jsonify
from io import StringIO, BytesIO
import base64
import autopep8
from transformers import pipeline, GPT2Tokenizer, GPT2LMHeadModel
import re
import subprocess
import platform
from functools import lru_cache

app = Flask(__name__)

# Load fine-tuned DistilGPT-2 model for roasting
model_path = "./fine_tuned_distilgpt2"
try:
    tokenizer = GPT2Tokenizer.from_pretrained(model_path)
    tokenizer.pad_token = tokenizer.eos_token
    model = GPT2LMHeadModel.from_pretrained(model_path)
    roast_generator = pipeline('text-generation', model=model, tokenizer=tokenizer)
except Exception as e:
    print(f"Failed to load fine-tuned model: {e}. Falling back to pre-trained distilgpt2.")
    tokenizer = GPT2Tokenizer.from_pretrained('distilgpt2')
    tokenizer.pad_token = tokenizer.eos_token
    model = GPT2LMHeadModel.from_pretrained('distilgpt2')
    roast_generator = pipeline('text-generation', model='distilgpt2', tokenizer='distilgpt2')

# Load code generation model
code_generator = pipeline('text-generation', model='distilgpt2', tokenizer='distilgpt2')

# ElevenLabs API configuration
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = "pNInz6obpgDQGcFmaJgB"  # Default voice

# Expanded roast templates with more variety and sarcasm
ROAST_TEMPLATES = {
    "no_docstring": {
        "mild": [
            "No docstring for {name}? Documentation is for winners, I guess.",
            "Someone forgot to document {name}. Hope you remember what it does in 6 months!",
            "No docstring for {name}? I'm sure it's perfectly self-explanatory... not."
        ],
        "medium": [
            "No docstring for {name}? Guess we're playing 'guess the function' today.",
            "Documentation is like flossing - everyone knows they should do it, but {name} proves you don't.",
            "{name} with no docs? I bet your variable names are just as descriptive."
        ],
        "brutal": [
            "No docstring for {name}? Did you think code is self-documenting like your ego?",
            "Writing docs is hard, I get it. But leaving {name} undocumented is just lazy.",
            "If {name} were any less documented, it would be classified information."
        ]
    },
    "single_letter_var": {
        "mild": [
            "Variable '{name}'? Could you be any more cryptic?",
            "Ah, '{name}' - the variable name chosen by programmers who hate future readers.",
            "Single-letter variables like '{name}' make code look like algebra homework."
        ],
        "medium": [
            "Single-letter '{name}'? Saving bytes or just being lazy?",
            "Naming a variable '{name}' is like naming your child 'Child' - technically correct but deeply unhelpful.",
            "'{name}' as a variable? Did your creative juices dry up?"
        ],
        "brutal": [
            "'{name}' as a variable? Did your keyboard run out of letters?",
            "Single-letter variables are the programming equivalent of grunting instead of speaking.",
            "I've seen more descriptive variable names in minified JavaScript. '{name}' is just sad."
        ]
    },
    "generic_var": {
        "mild": [
            "'{name}' as a variable? How original.",
            "Another '{name}' variable? You're really pushing the boundaries of creativity.",
            "Ah, '{name}' - the go-to variable name when you can't be bothered to think."
        ],
        "medium": [
            "Oh, '{name}'? Did you get that from the 'Bad Variable Names' handbook?",
            "'{name}' is to variable names what 'thingy' is to object descriptions.",
            "Naming things is hard, but '{name}' isn't even trying."
        ],
        "brutal": [
            "'{name}' for a variable? I've seen more creativity in a blank text file.",
            "If '{name}' were any more generic, it would just be called 'variable'.",
            "Using '{name}' as a variable name is the programming equivalent of naming your dog 'Dog'."
        ]
    },
    "long_function": {
        "mild": [
            "Function '{name}' is a bit long. Consider breaking it up.",
            "'{name}' is getting a little lengthy there. Maybe it's time for a split?",
            "That '{name}' function is doing quite a lot. Might be time to delegate some responsibilities."
        ],
        "medium": [
            "'{name}' is longer than my patience with this code.",
            "Function '{name}' has more lines than my last grocery list. And that's saying something.",
            "If '{name}' were any longer, it would need its own chapter index."
        ],
        "brutal": [
            "'{name}' is so long, it needs its own zip code.",
            "This '{name}' function is the programming equivalent of a run-on sentence.",
            "I've seen shorter Russian novels than this '{name}' function."
        ]
    },
    "excessive_nesting": {
        "mild": [
            "Nesting depth {depth}? Getting a bit deep there.",
            "That's quite the nested structure you've got. Might want to flatten it out.",
            "With {depth} levels of nesting, you're building a code pyramid."
        ],
        "medium": [
            "{depth} levels of nesting? Are you building code or a matryoshka doll?",
            "This nesting is so deep, I need a flashlight to find my way out.",
            "At {depth} levels deep, your code is starting to resemble Inception."
        ],
        "brutal": [
            "Nesting depth {depth}? Your code is more tangled than headphone wires!",
            "With {depth} levels of nesting, you're one level away from creating a black hole.",
            "This code has more layers than an onion, and it's making me cry just the same."
        ]
    },
    "high_complexity": {
        "mild": [
            "Complexity {score} in '{name}'? That's... ambitious.",
            "Function '{name}' is getting a bit complex with a score of {score}.",
            "Cyclomatic complexity of {score} in '{name}'? That's quite the mental workout."
        ],
        "medium": [
            "Complexity {score} in '{name}'? More twisted than a mystery novel.",
            "With a complexity of {score}, '{name}' is like a Rube Goldberg machine.",
            "Function '{name}' has more paths than a choose-your-own-adventure book."
        ],
        "brutal": [
            "'{name}' with complexity {score}? Did you write this during an earthquake?",
            "Complexity {score}? This function is what happens when you give a monkey a keyboard.",
            "At complexity {score}, this function isn't code - it's a cry for help."
        ]
    },
    "low_maintainability": {
        "mild": [
            "Maintainability index {score}? Could use some improvement.",
            "A maintainability score of {score} suggests this code might be tricky to work with.",
            "With a maintainability index of {score}, future you might not be too happy."
        ],
        "medium": [
            "Score {score} for maintainability? This code will be legacy by tomorrow.",
            "Maintainability index of {score}? I've seen spaghetti code with better structure.",
            "At {score} maintainability, this code is like a house of cards in a wind tunnel."
        ],
        "brutal": [
            "{score} maintainability? This code is a time bomb waiting to explode!",
            "With a maintainability score of {score}, this code isn't just bad - it's archeologically significant.",
            "A maintainability index of {score} is what happens when you let autocorrect write your code."
        ]
    },
    "pylint": {
        "mild": [
            "{issue}? A small oversight.",
            "Found a little issue: {issue}. Easy fix!",
            "Minor problem detected: {issue}. Nothing to worry about."
        ],
        "medium": [
            "{issue}? Your code is trying to tell you something.",
            "I found {issue}. It's not a bug, it's a feature... right?",
            "Looks like we've got {issue}. Time for a quick fix!"
        ],
        "brutal": [
            "{issue}? This belongs in a coding horror museum!",
            "Seriously, {issue}? Did you even test this?",
            "{issue} detected. I've seen better code from a room full of typing cats."
        ]
    },
    "general": {
        "mild": [
            "I've seen better code from a first-year CS student.",
            "This code works, but it's not exactly elegant.",
            "There's room for improvement here, but it's not the worst I've seen."
        ],
        "medium": [
            "This code is like a IKEA furniture assembly - it works, but you're not sure how.",
            "I've seen more organized code in a kindergarten art project.",
            "This isn't bad code... it's just creatively structured."
        ],
        "brutal": [
            "This code is what happens when you let your cat walk on the keyboard.",
            "If this code were a person, it would be wearing socks with sandals.",
            "I've seen more logical reasoning from a Magic 8-Ball."
        ]
    }
}

# Expanded code generation examples
CODE_EXAMPLES = {
    "add two numbers": {
        "code": "def add_numbers(a, b):\n    \"\"\"Add two numbers together.\"\"\"\n    return a + b\n\n# Example usage\nresult = add_numbers(5, 3)\nprint(f\"The sum is: {result}\")",
        "roast": "You need help adding two numbers? Maybe you should stick to counting on your fingers."
    },
    "calculator": {
        "code": "def calculator(a, b, operation):\n    \"\"\"Perform basic arithmetic operations.\"\"\"\n    if operation == 'add':\n        return a + b\n    elif operation == 'subtract':\n        return a - b\n    elif operation == 'multiply':\n        return a * b\n    elif operation == 'divide':\n        if b != 0:\n            return a / b\n        else:\n            raise ValueError(\"Cannot divide by zero\")\n    else:\n        raise ValueError(\"Unsupported operation\")\n\n# Example usage\nresult = calculator(10, 5, 'add')\nprint(f\"Result: {result}\")",
        "roast": "A calculator? Really? Did you forget how to use the one on your phone?"
    },
    "hello world": {
        "code": "print(\"Hello, World!\")",
        "roast": "You need help with 'Hello World'? Maybe consider a different career."
    },
    "fibonacci": {
        "code": "def fibonacci(n):\n    \"\"\"Generate a Fibonacci sequence up to n elements.\"\"\"\n    if n <= 0:\n        return []\n    elif n == 1:\n        return [0]\n    elif n == 2:\n        return [0, 1]\n    \n    sequence = [0, 1]\n    for i in range(2, n):\n        sequence.append(sequence[i-1] + sequence[i-2])\n    return sequence\n\n# Example usage\nprint(fibonacci(10))",
        "roast": "Fibonacci sequence? At least you're trying something moderately interesting."
    },
    "file reader": {
        "code": "def read_file(filename):\n    \"\"\"Read and return the contents of a file.\"\"\"\n    try:\n        with open(filename, 'r') as file:\n            return file.read()\n    except FileNotFoundError:\n        print(f\"File {filename} not found\")\n        return None\n    except IOError:\n        print(f\"Error reading file {filename}\")\n        return None\n\n# Example usage\ncontent = read_file(\"example.txt\")\nif content:\n    print(content)",
        "roast": "Reading files is pretty basic stuff. Did you skip Programming 101?"
    },
    "sort list": {
        "code": "def sort_list(lst, reverse=False):\n    \"\"\"Sort a list in ascending or descending order.\"\"\"\n    return sorted(lst, reverse=reverse)\n\n# Example usage\nnumbers = [3, 1, 4, 1, 5, 9, 2, 6, 5]\nsorted_numbers = sort_list(numbers)\nprint(f\"Sorted numbers: {sorted_numbers}\")",
        "roast": "Sorting a list? Couldn't figure out the built-in sorted() function on your own?"
    }
}


def analyze_code(code, language="python"):
    """Analyze code and return issues and metrics."""
    issues = []
    metrics = {}
    
    if language == "python":
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.Module)):
                    if not ast.get_docstring(node):
                        issues.append(f"No docstring for {node.__class__.__name__.lower()} '{getattr(node, 'name', 'module')}'")
                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                    if len(node.id) == 1:
                        issues.append(f"Single-letter variable name '{node.id}'")
                    elif node.id.lower() in ['foo', 'bar', 'baz', 'temp', 'data', 'var', 'value', 'stuff', 'things']:
                        issues.append(f"Generic variable name '{node.id}'")
                if isinstance(node, ast.FunctionDef):
                    body_lines = sum(len(getattr(n, 'body', [])) for n in ast.walk(node))
                    if body_lines > 20:
                        issues.append(f"Overly long function '{node.name}'")
            
            def count_nesting(node, depth=0):
                if isinstance(node, (ast.For, ast.While, ast.If, ast.Try, ast.With)):
                    depth += 1
                    for child in ast.iter_child_nodes(node):
                        depth = max(depth, count_nesting(child, depth))
                return depth
            
            max_nesting = max(count_nesting(node) for node in ast.walk(tree))
            if max_nesting > 3:
                issues.append(f"Excessive nesting with depth {max_nesting}")
        except SyntaxError as e:
            # Clean up the error message for better readability
            error_msg = str(e).split('\n')[0]  # Get just the first line
            issues.append(f"Syntax error: {error_msg}")
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
            temp_file.write(code)
            temp_file_path = temp_file.name
        
        try:
            output = StringIO()
            Run([temp_file_path, '--disable=all', '--enable=W0612,E0602,W0703,E1120'], 
                reporter=TextReporter(output), exit=False)
            pylint_output = output.getvalue().splitlines()
            for line in pylint_output:
                if any(err in line for err in ["Unused variable", "Undefined variable", "Broad-except", "No value for argument"]):
                    # Clean up the pylint error message
                    clean_line = line.split(':')[-1].strip()  # Remove file path info
                    issues.append(clean_line)
        finally:
            os.unlink(temp_file_path)
        
        # Initialize complexity with default value
        complexity = []
        try:
            complexity = cc_visit(code)
            for func in complexity:
                if func.complexity > 10:
                    issues.append(f"High cyclomatic complexity {func.complexity} in function '{func.name}'")
        except Exception as e:
            print(f"Complexity analysis failed: {e}")
        
        try:
            mi_score = mi_visit(code, multi=True)
            if mi_score < 70:
                issues.append(f"Low maintainability index {mi_score:.1f}")
        except Exception as e:
            print(f"Maintainability analysis failed: {e}")
            mi_score = 100
        
        # Get max complexity safely
        max_complexity = 0
        if complexity:
            max_complexity = max([func.complexity for func in complexity] + [0])
        
        metrics = {
            "line_count": len(code.splitlines()),
            "cyclomatic_complexity": max_complexity,
            "maintainability_index": mi_score
        }
    elif language in ["javascript", "java"]:
        issues.append(f"{language} analysis not fully implemented yet.")
        metrics = {"line_count": len(code.splitlines()), "cyclomatic_complexity": 0, "maintainability_index": 0}
    
    return issues, metrics

def correct_code(code):
    """Correct Python code to follow PEP 8 and best practices."""
    # First, try to fix syntax errors using AI
    try:
        # Try to parse the code first to check for syntax errors
        ast.parse(code)
    except SyntaxError as e:
        # If there's a syntax error, try to fix it using the AI model
        try:
            fix_prompt = f"Fix the following Python code with syntax errors. Return only the corrected code:\n\n{code}"
            fixed_output = code_generator(fix_prompt, max_new_tokens=200, num_return_sequences=1, 
                                       temperature=0.3, truncation=True)[0]['generated_text']
            
            # Extract just the code part (remove the prompt)
            fixed_code = fixed_output.replace(fix_prompt, "").strip()
            
            # Try to parse the fixed code to see if it works
            ast.parse(fixed_code)
            code = fixed_code
        except:
            # If AI fixing fails, just return the original code with a comment
            return f"# Could not fix syntax errors in code:\n# {str(e).split(chr(10))[0]}\n\n{code}"
    
    # Apply autopep8 for formatting
    try:
        corrected_code = autopep8.fix_code(code, options={'aggressive': 2})
    except:
        corrected_code = code
    
    return corrected_code

def generate_roast(issues, roast_level="medium"):
    """Generate sarcastic roasts for code issues."""
    if not issues:
        return ["Wow, your code is actually decent. I'm almost disappointed."]
    
    roasts = []
    
    # Add a general roast about the overall code quality
    if "general" in ROAST_TEMPLATES and roast_level in ROAST_TEMPLATES["general"]:
        general_roast = random.choice(ROAST_TEMPLATES["general"][roast_level])
        roasts.append(general_roast)
    
    # Add specific roasts for each issue
    for issue in issues[:3]:  # Limit to 3 specific roasts to avoid overwhelming
        roast = None
        
        # Clean up the issue message for better roasting
        clean_issue = issue
        if "undefined-variable" in issue or "Undefined variable" in issue:
            clean_issue = "Undefined variable found in your code"
        elif "syntax error" in issue.lower():
            clean_issue = "Syntax error found in your code"
        elif "unused variable" in issue.lower():
            clean_issue = "Unused variable found in your code"
        
        if "No docstring" in clean_issue and "no_docstring" in ROAST_TEMPLATES:
            parts = clean_issue.split("'")
            name = parts[1] if len(parts) >= 3 else "this element"
            if roast_level in ROAST_TEMPLATES["no_docstring"]:
                roast = random.choice(ROAST_TEMPLATES["no_docstring"][roast_level]).format(name=name)
        
        elif "Single-letter variable" in clean_issue and "single_letter_var" in ROAST_TEMPLATES:
            parts = clean_issue.split("'")
            name = parts[1] if len(parts) >= 2 else "x"
            if roast_level in ROAST_TEMPLATES["single_letter_var"]:
                roast = random.choice(ROAST_TEMPLATES["single_letter_var"][roast_level]).format(name=name)
        
        elif "Generic variable name" in clean_issue and "generic_var" in ROAST_TEMPLATES:
            parts = clean_issue.split("'")
            name = parts[1] if len(parts) >= 2 else "data"
            if roast_level in ROAST_TEMPLATES["generic_var"]:
                roast = random.choice(ROAST_TEMPLATES["generic_var"][roast_level]).format(name=name)
        
        elif "Overly long function" in clean_issue and "long_function" in ROAST_TEMPLATES:
            parts = clean_issue.split("'")
            name = parts[1] if len(parts) >= 2 else "this function"
            if roast_level in ROAST_TEMPLATES["long_function"]:
                roast = random.choice(ROAST_TEMPLATES["long_function"][roast_level]).format(name=name)
        
        elif "Excessive nesting" in clean_issue and "excessive_nesting" in ROAST_TEMPLATES:
            parts = clean_issue.split()
            depth = parts[-1] if len(parts) >= 4 else "many"
            if roast_level in ROAST_TEMPLATES["excessive_nesting"]:
                roast = random.choice(ROAST_TEMPLATES["excessive_nesting"][roast_level]).format(depth=depth)
        
        elif "High cyclomatic complexity" in clean_issue and "high_complexity" in ROAST_TEMPLATES:
            parts = clean_issue.split("'")
            if len(parts) >= 4:
                name = parts[1]
                score = parts[3]
            else:
                name = "this function"
                score = "high"
            if roast_level in ROAST_TEMPLATES["high_complexity"]:
                roast = random.choice(ROAST_TEMPLATES["high_complexity"][roast_level]).format(name=name, score=score)
        
        elif "Low maintainability index" in clean_issue and "low_maintainability" in ROAST_TEMPLATES:
            parts = clean_issue.split()
            score = parts[-1] if len(parts) >= 4 else "low"
            if roast_level in ROAST_TEMPLATES["low_maintainability"]:
                roast = random.choice(ROAST_TEMPLATES["low_maintainability"][roast_level]).format(score=score)
        
        elif any(err in clean_issue.lower() for err in ["unused variable", "undefined variable", "broad-except", "no value for argument", "syntax error"]):
            if "pylint" in ROAST_TEMPLATES and roast_level in ROAST_TEMPLATES["pylint"]:
                roast = random.choice(ROAST_TEMPLATES["pylint"][roast_level]).format(issue=clean_issue)
        
        # Fallback if no specific roast was found
        if not roast:
            roast = f"{clean_issue}. You might want to look into that."
        
        roasts.append(roast)
    
    return roasts


def generate_code_from_prompt(prompt):
    """Generate code based on user prompt with sarcastic response."""
    prompt_lower = prompt.lower()
    
    # Check if prompt matches any known patterns
    for key in CODE_EXAMPLES:
        if key in prompt_lower:
            return CODE_EXAMPLES[key]["code"], CODE_EXAMPLES[key]["roast"]
    
    # Try to generate code using the model for unknown prompts
    try:
        code_prompt = f"Write Python code to {prompt}. Include proper docstrings and follow PEP 8 guidelines."
        code_output = code_generator(code_prompt, max_new_tokens=150, num_return_sequences=1, 
                                   temperature=0.7, truncation=True)[0]['generated_text']
        
        # Extract just the code part (remove the prompt)
        code = code_output.replace(code_prompt, "").strip()
        
        # Try to format the code
        try:
            code = autopep8.fix_code(code, options={'aggressive': 1})
        except:
            pass
        
        roast = random.choice([
            f"I generated code for '{prompt}', but honestly, if you can't write this yourself, maybe programming isn't for you.",
            f"Here's some code for '{prompt}'. Try to learn from it instead of just copying, okay?",
            f"Wow, you really need help with '{prompt}'? This is pretty basic stuff.",
            f"Generated code for '{prompt}'. Don't get too dependent on me now."
        ])
        
        return code, roast
    except Exception as e:
        print(f"Code generation failed: {e}")
        return f"# Could not generate code for: {prompt}", f"I could generate code for '{prompt}', but honestly, if you can't even describe what you need properly, maybe you should reconsider your life choices."

def text_to_speech(text, roast_level="medium"):
    """Convert text to speech using ElevenLabs or fallback to system TTS."""
    # First try ElevenLabs if API key is available
    if ELEVENLABS_API_KEY and ELEVENLABS_API_KEY != "sk_d5f7149c8cec460c474eb8689acd089ca0d029b7a85951fb":
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": ELEVENLABS_API_KEY
        }
        
        # Enhanced voice settings based on roast level for more emotion
        if roast_level == "mild":
            stability = 0.4
            similarity_boost = 0.8
            style = 0.3
            voice_id = "pNInz6obpgDQGcFmaJgB"  # Antoni - friendly
        elif roast_level == "medium":
            stability = 0.3
            similarity_boost = 0.7
            style = 0.5
            voice_id = "VR6AewLTigWG4xSOukaG"  # Arnold - sarcastic
        else:  # brutal
            stability = 0.2
            similarity_boost = 0.6
            style = 0.7
            voice_id = "AZnzlk1XvdvUeBnXmlld"  # Domi - energetic
        
        # Add more expressive text with pauses and emphasis
        expressive_text = add_expression_to_text(text, roast_level)
        
        data = {
            "text": expressive_text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": stability,
                "similarity_boost": similarity_boost,
                "style": style,
                "use_speaker_boost": True
            }
        }
        
        try:
            response = requests.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                json=data,
                headers=headers,
                timeout=15
            )
            response.raise_for_status()
            return BytesIO(response.content)
        except Exception as e:
            print(f"ElevenLabs failed: {e}. Falling back to system TTS.")
    
    # Fallback to system TTS based on platform
    try:
        if platform.system() == "Darwin":  # macOS
            return generate_audio_with_say_simple(text, roast_level)
        elif platform.system() == "Windows":  # Windows
            return generate_audio_with_windows_tts(text)
        else:  # Linux
            return generate_audio_with_linux_tts(text)
    except Exception as e:
        print(f"System TTS also failed: {e}")
        # Return None if all TTS methods fail - this won't break the app
        return None

def generate_audio_with_say_simple(text, roast_level):
    """Generate audio using macOS 'say' command with simple approach."""
    try:
        # Create a temporary file
        with tempfile.NamedTemporaryFile(suffix='.aiff', delete=False) as temp_file:
            temp_path = temp_file.name
        
        # Use basic macOS 'say' command without complex parameters
        cmd = [
            'say', 
            '-o', temp_path,
            text
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            print(f"macOS 'say' command failed: {result.stderr}")
            return None
        
        # Convert AIFF to MP3 using afconvert
        mp3_path = temp_path.replace('.aiff', '.mp3')
        convert_result = subprocess.run(['afconvert', '-f', 'mp4f', '-d', 'aac', temp_path, mp3_path], 
                                      capture_output=True, text=True, timeout=30)
        
        if convert_result.returncode != 0:
            print(f"afconvert failed: {convert_result.stderr}")
            return None
        
        # Read the MP3 file
        with open(mp3_path, 'rb') as f:
            audio_data = f.read()
        
        # Clean up
        os.unlink(temp_path)
        os.unlink(mp3_path)
        
        return BytesIO(audio_data)
    except Exception as e:
        print(f"macOS audio generation failed: {e}")
        return None
    
def add_expression_to_text(text, roast_level):
    """Add pauses and emphasis to make the speech more expressive."""
    # Add pauses for dramatic effect
    phrases = text.split('. ')
    expressive_text = ""
    
    for i, phrase in enumerate(phrases):
        if phrase.strip():
            # Add emphasis based on roast level
            if roast_level == "brutal" and any(keyword in phrase.lower() for keyword in ["disaster", "horrible", "terrible", "awful"]):
                expressive_text += f"<emphasis level=\"strong\">{phrase}</emphasis>"
            elif roast_level == "medium" and any(keyword in phrase.lower() for keyword in ["really", "seriously", "actually"]):
                expressive_text += f"<emphasis level=\"moderate\">{phrase}</emphasis>"
            else:
                expressive_text += phrase
                
            # Add pauses between phrases
            if i < len(phrases) - 1:
                expressive_text += f"...<break time=\"500ms\"/> "
            else:
                expressive_text += ".<break time=\"300ms\"/>"
    
    # Add intro based on roast level
    if roast_level == "brutal":
        expressive_text = f"<prosody rate=\"slow\" pitch=\"low\">Oh my god...</prosody><break time=\"700ms\"/> {expressive_text}"
    elif roast_level == "medium":
        expressive_text = f"<prosody rate=\"medium\" pitch=\"medium\">Okay, let's see...</prosody><break time=\"500ms\"/> {expressive_text}"
    else:
        expressive_text = f"<prosody rate=\"fast\" pitch=\"high\">Alright then...</prosody><break time=\"300ms\"/> {expressive_text}"
    
    return expressive_text


def generate_audio_with_say(text, roast_level):
    """Generate audio using macOS 'say' command with more expressive voices."""
    try:
        # Create a temporary file
        with tempfile.NamedTemporaryFile(suffix='.aiff', delete=False) as temp_file:
            temp_path = temp_file.name
        
        # Adjust voice and rate based on roast level for more expression
        if roast_level == "mild":
            voice = "Samantha"
            rate = 170
            pitch = 50
        elif roast_level == "medium":
            voice = "Fred"  # More sarcastic tone
            rate = 160
            pitch = 40
        else:  # brutal
            voice = "Victoria"  # More dramatic tone
            rate = 150
            pitch = 30
        
        # Use macOS 'say' command to generate audio with more expression
        cmd = [
            'say', 
            '-v', voice,
            '-r', str(rate),
            '-p', str(pitch),
            '-o', temp_path,
            text
        ]
        subprocess.run(cmd, check=True, timeout=30, capture_output=True)
        
        # Convert AIFF to MP3 using afconvert
        mp3_path = temp_path.replace('.aiff', '.mp3')
        subprocess.run(['afconvert', '-f', 'mp4f', '-d', 'aac', temp_path, mp3_path], 
                      check=True, timeout=30, capture_output=True)
        
        # Read the MP3 file
        with open(mp3_path, 'rb') as f:
            audio_data = f.read()
        
        # Clean up
        os.unlink(temp_path)
        os.unlink(mp3_path)
        
        return BytesIO(audio_data)
    except Exception as e:
        print(f"macOS 'say' command failed: {e}")
        return None

def generate_audio_with_windows_tts(text):
    """Generate audio using Windows TTS."""
    try:
        # For Windows, we'll use a simple approach with gTTS as fallback
        from gtts import gTTS
        
        # Create in-memory file
        mp3_fp = BytesIO()
        tts = gTTS(text=text, lang='en')
        tts.write_to_fp(mp3_fp)
        mp3_fp.seek(0)
        
        return mp3_fp
    except Exception as e:
        print(f"Windows TTS failed: {e}")
        return None

def generate_audio_with_linux_tts(text):
    """Generate audio using Linux TTS (espeak)."""
    try:
        # Create a temporary file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            temp_path = temp_file.name
        
        # Use espeak to generate audio
        cmd = [
            'espeak',
            '-w', temp_path,
            text
        ]
        subprocess.run(cmd, check=True, timeout=30, capture_output=True)
        
        # Read the WAV file
        with open(temp_path, 'rb') as f:
            audio_data = f.read()
        
        # Clean up
        os.unlink(temp_path)
        
        return BytesIO(audio_data)
    except Exception as e:
        print(f"Linux TTS failed: {e}")
        return None

@app.route('/api/roast', methods=['POST'])
def roast_code():
    data = request.json
    code = data.get('code', '')
    roast_level = data.get('roast_level', 'medium')
    language = data.get('language', 'python')
    
    if not code:
        return jsonify({"error": "No code provided"}), 400
    
    try:
        issues, metrics = analyze_code(code, language)
        
        if not issues:
            roasts = ["No issues found. Either you're a coding genius or this is your first successful program!"]
            audio_data = text_to_speech("Wow, your code is actually pretty good. I'm almost disappointed.", roast_level)
        else:
            roasts = generate_roast(issues, roast_level)
            roast_text = " ".join(roasts)
            audio_data = text_to_speech(roast_text, roast_level)
        
        corrected_code = correct_code(code) if language == "python" else code
        
        audio_b64 = None
        if audio_data:
            audio_b64 = base64.b64encode(audio_data.getvalue()).decode('utf-8')
        
        return jsonify({
            "roasts": roasts,
            "corrected_code": corrected_code,
            "metrics": metrics,
            "audio": audio_b64
        })
    
    except Exception as e:
        print(f"Error in roast_code: {e}")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

@app.route('/api/generate', methods=['POST'])
def generate_code_endpoint():
    data = request.json
    prompt = data.get('prompt', '')
    
    if not prompt:
        return jsonify({"error": "No prompt provided"}), 400
    
    try:
        code, roast = generate_code_from_prompt(prompt)
        audio_data = text_to_speech(roast, "medium")
        
        audio_b64 = None
        if audio_data:
            audio_b64 = base64.b64encode(audio_data.getvalue()).decode('utf-8')
        
        return jsonify({
            "roast": roast,
            "code": code,
            "audio_file": audio_b64
        })
    
    except Exception as e:
        print(f"Error in generate_code_endpoint: {e}")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "model_loaded": True})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)