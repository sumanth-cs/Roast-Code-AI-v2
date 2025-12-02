import os
import json
from typing import Dict, List, Optional, Any
import openai
from openai import OpenAI
from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
import google.generativeai as genai

class LLMService:
    """Service for interacting with various LLMs"""
    
    def __init__(self):
        # Initialize OpenAI
        self.openai_client = OpenAI(
            api_key=os.getenv('OPENAI_API_KEY'),
            timeout=30.0
        )
        
        # Initialize Google Gemini
        genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
        self.gemini_model = genai.GenerativeModel('gemini-pro')
        
        # Load local models
        self.local_model = None
        self.local_tokenizer = None
        self._load_local_models()
        
        # Load roast templates
        with open('ml_models/roast_templates.json', 'r') as f:
            self.roast_templates = json.load(f)
    
    async def generate_roast(self, code: str, issues: List[str], language: str, intensity: str = 'medium') -> Dict:
        """Generate roast for code"""
        try:
            # Use OpenAI for better quality roasts
            prompt = self._create_roast_prompt(code, issues, language, intensity)
            
            response = await self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a sarcastic code reviewer. Provide humorous but helpful feedback."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7 + (0.1 if intensity == 'brutal' else 0),
                max_tokens=500
            )
            
            roast_text = response.choices[0].message.content
            
            return {
                'text': roast_text,
                'intensity': intensity,
                'language': language,
                'model': 'gpt-4'
            }
            
        except Exception as e:
            # Fallback to template-based roasting
            return self._generate_template_roast(issues, intensity)
    
    async def generate_suggestions(self, code: str, issues: List[str], language: str) -> List[str]:
        """Generate improvement suggestions"""
        try:
            prompt = f"""Given this {language} code and these issues, provide 3 specific suggestions for improvement:

Code:

Issues:
{chr(10).join(issues)}

Provide suggestions in the format:
1. Suggestion one
2. Suggestion two
3. Suggestion three"""

            response = await self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a helpful code reviewer providing constructive suggestions."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=300
            )
            
            suggestions = response.choices[0].message.content.strip().split('\n')
            return [s.strip() for s in suggestions if s.strip()]
            
        except:
            return ["Run static analysis tools", "Add documentation", "Refactor complex functions"]
    
    async def correct_code(self, code: str, issues: List[str], language: str) -> str:
        """Generate corrected version of code"""
        try:
            prompt = f"""Correct this {language} code by fixing the following issues:

Issues to fix:
{chr(10).join(issues[:5])}

Original code:

Provide only the corrected code without any explanations:"""

            response = await self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a code correction assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=1000
            )
            
            corrected = response.choices[0].message.content.strip()
            
            # Extract code from markdown if present
            if '```' in corrected:
                corrected = corrected.split('```')[1].split('```')[0].strip()
                if corrected.startswith(language):
                    corrected = corrected[len(language):].strip()
            
            return corrected
            
        except Exception as e:
            return code
    
    async def generate_code_from_prompt(self, prompt: str, language: str = 'python', complexity: str = 'medium') -> str:
        """Generate code from natural language prompt"""
        try:
            system_prompt = f"You are a {language} programming expert. Generate clean, efficient code."
            
            user_prompt = f"""Generate {language} code for: {prompt}

Requirements:
- Use proper {language} syntax and conventions
- Include appropriate comments
- Make the code {complexity} complexity level
- Return only the code without explanations"""

            response = await self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            generated_code = response.choices[0].message.content.strip()
            
            # Extract code from markdown if present
            if '```' in generated_code:
                generated_code = generated_code.split('```')[1].split('```')[0].strip()
                if generated_code.startswith(language):
                    generated_code = generated_code[len(language):].strip()
            
            return generated_code
            
        except Exception as e:
            # Fallback to local model
            return self._generate_with_local_model(prompt, language)
    
    def _create_roast_prompt(self, code: str, issues: List[str], language: str, intensity: str) -> str:
        """Create prompt for roast generation"""
        intensity_map = {
            'mild': 'gentle and constructive',
            'medium': 'sarcastic but helpful',
            'brutal': 'very sarcastic and brutally honest'
        }
        
        return f"""As a {intensity_map.get(intensity, 'sarcastic')} code reviewer, provide feedback on this {language} code.

Code:

Issues found:
{chr(10).join(issues[:5]) if issues else 'No major issues found'}

Provide your feedback in a humorous, roast-style format. Keep it under 3 sentences:"""
    
    def _generate_template_roast(self, issues: List[str], intensity: str) -> Dict:
        """Generate roast from templates"""
        import random
        
        if not issues:
            templates = self.roast_templates['general'].get(intensity, [])
            if templates:
                roast_text = random.choice(templates)
            else:
                roast_text = "Your code is surprisingly decent. I'm almost disappointed."
        else:
            # Pick a random issue category
            categories = list(self.roast_templates.keys())
            category = random.choice(categories)
            
            if intensity in self.roast_templates[category]:
                templates = self.roast_templates[category][intensity]
                if templates:
                    template = random.choice(templates)
                    # Format with placeholders
                    roast_text = template.format(
                        name="this code",
                        depth="several",
                        score="high",
                        issue=issues[0] if issues else "something"
                    )
                else:
                    roast_text = f"Found {len(issues)} issues in your code."
            else:
                roast_text = f"Found {len(issues)} issues that need fixing."
        
        return {
            'text': roast_text,
            'intensity': intensity,
            'language': 'template',
            'model': 'template-based'
        }
    
    def _generate_with_local_model(self, prompt: str, language: str) -> str:
        """Generate code using local model"""
        if self.local_model and self.local_tokenizer:
            try:
                generator = pipeline('text-generation', model=self.local_model, tokenizer=self.local_tokenizer)
                result = generator(prompt, max_length=200, num_return_sequences=1)
                return result[0]['generated_text']
            except:
                pass
        
        # Fallback to simple examples
        examples = {
            'python': '''def solution():
    # Implement your solution here
    pass

if __name__ == "__main__":
    solution()''',
            'javascript': '''function solution() {
    // Implement your solution here
}

solution();''',
            'java': '''public class Solution {
    public static void main(String[] args) {
        // Implement your solution here
    }
}'''
        }
        
        return examples.get(language, examples['python'])
    
    def _load_local_models(self):
        """Load local models for fallback"""
        try:
            model_path = "ml_models/fine_tuned_distilgpt2"
            if os.path.exists(model_path):
                self.local_tokenizer = AutoTokenizer.from_pretrained(model_path)
                self.local_model = AutoModelForCausalLM.from_pretrained(model_path)
        except:
            pass
    
    def is_available(self) -> bool:
        """Check if LLM services are available"""
        return (
            bool(os.getenv('OPENAI_API_KEY')) or 
            bool(os.getenv('GEMINI_API_KEY')) or 
            self.local_model is not None
        )