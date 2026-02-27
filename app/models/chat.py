from gettext import install
import json
import os
from datetime import datetime
import uuid
from typing import Dict, List, Optional
from pathlib import Path

# from langchain_classic.memory import RedisChatMessageHistory
from langchain_community.chat_message_histories import RedisChatMessageHistory 
import redis

# str转换为dict 
import ast

# redis    
from app.server.redis_service import redis_service , chat_message_history
from config.settings import settings
  

from langchain_core.messages import BaseMessage



# ======================================================== 聊天消息类 ========================================================

class ChatMessage:
    """聊天消息类"""
    
    def __init__(self,  user_message: str, ai_response: str, message_type: str = "text", 
                 file_info: Optional[Dict] = None, message_id: Optional[str] = None ):
        # 用户id
        self.id = message_id or str(uuid.uuid4())
        # 用户发送的消息
        self.user_message = user_message
        # ai回复的消息
        self.ai_response = ai_response
        # 时间
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # 消息类型
        self.type = message_type
        # 文件信息
        self.file_info = file_info or {}
    
    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            "id": self.id,
            "user": self.user_message,
            "ai": self.ai_response,
            "timestamp": self.timestamp,
            "type": self.type,
            "file_info": self.file_info
        }

class ChatFile:
    """聊天文件类"""
    
    def __init__(self, filename: str, saved_name: str, size: int, content_type: str):
        self.id = str(uuid.uuid4())
        self.filename = filename
        self.saved_name = saved_name
        self.upload_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.size = size
        self.type = content_type
    
    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            "id": self.id,
            "filename": self.filename,
            "saved_name": self.saved_name,
            "upload_time": self.upload_time,
            "size": self.size,
            "type": self.type
        }


# ======================================================== 聊天实例类 ========================================================
class ChatInstance:
    """聊天实例类"""
    
    def __init__(self, instance_id: Optional[str] = None ,instance_name: str = "新聊天"):
        self.id = instance_id or str(uuid.uuid4())
        self.name = instance_name
        self.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # self.messages: List[ChatMessage] = []
        self.messages: List[BaseMessage] = []
        self.files: List[ChatFile] = []

    # 获取聊天消息
    def get_message(self,instance):

        return ''
    
    # 添加聊天消息
    def add_message(self, instance ,user_message: str, ai_response: str, message_type: str = "text", message_time:str=None,
                   file_info: Optional[Dict] = None) :
        """
        将用户消息和ai回复添加到聊天实例的历史消息中
            参数：
            - instance: 聊天实例对象
            - user_message: 用户发送的消息
            - ai_response: AI的回复消息
            - message_type: 消息类型，默认为"text"
            - message_time: 消息时间，默认为当前时间
            - file_info: 文件信息，默认为None
        """ 
        # print('开始添消息')
        id = instance.id
        # print(f'id:{id}')
        # 创建redis历史消息服务
        chat_message_history_client = chat_message_history.get_chat_message_history_client(id)
        # print(f'准备添加',chatmessagehistory)
        # 进行添加对话
        chat_message_history.add_user_ai_message(
                                                 chat_message_history_client,
                                                 user_message,
                                                 ai_response,
                                                 message_type,
                                                 message_time
                                                 )
        
        mes = chat_message_history_client.messages
        # print(f'app/models/chat.py: add_message1: 添加消息完成:',mes,'\n\n\n\n\n======================\n\n\n')
        self.messages.append(mes) 
        # print(f'app/models/chat.py: add_message2: 添加消息完成:{self.messages}')
        return mes

    # # 添加聊天消息
    # def add_message(self, user_message: str, ai_response: str, message_type: str = "text", 
    #                file_info: Optional[Dict] = None) -> ChatMessage:
    #     """添加聊天消息"""
    #     message = ChatMessage(user_message, ai_response, message_type, file_info)
    #     self.messages.append(message)
    #     return message
    
    
    # 添加聊天文件
    def add_file(self, filename: str, saved_name: str, size: int, content_type: str) -> ChatFile:
        """添加文件"""
        file = ChatFile(filename, saved_name, size, content_type)
        self.files.append(file)
        return file
    
    # 根据ID获取聊天文件
    def get_file_by_id(self, file_id: str) -> Optional[ChatFile]:
        """根据ID获取文件"""
        for file in self.files:
            if file.id == file_id:
                return file
        return None
    
    # 删除聊天文件
    def remove_file(self, file_id: str) -> bool:
        """删除文件"""
        file_to_remove = self.get_file_by_id(file_id)
        if file_to_remove:
            self.files = [f for f in self.files if f.id != file_id]
            return True
        return False
    
    # 转换为字典格式
    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at,
            "messages": [msg.to_dict() for msg in self.messages],
            "files": [file.to_dict() for file in self.files]
        }

    # 封装为对象
    def to_class(id,name=None,created_at=None,messages=None,files=None):
        ci = ChatInstance(id,name)
        ci.created_at= created_at
        ci.messages= messages
        ci.files = files
        


