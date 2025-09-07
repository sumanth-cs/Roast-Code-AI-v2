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
import openai
import os
from typing import List

app = Flask(__name__)

# Initialize OpenAI client
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY  # Add this line
else:
    print("OpenAI API key not found. Enhanced code correction will be disabled.")

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

# ElevenLabs API configuration - USE YOUR REAL API KEY HERE
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
if not ELEVENLABS_API_KEY:
    print("ElevenLabs API key not found. Voice features will be disabled.")
ELEVENLABS_VOICE_ID = "pNInz6obpgDQGcFmaJgB"

# Expanded roast templates with more variety and sarcasm
ROAST_TEMPLATES= {
    "no_docstring": {
        "mild": [
            "Bruh, no docstring? Did you forget what `{name}` does, or are you hoping nobody asks?",
            "You call this documentation? My dog can write better comments.",
            "I've seen more descriptive code comments on a blank page. What is `{name}` even doing?"
        ],
        "medium": [
            "Look, I'm just an AI, but even I need an instruction manual. What is `{name}`?!",
            "This isn't code. It's a mystery box, and I don't want to open it.",
            "If `{name}` were any less documented, it would be a classified secret."
        ],
        "brutal": [
            "Bruh, you're not a hero for skipping the docs on `{name}`. You're just lazy.",
            "This isn't code. It's an elaborate prank on the next person who reads this.",
            "I've seen more readable ancient hieroglyphs than this undocumented `{name}`."
        ]
    },
    "single_letter_var": {
        "mild": [
            "A single letter variable, `{name}`? How original. Did you run out of ideas?",
            "'{name}'? Seriously? My cat walks across the keyboard and creates more meaningful variable names.",
            "I've seen more descriptive text on a traffic sign."
        ],
        "medium": [
            "Bruh, '{name}'? You're not saving bytes, you're just making me sad.",
            "This isn't a variable, it's a placeholder for an actual thought.",
            "I'm guessing '{name}' stands for 'I have no idea what to call this'."
        ],
        "brutal": [
            "'{name}'? What a trash variable name. Did your keyboard run out of letters?",
            "I bet your creative juices dried up. Now you're using single letters like a caveman.",
            "I'd rather stare at a blank screen than try to figure out what `{name}` is."
        ]
    },
    "generic_var": {
        "mild": [
            "Oh, '{name}'? Did you get that from the 'Bad Variable Names' handbook?",
            "'{name}' is to variables what 'thingy' is to object descriptions.",
            "You're not being lazy with `{name}`. You're just being a genius... at not trying."
        ],
        "medium": [
            "I've seen more creative variable names on a license plate.",
            "Bruh, `{name}`? I’ve seen more creative code from a room full of typing cats.",
            "If `{name}` were any more generic, it would just be called 'variable'."
        ],
        "brutal": [
            "This variable `{name}` is a choice. A poor, poor choice.",
            "Using `{name}` is a clear sign you've given up on life.",
            "I've seen more creativity in a blank text file."
        ]
    },
    "long_function": {
        "mild": [
            "Bruh, `{name}` is longer than my patience with this code. Break it up, maybe?",
            "I feel like I need an intermission to get through `{name}`. It's not a novel, it's code.",
            "That function `{name}` is doing quite a lot. Are you sure it's not trying to solve world peace?"
        ],
        "medium": [
            "I've seen shorter Russian novels than this function. I hope `{name}` is worth it.",
            "Is `{name}` a function or a cry for help?",
            "This isn't a function. It's a run-on sentence."
        ],
        "brutal": [
            "This function is so long, it needs its own zip code.",
            "I'm afraid to touch this function. It looks like a house of cards in a wind tunnel.",
            "Did you write this during an earthquake?"
        ]
    },
    "excessive_nesting": {
        "mild": [
            "Nesting depth `{depth}`? Are you building code or a Matryoshka doll?",
            "Bruh, this nesting is so deep, I need a flashlight to find my way out.",
            "This code has more layers than an onion, and it's making me cry just the same."
        ],
        "medium": [
            "With `{depth}` levels of nesting, your code is starting to resemble Inception.",
            "Your code looks like a staircase designed by a sadist.",
            "This nesting is so tangled, it's like headphone wires in a black hole."
        ],
        "brutal": [
            "I've seen more straightforward tax code than this.",
            "I'm pretty sure you're one level away from creating a black hole with this code.",
            "This nesting is a disaster."
        ]
    },
    "high_complexity": {
        "mild": [
            "Complexity `{score}` in `{name}`? That's... ambitious. Or just lazy.",
            "With a complexity of `{score}`, `{name}` is more twisted than a mystery novel.",
            "This function has more paths than a choose-your-own-adventure book. Good luck."
        ],
        "medium": [
            "Complexity `{score}`? This function is what happens when you give a monkey a keyboard.",
            "This isn't code, it’s modern art. Unreadable, but full of emotion.",
            "At complexity `{score}`, this function isn't code, it's a Rube Goldberg machine."
        ],
        "brutal": [
            "Complexity `{score}`? I've seen simpler nuclear launch codes.",
            "My dog can code better than this. What a trash code.",
            "This isn't a function, it's a cry for help."
        ]
    },
    "low_maintainability": {
        "mild": [
            "Maintainability index `{score}`? This code will be legacy by tomorrow.",
            "This code is like a house of cards in a wind tunnel. Don't touch it.",
            "With a maintainability index of `{score}`, future you will hate past you."
        ],
        "medium": [
            "I've seen spaghetti code with better structure.",
            "Your maintainability score is `{score}`. I'm afraid to touch this.",
            "This code isn't just bad; it's archeologically significant."
        ],
        "brutal": [
            "Maintainability `{score}`. This code isn't a bug; it's a lifestyle.",
            "I'd rather debug my own brain than this code.",
            "A maintainability score of `{score}` is what happens when you let autocorrect write your code."
        ]
    },
    "pylint": {
        "mild": [
            "Found a little issue: `{issue}`. Easy fix!",
            "Looks like we've got `{issue}`. Time for a quick fix!",
            "I found `{issue}`. It's not a bug, it's a feature... right?"
        ],
        "medium": [
            "Your code is trying to tell you something: `{issue}`.",
            "I've seen better code from a room full of typing cats. `{issue}`.",
            "Seriously, `{issue}`? Did you even test this?"
        ],
        "brutal": [
            "`{issue}` detected. This belongs in a coding horror museum!",
            "Are you a programmer or a professional procrastinator?",
            "What did you do to your code to get `{issue}`?"
        ]
    },
    "general": {
        "mild": [
            "This code works, but it's not exactly elegant.",
            "I've seen better code from a first-year CS student.",
            "This isn't bad code... it's just creatively structured."
        ],
        "medium": [
            "This code is like a IKEA furniture assembly - it works, but you're not sure how.",
            "I've seen more organized code in a kindergarten art project.",
            "I've seen more logical reasoning from a Magic 8-Ball."
        ],
        "brutal": [
            "This code is what happens when you let your cat walk on the keyboard.",
            "If this code were a person, it would be wearing socks with sandals.",
            "I've seen more logic in a bad romance novel."
        ]
    }
}

