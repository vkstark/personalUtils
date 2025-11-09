"""
ChatSystem - GPT-Powered Chat with Function Calling
Integrates all personalUtils as callable tools with agentic capabilities.

Author: Vishal Kumar
License: MIT
"""

__version__ = "1.0.0"

from .core.config import Settings, get_settings
from .core.chat_engine import ChatEngine
from .core.conversation import ConversationManager

__all__ = [
    "Settings",
    "get_settings",
    "ChatEngine",
    "ConversationManager",
]
