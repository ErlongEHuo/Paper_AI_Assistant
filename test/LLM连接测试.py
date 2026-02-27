import os

from langchain_openai import ChatOpenAI

  
# ========================== deepseek 模型测试 =========================
api_key = os.environ["CHAT_API_KEY"]
url_base = r'https://api.deepseek.com'

llm = ChatOpenAI(
    model="deepseek-chat",
    api_key=api_key,
    base_url=url_base,
    # stream_usage=True,
    # temperature=None,
    # max_tokens=None,
    # timeout=None,
    # reasoning_effort="low",
    # max_retries=2,
    # api_key="...",  # If you prefer to pass api key in directly
    # base_url="...",
    # organization="...",
    # other params...
)

responses = llm.invoke('你好呀!')
print(responses.content)
