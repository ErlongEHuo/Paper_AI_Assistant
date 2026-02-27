

# Redis提供了丰富的数据类型，每种类型都有其特定的应用场景： 
## 字符串(String)：缓存、计数器、会话存储
## 列表(List)：消息队列、最新列表、时间线
## 哈希(Hash)：对象存储、用户配置文件
## 集合(Set)：标签、唯一元素集合、共同好友
## 有序集合(Sorted Set)：排行榜、带权重的队列
## 位图(Bitmap)：签到、状态标记、统计
## HyperLogLog：大数据量去重统计
## 流(Stream)：消息队列、事件日志
## 地理空间(Geospatial)：位置服务、附近搜索
## 布隆过滤器(Bloom Filter)：快速判断元素是否存在


import redis


redis_config = {
    'host': 'localhost',
    'port': 6380,
    # 'db': 0
}

redis_client = redis.Redis(**redis_config)

print(redis_client.keys())

# # ============================ string类型 ============================
# redis_client.rpush('test_key1', 'test_value1')
# print(redis_client.get('test_key'))


# # ============================ list类型 ============================

# # 从右侧（末尾）添加元素
# redis_client.rpush('test_key2', 'item1', 'item2', 'item3') 
# # 从左侧（开头）添加元素
# redis_client.lpush('test_key2', 'item0')
 
# # 获取列表所有元素
# print(redis_client.lrange('test_key2', 0, -1))

# # # 获取列表长度
# list_len = redis_client.llen('test_key2')
# print(f"列表长度: {list_len}")  # 输出: 4

# # 弹出元素（从右侧） 删除并返回
# right_item = redis_client.rpop('test_key2')
# print(f"从右侧弹出的元素: {right_item}")  # 输出: item3

# # 弹出元素（从左侧） 删除并返回
# left_item = redis_client.lpop('test_key2')
# print(f"从左侧弹出的元素: {left_item}")  # 输出: item0

# # 获取指定索引的元素
# item_at_index = redis_client.lindex('test_key2', 0)
# print(f"索引0的元素: {item_at_index}")  # 输出: item1

 













# import redis  
 

# # redis配置
# redis_config = {
#                                 'host': 'localhost',
#                                 'port': 6380,
#                                 'db': 0
#                                 }

# class RedisService:
#     def __init__(self):
#         self.redis_client = redis.Redis(
#                             # **Settings.redis_config
#                             **redis_config
#                             )
#         self.chat_instances = 'chat_instances'

#     # 获取所有聊天实例的ID
#     def get_all_instances(self) :
#         """获取所有聊天实例的ID"""
#         keys = self.redis_client.keys(f"{self.chat_instances}*")
#         return [key.decode('utf-8') for key in keys]

#     # 获取单个实例信息
#     def get_instance(self, instance_id: str):
#         """获取单个聊天实例的信息"""
#         key = f"{self.instances_prefix}{instance_id}"
#         if self.redis_client.exists(key):
#             return self.redis_client.hget(key).decode('utf-8')
#         return None
    
#     # 设置单个实例信息
#     def set_instance(self, instance_id: str, instance_info: str = '') -> None:
#         """设置单个聊天实例的信息"""
#         key = f"{self.instances_prefix}{instance_id}"
#         self.redis_client.hset(key, 'message', instance_info)
    
#     # 更新实例信息
#     def update_user(self, user_id, updates):
#         """更新实例信息（部分更新）"""
#         user_key = f"{self.user_key_prefix}{user_id}"
        
#         # 只更新提供的字段
#         for field, value in updates.items():
#             self.redis.hset(user_key, field, str(value))
        
#         return True
 
#     # 上传实例信息
#     def delete_user(self, user_id):
#         """删除实例"""
#         user_key = f"{self.user_key_prefix}{user_id}"
#         return self.redis.delete(user_key) > 0
    