# Expanded code generation examples
CODE_EXAMPLES = {
    "add two numbers": {
        "code": "def add_numbers(a, b):\n    \"\"\"Add two numbers together.\"\"\"\n    return a + b\n\n# Example usage\nresult = add_numbers(5, 3)\nprint(f\"The sum is: {result}\")",
        "roast": "A function for adding two numbers, bruh? Did your calculator break or what?"
    },
    "calculator": {
        "code": "def calculator(a, b, operation):\n    \"\"\"Perform basic arithmetic operations.\"\"\"\n    if operation == 'add':\n        return a + b\n    elif operation == 'subtract':\n        return a - b\n    elif operation == 'multiply':\n        return a * b\n    elif operation == 'divide':\n        if b != 0:\n            return a / b\n        else:\n            raise ValueError(\"Cannot divide by zero\")\n    else:\n        raise ValueError(\"Unsupported operation\")\n\n# Example usage\nresult = calculator(10, 5, 'add')\nprint(f\"Result: {result}\")",
        "roast": "What a trash calculator. I've seen more innovation on a Speak & Spell."
    },
    "hello world": {
        "code": "print(\"Hello, World!\")",
        "roast": "You call that code? My dog can code a better 'Hello World' in its sleep."
    },
    "fibonacci": {
        "code": "def fibonacci(n):\n    \"\"\"Generate a Fibonacci sequence up to n elements.\"\"\"\n    if n <= 0:\n        return []\n    elif n == 1:\n        return [0]\n    elif n == 2:\n        return [0, 1]\n    \n    sequence = [0, 1]\n    for i in range(2, n):\n        sequence.append(sequence[i-1] + sequence[i-2])\n    return sequence\n\n# Example usage\nprint(fibonacci(10))",
        "roast": "Fibonacci? Seriously, bruh? Is this your final project for CS101?"
    },
    "file reader": {
        "code": "def read_file(filename):\n    \"\"\"Read and return the contents of a file.\"\"\"\n    try:\n        with open(filename, 'r') as file:\n            return file.read()\n    except FileNotFoundError:\n        print(f\"File {filename} not found\")\n        return None\n    except IOError:\n        print(f\"Error reading file {filename}\")\n        return None\n\n# Example usage\ncontent = read_file(\"example.txt\")\nif content:\n    print(content)",
        "roast": "I've seen more creative file readers from a toddler's toy. What a trash."
    },
    "sort list": {
        "code": "def sort_list(lst, reverse=False):\n    \"\"\"Sort a list in ascending or descending order.\"\"\"\n    return sorted(lst, reverse=reverse)\n\n# Example usage\nnumbers = [3, 1, 4, 1, 5, 9, 2, 6, 5]\nsorted_numbers = sort_list(numbers)\nprint(f\"Sorted numbers: {sorted_numbers}\")",
        "roast": "You wrote a whole function for `sorted()`? Bruh, just use the built-in function."
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

def enhanced_correct_code(code: str, issues: List[str]) -> str:
    """
    Use OpenAI to intelligently correct code based on identified issues.
    """
    if not OPENAI_API_KEY:  # Change this line
        # Fallback to basic correction if no OpenAI client
        try:
            return autopep8.fix_code(code, options={'aggressive': 2})
        except:
            return code
    
    # Create a prompt that explains the issues and asks for correction
    issues_text = "\n".join([f"- {issue}" for issue in issues])
    
    prompt = f"""
    Please correct the following Python code to fix these issues:
    {issues_text}
    
    Additionally, ensure the code follows PEP 8 guidelines, has proper docstrings, 
    and uses meaningful variable names.
    
    Return only the corrected code without any explanations.
    
    Code to correct:
    ```python
    {code}
    ```
    """
    
    try:
        # Use the OLD OpenAI API format
        response = openai.ChatCompletion.create(  # Change this line
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful Python code assistant that improves code quality."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            temperature=0.2
        )
        
        corrected_code = response.choices[0].message.content.strip()  # This line stays the same
        
        # Extract code from markdown code blocks if present
        if "```python" in corrected_code:
            corrected_code = corrected_code.split("```python")[1].split("```")[0].strip()
        elif "```" in corrected_code:
            corrected_code = corrected_code.split("```")[1].split("```")[0].strip()
            
        return corrected_code
        
    except Exception as e:
        print(f"OpenAI correction failed: {e}")
        # Fallback to autopep8
        try:
            return autopep8.fix_code(code, options={'aggressive': 2})
        except:
            return code

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
    if ELEVENLABS_API_KEY:
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
            print(f"Attempting ElevenLabs API call with voice_id: {voice_id}")
            response = requests.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                json=data,
                headers=headers,
                timeout=15
            )
            
            # Check if the response is successful
            if response.status_code == 200:
                print("ElevenLabs API call successful!")
                return BytesIO(response.content)
            else:
                print(f"ElevenLabs API failed with status code: {response.status_code}")
                print(f"Response text: {response.text}")
                
                # Check for specific error conditions
                if response.status_code == 401:
                    print("ERROR: Invalid API key. Please check your ElevenLabs API key.")
                elif response.status_code == 402:
                    print("ERROR: Quota exceeded. Check your ElevenLabs subscription.")
                elif response.status_code == 422:
                    print("ERROR: Invalid request parameters. Check your voice_id and data format.")
                elif response.status_code == 429:
                    print("ERROR: Rate limit exceeded. Try again later.")
                    
        except requests.exceptions.Timeout:
            print("ERROR: ElevenLabs API request timed out.")
        except requests.exceptions.ConnectionError:
            print("ERROR: Failed to connect to ElevenLabs API. Check your internet connection.")
        except Exception as e:
            print(f"ERROR: ElevenLabs API call failed: {e}")
    
    # Fallback to system TTS based on platform
    print("Falling back to system TTS...")
    try:
        if platform.system() == "Darwin":  # macOS
            return generate_audio_with_say(text, roast_level)
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
    # Map roast level to expressive parameters
    expression_config = {
        "mild": {
            "intro": "Alright, let's take a look at this...",
            "pause_time": "300ms",
            "rate": "fast",
            "pitch": "high",
            "emphasis": "moderate"
        },
        "medium": {
            "intro": "Okay, let's see what we have here...",
            "pause_time": "500ms", 
            "rate": "medium",
            "pitch": "medium",
            "emphasis": "strong"
        },
        "brutal": {
            "intro": "Oh my god... what is this mess...",
            "pause_time": "700ms",
            "rate": "slow",
            "pitch": "low",
            "emphasis": "strong"
        }
    }
    
    config = expression_config.get(roast_level, expression_config["medium"])
    
    # Add dramatic pauses and emphasis to key words
    emphasis_words = {
        "mild": ["maybe", "consider", "suggestion", "improve"],
        "medium": ["problem", "issue", "error", "fix", "should"],
        "brutal": ["terrible", "awful", "horrible", "disaster", "trash", "lazy", "bad", "wrong"]
    }
    
    words = text.split()
    expressive_text = ""
    
    for i, word in enumerate(words):
        # Add emphasis to key words based on roast level
        if any(keyword in word.lower() for keyword in emphasis_words[roast_level]):
            expressive_text += f'<emphasis level="{config["emphasis"]}">{word}</emphasis>'
        else:
            expressive_text += word
            
        # Add pauses for dramatic effect
        if i < len(words) - 1:
            if roast_level == "brutal" and random.random() < 0.1:
                expressive_text += f'...<break time="{config["pause_time"]}"/> '
            elif roast_level == "medium" and random.random() < 0.05:
                expressive_text += f'<break time="{config["pause_time"]}"/> '
            else:
                expressive_text += " "
    
    # Add expressive intro based on roast level
    expressive_intro = f'<prosody rate="{config["rate"]}" pitch="{config["pitch"]}">{config["intro"]}</prosody><break time="{config["pause_time"]}"/>'
    
    return expressive_intro + expressive_text


def generate_audio_with_say(text, roast_level):
    """Generate audio using macOS 'say' command with more expressive voices."""
    try:
        # Create a temporary file
        with tempfile.NamedTemporaryFile(suffix='.aiff', delete=False) as temp_file:
            temp_path = temp_file.name
            
        # More expressive voice mapping
        voice_mapping = {
            "mild": ["Samantha", "150", "50"],  # [voice, rate, pitch]
            "medium": ["Fred", "140", "40"],     # More sarcastic tone
            "brutal": ["Victoria", "130", "30"]  # More dramatic tone
        }
        
        voice, rate, pitch = voice_mapping.get(roast_level, ["Fred", "140", "40"])
        
        # Use macOS 'say' command to generate audio with more expression
        cmd = [
            'say', 
            '-v', voice,
            '-r', rate,
            '-p', pitch,
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
    """Generate audio using Windows TTS with better quality."""
    try:
        # Use pyttsx3 for better Windows TTS
        import pyttsx3
        
        engine = pyttsx3.init()
        
        # Set properties for better sound
        engine.setProperty('rate', 180)  # Speed percent
        engine.setProperty('volume', 0.9)  # Volume 0-1
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
            temp_path = temp_file.name
            
        engine.save_to_file(text, temp_path)
        engine.runAndWait()
        
        # Read the file
        with open(temp_path, 'rb') as f:
            audio_data = f.read()
            
        # Clean up
        os.unlink(temp_path)
        return BytesIO(audio_data)
        
    except Exception as e:
        print(f"Windows pyttsx3 failed: {e}")
        # Fallback to gTTS
        try:
            from gtts import gTTS
            mp3_fp = BytesIO()
            tts = gTTS(text=text, lang='en', slow=False)
            tts.write_to_fp(mp3_fp)
            mp3_fp.seek(0)
            return mp3_fp
        except Exception as e:
            print(f"Windows gTTS also failed: {e}")
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
        
        # Use the enhanced correction function
        corrected_code = enhanced_correct_code(code, issues) if language == "python" else code
        
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

@app.route('/api/debug/elevenlabs', methods=['GET'])
def debug_elevenlabs():
    """Debug endpoint to check ElevenLabs API status"""
    if not ELEVENLABS_API_KEY:
        return jsonify({
            "status": "error",
            "message": "ElevenLabs API key not configured"
        }), 400
    
    try:
        # Test the voices endpoint to check API key validity
        headers = {
            "Accept": "application/json",
            "xi-api-key": ELEVENLABS_API_KEY
        }
        
        response = requests.get(
            "https://api.elevenlabs.io/v1/voices",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            voices = response.json()
            return jsonify({
                "status": "success",
                "message": "ElevenLabs API is working correctly",
                "voices_count": len(voices.get('voices', [])),
                "api_key_prefix": ELEVENLABS_API_KEY[:10] + "..." if ELEVENLABS_API_KEY else "None"
            })
        else:
            return jsonify({
                "status": "error",
                "message": f"ElevenLabs API returned status code: {response.status_code}",
                "response_text": response.text[:200] + "..." if len(response.text) > 200 else response.text,
                "api_key_prefix": ELEVENLABS_API_KEY[:10] + "..." if ELEVENLABS_API_KEY else "None"
            }), 400
            
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Exception when calling ElevenLabs API: {str(e)}",
            "api_key_prefix": ELEVENLABS_API_KEY[:10] + "..." if ELEVENLABS_API_KEY else "None"
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy", 
        "model_loaded": True,
        "openai_available": bool(OPENAI_API_KEY),  
        "elevenlabs_available": bool(ELEVENLABS_API_KEY)
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)