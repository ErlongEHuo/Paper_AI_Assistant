from pathlib import Path
from typing import Dict, Any
import os
from dotenv import load_dotenv 

# 加载 .env 文件
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)
 

class Settings:
    """配置管理类"""
    
    def __init__(self):
        # 使用绝对路径处理，避免相对路径问题
        self.BASE_DIR = Path(__file__).parent.parent.absolute()
        self.UPLOAD_DIR = self.BASE_DIR / "database/download"  # 上传文件路径
        # self.STATIC_DIR = self.BASE_DIR / "static"   # 静态文件路径
        # self.TEMPLATES_DIR = self.BASE_DIR / "templates"  # 模板文件路径
        
        # 服务器配置
        self.HOST = "127.0.0.1"
        self.PORT = 9657
        
        # 文件上传配置
        self.MAX_FILE_SIZE = 100 * 1024 * 1024   # 100MB # 最大文件大小
        # 允许哪些文件上传
        self.ALLOWED_FILE_TYPES = [
            "image/jpeg", "image/png", "image/gif",
            "application/pdf", "text/plain", "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ]

        # 向量数据库配置
        self.CHROMADB_DIR = self.BASE_DIR / "database/.chroma_db"  # Chroma 向量数据库存储目录
        # 向量数据库集合名称
        self.CHROMADB_COLLECTION_NAME = "ollama_embeddings_test"

        # redis配置
        self.redis_config = {
                                        'host': 'localhost',
                                        'port': 6380,
                                        'db': 0
                                        } 
        self.redis_url = 'redis://:@localhost:6380'


        # 对话LLM模型配置
        self.CHAT_LLM_MODEL = "deepseek-chat"
        self.THINKING_LLM_MODEL = "deepseek-reasoner"

        # 向量化LLM模型配置
        self.EMBEDDINGS_LLM_MODEL = "text-embedding-v4"


        
        # 创建必要的目录
        self._create_directories()
    
    def _create_directories(self):
        """创建必要的目录"""
        self.UPLOAD_DIR.mkdir(exist_ok=True) 
    
    def get_server_config(self) -> Dict[str, Any]:
        """获取服务器配置"""
        return {
            "host": self.HOST,
            "port": self.PORT
        }
     

# 全局配置实例
settings = Settings()





""" 模型配置类 """
class OllamaChatLLMConfig: 
    """ Ollama Chat LLM 配置 """ 
    def __init__(self): 
        self.chatModel="gemma3:4b" 
        # self.chatModel="qwen3-vl:8b" 
        # self.chatModel="deepseek-r1:7b" 
        self.embeddingsModel="bge-m3:latest"
        self.temperature = 0

    




# 全局配置实例
ollamaLLMConfig = OllamaChatLLMConfig()