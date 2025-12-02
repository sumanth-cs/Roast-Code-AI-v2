import os
from typing import Dict, List, Optional
import requests
from googletrans import Translator

class MultiLanguageSupport:
    """Multi-language support for code analysis and generation"""
    
    def __init__(self):
        self.translator = Translator()
        self.supported_languages = {
            'python': {
                'name': 'Python',
                'ext': '.py',
                'version': '3.9+',
                'keywords': ['def', 'class', 'import', 'from', 'if', 'for', 'while']
            },
            'javascript': {
                'name': 'JavaScript',
                'ext': '.js',
                'version': 'ES6+',
                'keywords': ['function', 'const', 'let', 'var', 'if', 'for', 'while']
            },
            'java': {
                'name': 'Java',
                'ext': '.java',
                'version': '11+',
                'keywords': ['public', 'class', 'void', 'static', 'if', 'for', 'while']
            },
            'cpp': {
                'name': 'C++',
                'ext': '.cpp',
                'version': '17+',
                'keywords': ['int', 'void', 'class', 'if', 'for', 'while']
            },
            'typescript': {
                'name': 'TypeScript',
                'ext': '.ts',
                'version': '4.0+',
                'keywords': ['interface', 'type', 'const', 'let', 'if', 'for', 'while']
            },
            'go': {
                'name': 'Go',
                'ext': '.go',
                'version': '1.19+',
                'keywords': ['func', 'package', 'import', 'if', 'for', 'range']
            },
            'rust': {
                'name': 'Rust',
                'ext': '.rs',
                'version': '2021+',
                'keywords': ['fn', 'let', 'mut', 'if', 'for', 'while']
            },
            'ruby': {
                'name': 'Ruby',
                'ext': '.rb',
                'version': '3.0+',
                'keywords': ['def', 'class', 'module', 'if', 'for', 'while']
            },
            'php': {
                'name': 'PHP',
                'ext': '.php',
                'version': '8.0+',
                'keywords': ['function', 'class', 'if', 'for', 'while']
            },
            'swift': {
                'name': 'Swift',
                'ext': '.swift',
                'version': '5.0+',
                'keywords': ['func', 'class', 'let', 'var', 'if', 'for', 'while']
            },
            'kotlin': {
                'name': 'Kotlin',
                'ext': '.kt',
                'version': '1.7+',
                'keywords': ['fun', 'class', 'val', 'var', 'if', 'for', 'while']
            }
        }
        
        # Code examples for each language
        self.code_examples = self._load_code_examples()
    
    def get_supported_languages(self) -> List[Dict]:
        """Get list of supported programming languages"""
        return [
            {
                'id': lang_id,
                'name': info['name'],
                'ext': info['ext'],
                'version': info['version']
            }
            for lang_id, info in self.supported_languages.items()
        ]
    
    def validate_code_syntax(self, code: str, language: str) -> Dict:
        """Validate code syntax for given language"""
        if language not in self.supported_languages:
            return {
                'valid': False,
                'error': f"Unsupported language: {language}"
            }
        
        # TODO: Implement actual syntax validation for each language
        # This would involve language-specific parsers
        
        return {
            'valid': True,
            'language': language,
            'basic_checks_passed': True
        }
    
    def translate_code_comment(self, comment: str, target_lang: str) -> str:
        """Translate code comment to target language"""
        try:
            translated = self.translator.translate(comment, dest=target_lang)
            return translated.text
        except:
            return comment
    
    def get_language_template(self, language: str, template_type: str = 'basic') -> str:
        """Get code template for a specific language"""
        templates = {
            'python': {
                'basic': """def main():
    \"\"\"Main function\"\"\"
    print("Hello, World!")

if __name__ == "__main__":
    main()""",
                'class': """class MyClass:
    \"\"\"A sample class\"\"\"
    
    def __init__(self, name):
        self.name = name
    
    def greet(self):
        \"\"\"Greet method\"\"\"
        return f"Hello, {self.name}!"

if __name__ == "__main__":
    obj = MyClass("World")
    print(obj.greet())"""
            },
            'javascript': {
                'basic': """function main() {
    // Main function
    console.log("Hello, World!");
}

main();""",
                'class': """class MyClass {
    constructor(name) {
        this.name = name;
    }
    
    greet() {
        return `Hello, ${this.name}!`;
    }
}

const obj = new MyClass("World");
console.log(obj.greet());"""
            },
            'java': {
                'basic': """public class Main {
    public static void main(String[] args) {
        System.out.println("Hello, World!");
    }
}""",
                'class': """public class MyClass {
    private String name;
    
    public MyClass(String name) {
        this.name = name;
    }
    
    public String greet() {
        return "Hello, " + this.name + "!";
    }
    
    public static void main(String[] args) {
        MyClass obj = new MyClass("World");
        System.out.println(obj.greet());
    }
}"""
            }
        }
        
        if language in templates and template_type in templates[language]:
            return templates[language][template_type]
        
        return f"// {language} code template"
    
    def detect_language(self, code: str) -> str:
        """Detect programming language from code"""
        # Simple keyword-based detection
        language_scores = {}
        
        for lang_id, info in self.supported_languages.items():
            score = 0
            for keyword in info['keywords']:
                if keyword in code:
                    score += 1
            
            # Check for language-specific patterns
            if lang_id == 'python':
                if 'def ' in code or 'import ' in code:
                    score += 5
            elif lang_id == 'javascript':
                if 'function ' in code or 'console.log' in code:
                    score += 5
            elif lang_id == 'java':
                if 'public class ' in code or 'System.out.println' in code:
                    score += 5
            
            language_scores[lang_id] = score
        
        if language_scores:
            detected = max(language_scores.items(), key=lambda x: x[1])
            if detected[1] > 0:
                return detected[0]
        
        return 'python'  # Default
    
    def format_code(self, code: str, language: str) -> str:
        """Format code according to language conventions"""
        if language == 'python':
            try:
                import autopep8
                return autopep8.fix_code(code)
            except:
                return code
        elif language == 'javascript':
            # Could use jsbeautifier or prettier if available
            return code
        else:
            return code
    
    def get_code_example(self, language: str, example_type: str = 'hello') -> Optional[str]:
        """Get code example for a language"""
        if language in self.code_examples and example_type in self.code_examples[language]:
            return self.code_examples[language][example_type]
        return None
    
    def _load_code_examples(self) -> Dict:
        """Load code examples for all languages"""
        return {
            'python': {
                'hello': '''print("Hello, World!")''',
                'function': '''def add(a, b):
    """Add two numbers"""
    return a + b

result = add(5, 3)
print(f"Result: {result}")''',
                'class': '''class Calculator:
    """A simple calculator class"""
    
    def __init__(self):
        self.result = 0
    
    def add(self, x):
        """Add to result"""
        self.result += x
        return self.result

calc = Calculator()
print(calc.add(10))'''
            },
            'javascript': {
                'hello': '''console.log("Hello, World!");''',
                'function': '''function add(a, b) {
    // Add two numbers
    return a + b;
}

const result = add(5, 3);
console.log(`Result: ${result}`);''',
                'class': '''class Calculator {
    constructor() {
        this.result = 0;
    }
    
    add(x) {
        // Add to result
        this.result += x;
        return this.result;
    }
}

const calc = new Calculator();
console.log(calc.add(10));'''
            }
        }
    
    def get_language_stats(self) -> Dict:
        """Get statistics about language support"""
        return {
            'total_languages': len(self.supported_languages),
            'languages': list(self.supported_languages.keys()),
            'primary_languages': ['python', 'javascript', 'java', 'cpp'],
            'secondary_languages': ['typescript', 'go', 'rust', 'ruby', 'php', 'swift', 'kotlin']
        }