#     # 检测实例是否存在
#     def user_exists(self, user_id):
#         """检查用户是否存在"""
#         user_key = f"{self.user_key_prefix}{user_id}"
#         return self.redis.exists(user_key) > 0

    
# redis_service = RedisService()

# # 复杂的聊天实例数据
# chat_instance = {
#     'id': 'heltest1',
#     'name': 'nihao1',
#     'created_at': '2023-01-01',
#     'messages': [
#         {'user': 'Hello', 'ai': 'Hi there!', 'timestamp': '2023-01-01 12:00:00'},
#         {'user': 'How are you?', 'ai': 'I am fine, thank you!', 'timestamp': '2023-01-01 12:01:00'}
#     ],
#     'settings': {
#         'theme': 'dark',
#         'language': 'zh-CN'
#     }
# }
# print('数据',chat_instance)

# # 转换json
# import json 
# json_str = json.dumps(chat_instance)
# print('json_str',json_str)


# redis_service.set_instance('heltest1',json_str)

# # 判断键的类型
# key_type = redis_service.redis_client.type('heltest1')
# print(key_type)
# if key_type == b'hash':  # Redis返回的是字节类型
#     print("这是一个hash类型")
# else:
#     print(f"这不是hash类型，而是: {key_type.decode('utf-8')}")





# import redis  
 

# # redis配置
# redis_config = {
#                                 'host': 'localhost',
#                                 'port': 6380,
#                                 'db': 0
#                                 }
  
# redis_client = redis.Redis(
#                # **Settings.redis_config
#                **redis_config
#                )
# chat_instances = 'chat_instances'

# # 添加用户
# redis_client.sadd(chat_instances, 'heltest3')
# redis_client.sadd(chat_instances, 'heltest2')

# # 获取所有用户
# all_instances = redis_client.smembers(chat_instances)
# print(all_instances)

# # 检查用户是否存在
# user_exists = redis_client.sismember(chat_instances, 'heltest2')
# print('是否存在：',user_exists)
# # 检查用户是否存在
# user_exists1 = redis_client.sismember(chat_instances, 'heltest4')
# print('是否存在：',user_exists1)


# # 获取用户数量
# user_count = redis_client.scard(chat_instances)
# print('用户数量：',user_count)

# # 删除用户
# redis_client.srem(chat_instances, 'heltest2')
# print(f'删除后：{redis_client.smembers(chat_instances)}')
  


# from ast import List
# from re import L
# import redis  
 

# # redis配置
# redis_config = {
#                                 'host': 'localhost',
#                                 'port': 6380,
#                                 'db': 0
#                                 }
  
# redis_client = redis.Redis(
#                # **Settings.redis_config
#                **redis_config
#                )
# chat_instances = 'chat_instances'

# # 使用hash存储实例
# redis_client.hset(chat_instances, 'heltest3', '测试3')
# redis_client.hset(chat_instances, 'heltest4', '测试4')
# redis_client.hset(chat_instances, 'heltest5', '测试5')


# # 获取所有实例
# all_instances = redis_client.hkeys(chat_instances)
# print('所有实例：',all_instances)


# t1 = list(all_instances)
# print(t1)

# # 打印所有实例
# for i in all_instances:
#     print(i.decode('utf-8'))

# for i in List(all_instances):
#     print(i.decode('utf-8'))

# # 查询指定实例是否存在 
# instance_exists = redis_client.hexists(chat_instances, 'heltest3')
# print('是否存在：',instance_exists)
# instance_exists1 = redis_client.hexists(chat_instances, 'heltest1')
# print('是否存在：',instance_exists1)


# # 查询指定实例信息
# instance_info = redis_client.hget(chat_instances, 'heltest4')
# print('实例信息：',instance_info.decode('utf-8'))


# # 查询实例个数
# instance_count = redis_client.hlen(chat_instances)
# print('实例数量：',instance_count)

# # 删除指定实例
# # redis_client.hdel(chat_instances, 'heltest5')
# # print('删除后：',redis_client.hkeys(chat_instances))
