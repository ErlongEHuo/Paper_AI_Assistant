
# from typing import List
# from langchain_community.chat_message_histories import RedisChatMessageHistory
 


     
# # class ChatMessageHistory(RedisChatMessageHistory) :

# #     def __init__(self) -> None:
        
# #         chat_message_history = RedisChatMessageHistory(
# #             session_id='instance_id1',
# #             url='redis://:@localhost:6380'
# #         )
# #         chat_message_history_client = []

# #     # def get_chat_message_history_client(self,instance_id:str) :
# #     #     """ 获取Redis历史消息对象""" 
 


# if __name__ == "__main__": 
#     # new_chat_message_history = ChatMessageHistory()
#     # print(new_chat_message_history,type(new_chat_message_history))
    
#     chat_message_history_client_list:List[RedisChatMessageHistory] = []
    
#     new_chat_message_history = RedisChatMessageHistory(
#                 session_id='instance_id1',
#                 url='redis://:@localhost:6380'
#             )
    
#     print('对象：',new_chat_message_history,'类型：',type(new_chat_message_history))

#     print(new_chat_message_history.session_id)

#     str='lll1'

#     # 判断 str 是否在 chat_message_history_client_list 中
#     if str not in [item.session_id for item in chat_message_history_client_list]:
#         chat_message_history_client_list.append(new_chat_message_history)



# from langchain_core.runnables.history import RunnableWithMessageHistory
# RunnableWithMessageHistory = RunnableWithMessageHistory()

# self.chatModel="gemma3:4b" 
# self.chatModel="qwen3-vl:8b" 
from langchain_ollama import ChatOllama

 


chat_llm = ChatOllama(
            model="deepseek-r1:7b" , # 对话模型
            verbose=True, # 开启 verbose 模式，打印详细日志
            validate_model_on_init = True , # 初始化时验证模型是否存在
            temperature=0, # 温度参数，控制生成文本的随机性 
            streaming=True, # 开启流式输出
        )

tools =[]
prompt= ''
from langchain.agents import create_agent
# 创建一个agent 
agent = create_agent(
    model=chat_llm, 
    tools= tools,
    system_prompt=prompt,
    # memory=memory,
) #智能体 

print(agent)