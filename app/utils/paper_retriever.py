 
from langchain_community.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type
from app.server.document_service import DocumentService

class PaperRetrieverInput(BaseModel):
    """检索工具的输入参数"""
    query: str = Field(description="用户的问题或查询")

class PaperRetrieverTool(BaseTool):
    """论文检索工具 - 用于从上传的论文中检索相关信息"""
    name = "paper_retriever"
    description = "从上传的PDF论文中检索与用户问题相关的文档片段。当用户询问论文内容、方法、数据集等信息时使用此工具。"
    args_schema: Type[BaseModel] = PaperRetrieverInput
    
    def __init__(self, instance_id: str):
        super().__init__()
        self.instance_id = instance_id
        self.doc_service = DocumentService()
        self.retriever = self.doc_service.get_retriever(instance_id)
    
    def _run(self, query: str) -> str:
        """执行检索"""
        # 获取相关文档
        docs = self.retriever.invoke(query)
        
        # 格式化检索结果,包含来源信息
        results = []
        for doc in docs:
            result = {
                "内容": doc.page_content,
                "页码": doc.metadata.get('page', '未知'),
                "来源": doc.metadata.get('source', '未知')
            }
            results.append(result)
        
        # 格式化为字符串
        formatted_results = "\n\n".join([
            f"【片段{i+1}】\n页码: {r['页码']}\n内容: {r['内容']}\n"
            for i, r in enumerate(results)
        ])
        
        return formatted_results

if __name__ == '__main__':
    # 创建一个检索器对象
    retriever = PaperRetrieverTool(instance_id="test_instance")
    
    # 输入一个搜索词
    query = input("2602.21604")
    
    # 检索并返回结果
    results = retriever.retrieve(query)
    print(results)