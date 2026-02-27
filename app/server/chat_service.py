from app.models.chat import ChatInstanceManager
from app.server.ai_service import AIService

# 创建全局服务实例，使用持久化存储
chat_manager = ChatInstanceManager("data")
ai_service = AIService()

# 注意：不再需要手动创建默认实例，ChatInstanceManager会自动处理