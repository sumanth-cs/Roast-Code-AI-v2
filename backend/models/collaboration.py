from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, field
import uuid

@dataclass
class Participant:
    """Collaboration session participant"""
    user_id: str
    username: str
    role: str = "participant"
    joined_at: datetime = field(default_factory=datetime.utcnow)
    cursor_position: Optional[Dict] = None
    last_active: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict:
        return {
            'user_id': self.user_id,
            'username': self.username,
            'role': self.role,
            'joined_at': self.joined_at.isoformat(),
            'last_active': self.last_active.isoformat(),
            'cursor_position': self.cursor_position
        }

@dataclass
class ChatMessage:
    """Chat message in collaboration session"""
    id: str
    user_id: str
    username: str
    message: str
    timestamp: datetime
    message_type: str = "chat"  # chat, system, code_suggestion
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': self.username,
            'message': self.message,
            'timestamp': self.timestamp.isoformat(),
            'type': self.message_type
        }

class CollaborationSession:
    """Real-time collaboration session"""
    
    def __init__(self, session_id: str, name: str, creator_id: str, language: str = "python"):
        self.session_id = session_id
        self.name = name
        self.creator_id = creator_id
        self.language = language
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        
        self.participants: Dict[str, Participant] = {}
        self.chat_messages: List[ChatMessage] = []
        self.code = ""
        self.code_history: List[Dict] = []
        self.settings = {
            'read_only': False,
            'allow_guests': True,
            'max_participants': 10,
            'auto_save': True
        }
    
    def add_participant(self, user_id: str, username: str, role: str = "participant") -> bool:
        """Add participant to session"""
        if len(self.participants) >= self.settings['max_participants']:
            return False
        
        if user_id not in self.participants:
            self.participants[user_id] = Participant(
                user_id=user_id,
                username=username,
                role=role
            )
            self.updated_at = datetime.utcnow()
            return True
        return False
    
    def remove_participant(self, user_id: str) -> bool:
        """Remove participant from session"""
        if user_id in self.participants:
            del self.participants[user_id]
            self.updated_at = datetime.utcnow()
            return True
        return False
    
    def update_code(self, code: str, user_id: Optional[str] = None) -> None:
        """Update session code"""
        self.code = code
        self.updated_at = datetime.utcnow()
        
        # Save to history (limited to last 100 changes)
        change_entry = {
            'timestamp': datetime.utcnow(),
            'user_id': user_id,
            'code': code,
            'change_size': len(code) - len(self.code_history[-1]['code'] if self.code_history else 0)
        }
        
        self.code_history.append(change_entry)
        if len(self.code_history) > 100:
            self.code_history = self.code_history[-100:]
    
    def update_cursor_position(self, user_id: str, position: Dict) -> None:
        """Update user's cursor position"""
        if user_id in self.participants:
            self.participants[user_id].cursor_position = position
            self.participants[user_id].last_active = datetime.utcnow()
    
    def add_chat_message(self, message_data: Dict) -> None:
        """Add chat message to session"""
        message = ChatMessage(
            id=str(uuid.uuid4()),
            user_id=message_data['user_id'],
            username=message_data['username'],
            message=message_data['message'],
            timestamp=datetime.utcnow()
        )
        
        self.chat_messages.append(message)
        
        # Keep only last 100 messages
        if len(self.chat_messages) > 100:
            self.chat_messages = self.chat_messages[-100:]
    
    def get_participant_list(self) -> List[Dict]:
        """Get list of participants"""
        return [p.to_dict() for p in self.participants.values()]
    
    def get_recent_chat(self, limit: int = 50) -> List[Dict]:
        """Get recent chat messages"""
        return [msg.to_dict() for msg in self.chat_messages[-limit:]]
    
    def get_code_history_slice(self, start: int = -10, end: int = None) -> List[Dict]:
        """Get slice of code history"""
        history_slice = self.code_history[start:end]
        return [
            {
                'timestamp': entry['timestamp'].isoformat(),
                'user_id': entry['user_id'],
                'change_size': entry['change_size']
            }
            for entry in history_slice
        ]
    
    def analyze_session_activity(self) -> Dict:
        """Analyze session activity metrics"""
        active_participants = [
            p for p in self.participants.values()
            if (datetime.utcnow() - p.last_active).seconds < 300  # Active in last 5 minutes
        ]
        
        return {
            'total_participants': len(self.participants),
            'active_participants': len(active_participants),
            'total_chat_messages': len(self.chat_messages),
            'code_changes': len(self.code_history),
            'session_duration': (datetime.utcnow() - self.created_at).seconds,
            'last_activity': self.updated_at.isoformat()
        }
    
    def to_dict(self) -> Dict:
        """Convert session to dictionary"""
        return {
            'session_id': self.session_id,
            'name': self.name,
            'creator_id': self.creator_id,
            'language': self.language,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'participants': self.get_participant_list(),
            'participant_count': len(self.participants),
            'settings': self.settings,
            'code_length': len(self.code),
            'activity': self.analyze_session_activity()
        }