# ======================================================== 聊天实例管理器 ========================================================

class ChatInstanceManager:
    """聊天实例管理器"""
    
    def __init__(self, data_dir: str = "redis_data"):
        # 存储所有聊天实例的字典，键为实例ID，值为ChatInstance对象
        self.instances: Dict[str, ChatInstance] = {} 
        # self.data_dir = Path(data_dir)
        # self.data_file = self.data_dir / "chat_instances.json"
        
        # 确保数据目录存在
        # self.data_dir.mkdir(exist_ok=True)
        
        # 启动时加载持久化数据
        self.load_instances()
        
        # 如果没有实例，创建一个默认实例
        if not self.instances:
            self.create_instance("默认聊天")
    

    # 创建一个聊天实例
    def create_instance(self, instance_name: str = "新聊天") -> ChatInstance:
        """创建新的聊天实例\n
            instance_name : 聊天实例名称
        return : 新的聊天实例对象ChatInstance
        """ 
        instance: ChatInstance = ChatInstance(instance_name=instance_name)  
        # 保存到文件 进行持久化存储
        self.save_instances(instance)
        # 存储到实例字典中
        self.instances[instance.id] = instance
        return instance
     
    
    # 获取一个聊天实例
    def get_instance(self, instance_id: str) -> Optional[ChatInstance]:
        """根据ID获取聊天实例""" 
        try:
            instance_json = ast.literal_eval(redis_service.get_instance(instance_id).decode('utf-8')) 
            
            chatinstance = ChatInstance(
                        instance_json.get('id'),
                        instance_json.get('name')
                        )
            chatinstance.created_at = instance_json.get("created_at")
            # 存储到实例字典中 
            self.instances[instance_json.get('id')] = chatinstance 
            return chatinstance  
        except Exception as e:  
            print('获取id聊天实例异常')

 

    # 获取所有聊天实例
    def get_all_instances(self) -> List[Dict]:
        """
        获取所有聊天实例的字典形式\n
        return : 所有聊天实例的字典列表
        """  
        #从redis中获取所有实例
        instances = redis_service.get_all_instances()
        # print('获取所有实例：',instances) 
        instances_list = []
        for i in instances:
            instances_list.append(i) 
        return instances_list


    
    # 删除一个聊天实例
    def delete_instance(self, instance_id: str) -> bool:
        """删除聊天实例"""
        instance = ast.literal_eval(redis_service.get_instance(instance_id).decode('utf-8'))
        if instance and len(instance) > 1:
            redis_service.remove_instance(instance_id)  
            # 删除实例字典中
            del self.instances[instance_id]
            return True
        return False 

    # 重命名一个聊天实例
    def rename_instance(self, instance_id: str, new_name: str) -> bool:
        """重命名聊天实例"""
        instance = ast.literal_eval(redis_service.get_instance(instance_id).decode('utf-8'))

        if instance and len(instance) > 1:
            redis_service.rename_instance(instance_id, new_name)
            instance_new =ast.literal_eval(redis_service.get_instance(new_name).decode('utf-8'))
            # 删除实例字典中
            del self.instances[instance_id]
            # 新增实例字典中
            self.instances[new_name] = instance_new
            return True
        return False 



    
    # 保存实例数据到文件里进行持久化
    def save_instances(self, instance: ChatInstance) -> None:
        """保存聊天实例数据到Redis"""
        try:     
            instance_dict = instance.to_dict()  
            # 存储到redis中，使用json字符串格式
            import json
            redis_service.add_instance(instance.id , json.dumps(instance_dict)) 
            print(f"chat/save_instances 成功保存实例 {instance.id} 到Redis")
        except Exception as e:  
            print(f"chat/save_instances 保存实例数据到redis失败: {e}")
 
 

 
    def load_instances(self) -> None:
        """
        从redis中初始化所有聊天实例数据，将所有实例数据加载到全局chat_service.py/chat_manager对象中\n
        return : None 
        """
        
        try:
            # 获取所有实例ID
            instances_list =redis_service.get_all_instances_list()

            # print(f'redis获取所有实例{instances_list}')

            # 清空当前实例
            self.instances.clear()

            # 从redis中解析实例对象
            for instance_id in instances_list:
                instance_id = instance_id
                # 通过用户id创建一个聊天实例类对象
                instance = ChatInstance(instance_id)   
                # 从redis中获取该实例数据
                instance_str = redis_service.get_instance(instance_id)
                
                # 判断该实例是否存在
                if instance_str:
                    try:
                        # 尝试使用JSON解析
                        import json
                        redis_instance_data = json.loads(instance_str)
                        # print('app/models/chat.py/load_instances: 使用JSON进行解析实例数据',redis_instance_data)
                    except json.JSONDecodeError:
                        # 如果JSON解析失败，尝试使用ast.literal_eval
                        redis_instance_data = ast.literal_eval(instance_str)
                        # print('chat/models/chat.py/load_instances: 使用ast.literal_eval进行解析实例数据',redis_instance_data)
                else:
                    # 如果redis中不存在该实例数据，则返回None
                    redis_instance_data = None
  
                #判断解析出来的实例数据是否为空
                if redis_instance_data:
                    try:
                        # 将解析的实例数据赋值给 ChatInstance 对象
                        instance_dict = redis_instance_data 
                        instance.name = instance_dict.get('name', instance.name)
                        instance.created_at = instance_dict.get('created_at', instance.created_at)
                        instance.messages = instance_dict.get('message',instance.messages)
                        instance.files = instance_dict.get('fiels',instance.files) 
                    except (ValueError, SyntaxError) as e:
                        print(f'解析实例数据失败: {e}')
 
                # 从Redis恢复历史消息客户端 
                chat_message_history_client: RedisChatMessageHistory = chat_message_history.get_chat_message_history_client(str(instance_id))
                # 通过历史消息客户端获取历史消息
                mess = chat_message_history_client.messages 
                #将实例对象中添加历史消息
                instance.messages.append(mess)


                # 将历史消息转换为ChatMessage对象
                # for msg in chat_message_history.messages:
                #     if msg.type == 'human':
                #         # 找到配对的AI消息
                #         ai_msg = None
                #         for next_msg in chat_message_history.messages:
                #             if next_msg.type == 'ai' and next_msg.id > msg.id:
                #                 ai_msg = next_msg
                #                 break

                #         chat_message = ChatMessage(
                #             user_message=msg.content,
                #             ai_response=ai_msg.content if ai_msg else '',
                #             message_type='text'
                #         )
                #         instance.messages.append(chat_message)

                # # 恢复文件
                # for file_data in instance_data.get("files", []):
                #     file = ChatFile(
                #         file_data["filename"],
                #         file_data["saved_name"],
                #         file_data["size"],
                #         file_data["type"]
                #     )
                #     file.id = file_data["id"]
                #     file.upload_time = file_data["upload_time"]
                #     instance.files.append(file) 
                #将实例对象添加到实例字典中
                self.instances[instance.id] = instance
            # 循环完所有的实例后进行打印 个数
            print(f"成功加载 {len(self.instances)} 个聊天实例")     
        except Exception as e:
            print(f"chat.py/load_instances 加载实例数据失败: {e}")
            # 如果加载失败，创建空实例字典
            self.instances = {}


    # # 从文件加载实例数据
    # def load_instances(self) -> None:
    #     """从文件加载实例数据"""
    #     try:
    #         if self.data_file.exists():
    #             with open(self.data_file, 'r', encoding='utf-8') as f:
    #                 data = json.load(f)
                
    #             # 清空当前实例
    #             self.instances.clear()
                
    #             # 重新创建实例对象
    #             for instance_data in data.get("instances", []):
    #                 instance = ChatInstance(instance_data["name"])
    #                 # 使用保存的ID而不是生成新的
    #                 instance.id = instance_data["id"]
    #                 instance.created_at = instance_data["created_at"]
                    
    #                 # 恢复消息
    #                 for msg_data in instance_data.get("messages", []):
    #                     message = ChatMessage(
    #                         msg_data["user"], 
    #                         msg_data["ai"], 
    #                         msg_data.get("type", "text"),
    #                         msg_data.get("file_info")
    #                     )
    #                     message.id = msg_data["id"]
    #                     message.timestamp = msg_data["timestamp"]
    #                     instance.messages.append(message)
                    
    #                 # 恢复文件
    #                 for file_data in instance_data.get("files", []):
    #                     file = ChatFile(
    #                         file_data["filename"],
    #                         file_data["saved_name"],
    #                         file_data["size"],
    #                         file_data["type"]
    #                     )
    #                     file.id = file_data["id"]
    #                     file.upload_time = file_data["upload_time"]
    #                     instance.files.append(file)
                    
    #                 self.instances[instance.id] = instance
                
    #             print(f"成功加载 {len(self.instances)} 个聊天实例")
                
    #     except Exception as e:
    #         print(f"加载实例数据失败: {e}")
    #         # 如果加载失败，创建空实例字典
    #         self.instances = {}
