import asyncio
import json
import os
import uuid
from datetime import datetime
from typing import List, Dict, Optional

import redis
from flask import Flask, request, jsonify, session
from flask_cors import CORS
from flask_socketio import SocketIO, join_room, leave_room, emit
from werkzeug.security import generate_password_hash, check_password_hash

from services.code_quality import CodeQualityAnalyzer
from services.llm_service import LLMService
from services.multilingual import MultiLanguageSupport
from services.tts_service import TTSService
from utils.cache import CacheManager
from models.collaboration import CollaborationSession

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['REDIS_URL'] = os.getenv('REDIS_URL', 'redis://localhost:6379')

# Enable CORS
CORS(app, supports_credentials=True, origins=os.getenv('ALLOWED_ORIGINS', '*').split(','))

# Initialize SocketIO for real-time collaboration
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Initialize services
redis_client = redis.from_url(app.config['REDIS_URL'])
cache_manager = CacheManager(redis_client)
code_analyzer = CodeQualityAnalyzer()
llm_service = LLMService()
multilingual = MultiLanguageSupport()
tts_service = TTSService()

# Store active collaboration sessions
active_sessions: Dict[str, CollaborationSession] = {}

@app.route('/api/analyze', methods=['POST'])
async def analyze_code():
    """Analyze code with multi-language support"""
    try:
        data = request.json
        code = data.get('code', '')
        language = data.get('language', 'python')
        roast_level = data.get('roast_level', 'medium')
        user_id = data.get('user_id', str(uuid.uuid4()))
        
        if not code:
            return jsonify({"error": "No code provided"}), 400
        
        # Check cache first
        cache_key = f"analysis:{hash(code)}:{language}:{roast_level}"
        cached_result = cache_manager.get(cache_key)
        if cached_result:
            return jsonify(cached_result)
        
        # Analyze code based on language
        if language == 'python':
            analysis = code_analyzer.analyze_python(code)
        elif language == 'javascript':
            analysis = code_analyzer.analyze_javascript(code)
        elif language == 'java':
            analysis = code_analyzer.analyze_java(code)
        elif language == 'cpp':
            analysis = code_analyzer.analyze_cpp(code)
        else:
            analysis = code_analyzer.analyze_generic(code, language)
        
        # Generate roast with AI
        roast = await llm_service.generate_roast(
            code=code,
            issues=analysis['issues'],
            language=language,
            intensity=roast_level
        )
        
        # Generate suggestions for improvement
        suggestions = await llm_service.generate_suggestions(
            code=code,
            issues=analysis['issues'],
            language=language
        )
        
        # Generate audio roast
        audio_data = await tts_service.generate_audio_roast(
            roast_text=roast['text'],
            intensity=roast_level,
            language=language
        )
        
        # Generate corrected code
        corrected_code = await llm_service.correct_code(
            code=code,
            issues=analysis['issues'],
            language=language
        )
        
        # Calculate comprehensive metrics
        metrics = code_analyzer.calculate_comprehensive_metrics(
            code=code,
            analysis=analysis,
            language=language
        )
        
        # Prepare response
        result = {
            "success": True,
            "analysis": analysis,
            "roast": roast,
            "suggestions": suggestions,
            "corrected_code": corrected_code,
            "metrics": metrics,
            "audio": audio_data,
            "language": language,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Cache the result
        cache_manager.set(cache_key, result, ttl=3600)
        
        # Track user analytics
        track_analysis_metrics(user_id, language, metrics)
        
        return jsonify(result)
        
    except Exception as e:
        app.logger.error(f"Analysis error: {str(e)}")
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500

@app.route('/api/generate', methods=['POST'])
async def generate_code():
    """Generate code based on prompt with multi-language support"""
    try:
        data = request.json
        prompt = data.get('prompt', '')
        language = data.get('language', 'python')
        complexity = data.get('complexity', 'medium')
        user_id = data.get('user_id', str(uuid.uuid4()))
        
        if not prompt:
            return jsonify({"error": "No prompt provided"}), 400
        
        # Generate code using LLM
        generated_code = await llm_service.generate_code_from_prompt(
            prompt=prompt,
            language=language,
            complexity=complexity
        )
        
        # Analyze the generated code
        analysis = code_analyzer.analyze_code(generated_code, language)
        
        # Generate a roast for the generated code
        roast = await llm_service.generate_roast(
            code=generated_code,
            issues=analysis['issues'],
            language=language,
            intensity='medium'
        )
        
        # Generate audio
        audio_data = await tts_service.generate_audio_roast(
            roast_text=roast['text'],
            intensity='medium',
            language=language
        )
        
        result = {
            "success": True,
            "code": generated_code,
            "analysis": analysis,
            "roast": roast,
            "audio": audio_data,
            "language": language,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Track generation metrics
        track_generation_metrics(user_id, language, len(generated_code))
        
        return jsonify(result)
        
    except Exception as e:
        app.logger.error(f"Generation error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/languages', methods=['GET'])
def get_supported_languages():
    """Get list of supported programming languages"""
    languages = multilingual.get_supported_languages()
    return jsonify({
        "success": True,
        "languages": languages,
        "count": len(languages)
    })

@app.route('/api/metrics/history', methods=['GET'])
def get_user_metrics_history():
    """Get user's analysis history and metrics"""
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({"error": "User ID required"}), 400
    
    history = get_user_history(user_id)
    metrics = calculate_user_metrics(user_id)
    
    return jsonify({
        "success": True,
        "history": history,
        "metrics": metrics
    })

@app.route('/api/collaboration/create', methods=['POST'])
def create_collaboration_session():
    """Create a new collaboration session"""
    data = request.json
    session_name = data.get('name', f"Session-{datetime.now().strftime('%Y%m%d-%H%M%S')}")
    language = data.get('language', 'python')
    user_id = data.get('user_id')
    
    if not user_id:
        return jsonify({"error": "User ID required"}), 400
    
    session_id = str(uuid.uuid4())
    collaboration_session = CollaborationSession(
        session_id=session_id,
        name=session_name,
        creator_id=user_id,
        language=language
    )
    
    active_sessions[session_id] = collaboration_session
    collaboration_session.add_participant(user_id, "host")
    
    return jsonify({
        "success": True,
        "session_id": session_id,
        "session": collaboration_session.to_dict()
    })

@app.route('/api/collaboration/<session_id>/join', methods=['POST'])
def join_collaboration_session(session_id):
    """Join an existing collaboration session"""
    data = request.json
    user_id = data.get('user_id')
    username = data.get('username', f"User-{user_id[:8]}")
    
    if session_id not in active_sessions:
        return jsonify({"error": "Session not found"}), 404
    
    session = active_sessions[session_id]
    session.add_participant(user_id, username)
    
    return jsonify({
        "success": True,
        "session": session.to_dict()
    })

# WebSocket event handlers
@socketio.on('join_session')
def handle_join_session(data):
    """Handle client joining a collaboration session"""
    session_id = data.get('session_id')
    user_id = data.get('user_id')
    username = data.get('username')
    
    if session_id in active_sessions:
        join_room(session_id)
        session = active_sessions[session_id]
        session.add_participant(user_id, username)
        
        emit('user_joined', {
            'user_id': user_id,
            'username': username,
            'participants': session.participants,
            'timestamp': datetime.utcnow().isoformat()
        }, room=session_id)
        
        emit('session_update', session.to_dict(), room=session_id)

@socketio.on('code_update')
def handle_code_update(data):
    """Handle real-time code updates"""
    session_id = data.get('session_id')
    user_id = data.get('user_id')
    code = data.get('code')
    cursor_position = data.get('cursor_position')
    
    if session_id in active_sessions:
        session = active_sessions[session_id]
        session.update_code(code)
        session.update_cursor_position(user_id, cursor_position)
        
        emit('code_updated', {
            'user_id': user_id,
            'code': code,
            'cursor_position': cursor_position,
            'timestamp': datetime.utcnow().isoformat()
        }, room=session_id, include_self=False)

@socketio.on('leave_session')
def handle_leave_session(data):
    """Handle client leaving a collaboration session"""
    session_id = data.get('session_id')
    user_id = data.get('user_id')
    
    if session_id in active_sessions:
        leave_room(session_id)
        session = active_sessions[session_id]
        session.remove_participant(user_id)
        
        emit('user_left', {
            'user_id': user_id,
            'participants': session.participants,
            'timestamp': datetime.utcnow().isoformat()
        }, room=session_id)
        
        # If no participants left, clean up session
        if not session.participants:
            del active_sessions[session_id]

@socketio.on('chat_message')
def handle_chat_message(data):
    """Handle chat messages in collaboration session"""
    session_id = data.get('session_id')
    user_id = data.get('user_id')
    message = data.get('message')
    
    if session_id in active_sessions:
        session = active_sessions[session_id]
        chat_message = {
            'user_id': user_id,
            'username': session.participants.get(user_id, {}).get('username'),
            'message': message,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        session.add_chat_message(chat_message)
        
        emit('new_chat_message', chat_message, room=session_id)

# Utility functions
def track_analysis_metrics(user_id, language, metrics):
    """Track analysis metrics for user analytics"""
    key = f"user:{user_id}:analytics"
    redis_client.hincrby(key, f"total_analysis_{language}", 1)
    redis_client.hincrby(key, "total_analysis", 1)
    
    # Store metrics history
    history_key = f"user:{user_id}:analysis_history"
    history_entry = {
        'timestamp': datetime.utcnow().isoformat(),
        'language': language,
        'metrics': metrics
    }
    redis_client.lpush(history_key, json.dumps(history_entry))
    redis_client.ltrim(history_key, 0, 99)  # Keep last 100 entries

def track_generation_metrics(user_id, language, code_length):
    """Track code generation metrics"""
    key = f"user:{user_id}:analytics"
    redis_client.hincrby(key, f"generations_{language}", 1)
    redis_client.hincrby(key, "total_generations", 1)
    redis_client.hincrby(key, "total_code_generated", code_length)

def get_user_history(user_id):
    """Get user's analysis history"""
    history_key = f"user:{user_id}:analysis_history"
    history = redis_client.lrange(history_key, 0, 49)  # Last 50 entries
    return [json.loads(entry) for entry in history]

def calculate_user_metrics(user_id):
    """Calculate comprehensive user metrics"""
    key = f"user:{user_id}:analytics"
    analytics = redis_client.hgetall(key)
    
    return {
        'total_analysis': int(analytics.get(b'total_analysis', 0)),
        'total_generations': int(analytics.get(b'total_generations', 0)),
        'total_code_generated': int(analytics.get(b'total_code_generated', 0)),
        'languages_used': {
            lang.decode().replace('total_analysis_', ''): int(count)
            for lang, count in analytics.items()
            if lang.startswith(b'total_analysis_')
        }
    }

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "redis": redis_client.ping(),
            "llm": llm_service.is_available(),
            "tts": tts_service.is_available()
        },
        "active_sessions": len(active_sessions)
    })

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5001))
    socketio.run(app, host='0.0.0.0', port=port, debug=os.getenv('FLASK_DEBUG', 'False') == 'True')