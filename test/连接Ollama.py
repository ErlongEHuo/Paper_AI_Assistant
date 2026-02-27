



# 导入必要库 

 
# ------------------------------ 连接 Ollama chat模型 -----------------------

# 导入langchain的chat模型 对话模型  
from langchain_ollama import ChatOllama  
# 测试路径使用
import sys
from pathlib import Path
# 添加项目根目录到Python搜索路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import ollamaLLMConfig

llm = ChatOllama(
    model=ollamaLLMConfig.chatModel,    # 定义使用的模型
    validate_model_on_init=True,        # 初始化时验证模型是否存在
    temperature=ollamaLLMConfig.temperature,    # 定义生成文本的随机性
) 

result = llm.invoke(
    "你是谁？"
)

print(result.content)


# ------------------------------ 连接 Ollama embeddings 模型 -----------------------

# # 测试路径使用
# from logging import config
# import sys
# from pathlib import Path
# # 添加项目根目录到Python搜索路径
# project_root = Path(__file__).parent.parent
# sys.path.insert(0, str(project_root)) 




# # 导入LLM配置文件
# from config.llm_config import ollamaLLMConfig
# # 模型LLM配置文件
# mondel_conf = ollamaLLMConfig

# # embeddings 模型 Ollama 测试
# from langchain_ollama import OllamaEmbeddings

# # 定义embeddings模型
# embeddings = OllamaEmbeddings(
#     model=mondel_conf.embeddingsModel,
# )


# data =  [
#         "你好",
#         "你好啊",
#         "你叫什么名字?",
#         "我叫王大锤",
#         "很高兴认识你大锤",
#     ]
 

# # vector_Documents = embeddings.embed_documents(data) 
# # print("\n\n\nembeddings 模型 Ollama 嵌入后结果:",vector_Documents)



# # embed_Query = embeddings.embed_query('这段话提到了什么名字？') 
# # print("\n\n\nembeddings 模型 Ollama 查询后结果:",embed_Query) 


# # -----------持久化到向量数据库 ---------------
# import chromadb # 导入 Chroma 向量数据库
# # from langchain_community.vectorstores import Chroma # langchain 提供的 Chroma 向量数据库类
# from langchain_chroma import Chroma


# # ============ 配置阶段 ============

# # App配置文件
# from config.settings import settings
# conf = settings


# # 1. 创建Chroma客户端并指定存储路径
# chroma_client = chromadb.PersistentClient(
#     path=conf.CHROMADB_DIR  # 向量数据库存储目录
# )



# # # ============ 存储阶段 ============

# # # 2. 创建或获取集合（collection） 进行存储
# # Chroma.from_texts(
# #     texts=data, # 要嵌入的文本数据
# #     embedding=embeddings, # 用于文本嵌入的模型
# #     client=chroma_client, # Chroma 客户端实例，用于连接和操作向量数据库
# #     collection_name=conf.CHROMADB_COLLECTION_NAME, # 要创建的向量数据库集合名称
# # )
 
# # # 3. 验证存储（可选）
# # print(f"✅ 向量数据库已保存到 ./chroma_db")
# # print(f"📊 存储了 {len(data)} 个文档")
# # print(f"🗂️  集合名称:{conf.CHROMADB_COLLECTION_NAME}")
# # collection = chroma_client.get_collection(conf.CHROMADB_COLLECTION_NAME)
# # print(f"📈 集合中的向量数量: {collection.count()}")


# # ================== 检索阶段 ==================

# # 3. 加载向量存储
# vectorstore = Chroma(
#     client=chroma_client,
#     collection_name=conf.CHROMADB_COLLECTION_NAME,
#     embedding_function=embeddings
# )

# # 4. 创建检索器
# retriever = vectorstore.as_retriever(
#     search_kwargs={"k": 3}, # 检索TopK个文档
#     return_source_documents=True, # 是否返回源文档
#     # search_type="similarity", # 检索类型，默认是相似度检索
#     search_type="mmr", # 最大边际相关检索
#     # search_type="similarity_score_threshold",  # 相似度阈值检索
#     # search_kwargs={"score_threshold": 0.2}, # 相似度阈值
# )

# # 5. 使用检索器进行检索
# query = "王"
# retrieved_documents = retriever.invoke(query)
# print(retrieved_documents)



# # =================== 内存检索器 =========================
# from langchain_core.vectorstores import InMemoryVectorStore  
# vectorstore: InMemoryVectorStore = InMemoryVectorStore.from_texts(
#     data,
#     embedding=embeddings,
# ) 
# # Use the vectorstore as a retriever
# retriever = vectorstore.as_retriever() 
# # Retrieve the most similar text
# retrieved_documents = retriever.invoke("大锤") 
# # Show the retrieved document's content
# print(retrieved_documents[0].page_content)