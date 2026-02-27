


from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents.base import Document
from langchain_openai import OpenAIEmbeddings

import chromadb
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter

api_key = os.environ["EMBEDDINGS_API_KEY"]
model=r'text-embedding-v4'
base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"


# embeddings = OpenAIEmbeddings(
#     model=model
#     ,base_url=base_url
#     ,api_key=api_key
#     )


from langchain_community.embeddings import DashScopeEmbeddings
    
# 使用阿里云 DashScope 嵌入模型
embeddings = DashScopeEmbeddings(
    model=model,
    dashscope_api_key=api_key
)
# 定义向量化数据库客户端
chroma_client = chromadb.PersistentClient(path=str(r'E:\代码\Paper_AI_Assistant\test\.chroma_db'))

Chroma = Chroma(
            client=chroma_client,
            collection_name=f"test_papers",
            embedding_function=embeddings,
        )

print(Chroma)

loader = PyPDFLoader(r'E:\代码\Paper_AI_Assistant\database\download\41e88adf-517b-4681-b3c1-7a8949ac78d3.pdf')
documents = loader.load()

 
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    length_function=len,
)
splits: list[Document] = text_splitter.split_documents(documents)
print('存储')
Chroma.add_documents(splits)  
print('存储完成')

import os
from openai import OpenAI

input_text = "衣服的质量杠杠的" 
client = OpenAI(
    # 若没有配置环境变量，请用阿里云百炼API Key将下行替换为：api_key="sk-xxx",
    # 新加坡和北京地域的API Key不同。获取API Key：https://help.aliyun.com/zh/model-studio/get-api-key
    api_key=api_key,  
    # 以下是北京地域base-url，如果使用新加坡地域的模型，需要将base_url替换为：https://dashscope-intl.aliyuncs.com/compatible-mode/v1
    base_url=base_url
)

completion = client.embeddings.create(
    model="text-embedding-v4" 
)

print(completion)