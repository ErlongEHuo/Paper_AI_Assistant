from typing import List
import ast
import json

import redis
from langchain_community.chat_message_histories import RedisChatMessageHistory
from langchain_core.messages import AIMessage, HumanMessage

from config.settings import settings


class RedisService:
    def __init__(self):
        self.redis_client = redis.Redis(**settings.redis_config)
        self.instances_table = "instances_table" #实例存储的key
        self.paper_prefix = "papers:" # 用户上传文章的key

    def add_instance(self, instance_id: str, instance):
        """ 
        添加一个聊天实例，并保存到redis中\n
        instance_id : 聊天实例id\n
        instance : 聊天实例对象
        """
        self.redis_client.hset(self.instances_table, instance_id, instance)

    def get_instance(self, instance_id: str):
        """获取聊天实例里某实例的信息"""
        instance = self.redis_client.hget(self.instances_table, instance_id)
        if instance:
            return instance.decode("utf-8") # 进行格式转换，从字节转换为字符串
        return None

    def remove_instance(self, instance_id: str):
        self.redis_client.hdel(self.instances_table, instance_id)

    def exists_instance(self, instance_id: str) -> bool:
        return self.redis_client.hexists(self.instances_table, instance_id)

    def get_all_instances(self):
        """ 
        从redis中获取所有聊天实例，并进行解析为ChatInstance对象\n
        return :ChatInstance对象列表
        """
        # 获取所有实例id列表
        instances_id_list = self.get_all_instances_list()
        instances_list = []
        #遍历历所有实例id
        for i in instances_id_list:
            # 获取该实例信息
            instance_str: str = self.get_instance(i)
            # 若实例信息存在
            if instance_str:
                try:
                    # 进行格式转换
                    instance_json = ast.literal_eval(instance_str)
                    from app.models.chat import ChatInstance
                    # 创建一个ChatInstance聊天实例对象
                    chat_instance = ChatInstance(
                        instance_json.get("id"), instance_json.get("name")
                    )
                    # 将 聊天实例的信息获取并赋值给对象
                    chat_instance.created_at = instance_json.get("created_at")
                    chat_instance.messages = instance_json.get("messages")
                    chat_instance.files = instance_json.get("files")
                    # 将聊天实例追加在列表中
                    instances_list.append(chat_instance)
                except json.JSONDecodeError as exc:
                    print(f"redis_service.py/get_all_instances ,解析实例失败 {i}: {exc}")
            else:
                print(f"redis_service.py/get_all_instances ,聊天实例Instance {i} not found")
        return instances_list

    # 获取redis里存储的实例
    def get_all_instances_list(self):
        """ 
            获取redis里存储的实例id列表
        """
        instances_list = []
        for i in self.redis_client.hkeys(self.instances_table):
            instances_list.append(i.decode("utf-8"))
        return instances_list

    def rename_instance(self, instance_id: str, new_id: str):
        instance = self.get_instance(instance_id)
        if instance is not None:
            self.redis_client.hset(self.instances_table, new_id, instance)
            self.redis_client.hdel(self.instances_table, instance_id)
        else:
            raise KeyError(f"Instance {instance_id} not found")

    def _paper_table(self, instance_id: str) -> str:
        """ 
            获取论文元数据存储的key,前缀+聊天实例id
                参数：
                    instance_id: 聊天实例id
                返回：
                    str:论文元数据存储的key
        """
        return f"{self.paper_prefix}{instance_id}"

    def add_paper_metadata(self, instance_id: str, paper_id: str, metadata: dict) -> None:
        """
        添加论文元数据到redis中
            参数:
                instance_id: 聊天实例id
                paper_id: 论文id
                metadata: 论文元数据
            返回: None
        """
        # 获取该实例存储的key
        key = self._paper_table(instance_id)
        self.redis_client.hset(key, paper_id, json.dumps(obj=metadata, ensure_ascii=False))

    def get_paper_metadata(self, instance_id: str, paper_id: str):
        """
            获取论文元数据
                参数：
                    instance_id: 聊天实例id
                    paper_id: 论文id
                返回：
                    json: 论文元数据
        """
        # 获取该实例存储的key
        key = self._paper_table(instance_id)
        # 从redis中获取该论文id的元数据
        value = self.redis_client.hget(key, paper_id)
        # 转换为JSON格式
        if not value:
            return None
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            try:
                return ast.literal_eval(value.decode("utf-8"))
            except Exception:
                return None

    def list_paper_metadata(self, instance_id: str):
        key = self._paper_table(instance_id)
        values = self.redis_client.hvals(key)
        papers = []
        for value in values:
            try:
                papers.append(json.loads(value))
            except json.JSONDecodeError:
                try:
                    papers.append(ast.literal_eval(value.decode("utf-8")))
                except Exception:
                    continue
        return papers


redis_service = RedisService()


class ChatMessageHistory:
    def __init__(self) -> None:
        #定义历史消息客户列表
        self.chat_message_history_client_list: List[RedisChatMessageHistory] = []

    def get_chat_message_history_client(self, instance_id: str) -> RedisChatMessageHistory:
        """ 根据用户实例id进行获取该用户实例的历史消息客户端 \n
            return :RedisChatMessageHistory对象
        """
        # 判断该实例id是否在历史消息客户列表中
        if instance_id not in [item.session_id for item in self.chat_message_history_client_list]:
            # 如果不在，则创建一个新的历史消息客户
            chat_message_history_client = RedisChatMessageHistory(
                session_id=instance_id,
                url=settings.redis_url,
            )
            # 将新创建的历史消息客户添加到列表中
            self.chat_message_history_client_list.append(chat_message_history_client)
            # 返回
            return chat_message_history_client
        # 如果在，则返回该实例id对应的历史消息客户
        chat_message_history_client: RedisChatMessageHistory = self.chat_message_history_client_list[
                                [item.session_id for item in self.chat_message_history_client_list].index(instance_id)
                            ]
        # 返回
        return chat_message_history_client

    def add_user_ai_message(self, chat_message_history_client, user_message, ai_message, message_type, message_time):
        """
         
        """
        # 其他参数信息
        additional_kwargs = {
            "message_type": message_type,
            "message_time": message_time,
        }
        # 添加用户消息
        chat_message_history_client.add_message(
            HumanMessage(content=user_message, additional_kwargs=additional_kwargs)
        )
        # 添加AI消息
        chat_message_history_client.add_message(
            AIMessage(content=ai_message, additional_kwargs=additional_kwargs)
        )
        print('app/server/redis_service.py: add_user_ai_message: 历史消息添加完成') 


chat_message_history = ChatMessageHistory()
