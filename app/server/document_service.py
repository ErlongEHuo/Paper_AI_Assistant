from math import e
import os
from pydoc import doc
import re
import uuid
from urllib.parse import urlparse
from urllib.request import urlopen

import chromadb
from langchain_chroma import Chroma


from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from config.settings import settings,ollamaLLMConfig

from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    UnstructuredHTMLLoader,
)
import tempfile
import shutil
 
from openai import OpenAI

class DocumentService:
    """
    功能：
        1. 加载PDF文档
        2. 对文档进行分块
        3. 对文档块进行向量化
        4. 将向量化后的文档块存储到Chroma向量数据库中
        5. 从Chroma向量数据库中检索文档块
    """

    def __init__(self):

        
        api_key = os.getenv("EMBEDDINGS_API_KEY" ) # 请输入你的api-key
        url_base = os.getenv("EMBEDDINGS_BASE_URL" )
 
        # 使用Ollama 定义向量化模型
        # self.embeddings = OllamaEmbeddings(model=ollamaLLMConfig.embeddingsModel)
          
        # 使用阿里云 DashScope 定义向量化模型
        from langchain_community.embeddings import DashScopeEmbeddings 
        # 使用阿里云 DashScope 嵌入模型
        self.embeddings = DashScopeEmbeddings(
            model=settings.EMBEDDINGS_LLM_MODEL,
            dashscope_api_key=api_key
        )
        
        # 定义向量化数据库客户端
        self.chroma_client = chromadb.PersistentClient(path=str(settings.CHROMADB_DIR))

    def _get_vectorstore(self, instance_id: str) -> Chroma:
        """
            获取或创建一个Chroma向量存储对象
            参数:
                instance_id: 聊天实例id
            返回：
                Chroma向量存储对象 按照instance_id创建
        """

        return Chroma(
            client=self.chroma_client,
            collection_name=f"{instance_id}_papers",
            embedding_function=self.embeddings,
        )

    def _safe_filename(self, filename: str) -> str:
        """
        处理文件名，将文件名 中 不合法的字符 替换为 _ ,并移除首尾空格，返回文件名或进行UUid拼接
            参数:
                filename: 原始文件名
            返回：
                str: 安全的文件名
        """
        # 将文件名 中 不合法的字符 替换为 _ ,并移除首尾空格，返回文件名或进行UUid拼接
        name = re.sub(r"[^\w\-. ]+", "_", filename).strip()
        return name or f"paper_{uuid.uuid4().hex}.pdf"

    def _safe_source_tag(self, source: str) -> str:
        """
        处理来源字符串，将其中不合法的字符 替换为 _ ,并移除首尾空格，返回来源字符串或进行UUid拼接
            参数:
                source: 原始来源字符串
            返回：
                str: 安全的来源字符串
        """
        # 处理来源字符串，将其中不合法的字符 替换为 _ ,并移除首尾空格，返回安全的来源标签或进行UUid拼接
        tag = re.sub(r"[^\w\-.]+", "_", source).strip("_")
        if len(tag) > 80:
            tag = tag[:80]
        return tag or uuid.uuid4().hex

    def _resolve_source(self, source: str) -> tuple[str, str]:
        """"
        解析论文来源,判断是否为arxiv id 或 http url ,如果是则返回url 与 文件名 ,否则抛出异常
            参数：
                source: 论文来源字符串
            返回：
                tuple[str, str]: 包含论文url 与 文件名的元组
        """
        # 解析论文来源
        src = source.strip()
        if not src:
            raise ValueError("Paper source cannot be empty[来源为空]")
        # 判断是否已 arxiv开头
        if src.lower().startswith("arxiv:"):
            # 从arxiv: 提取后面的id
            src = src.split(":", 1)[1].strip()
        # 判断是否为arxiv id格式
        if re.match(r"^\d{4}\.\d{4,5}(v\d+)?$", src):
            # 构建 arxiv 论文Url ，并返回url 与 文件名
            url = f"https://arxiv.org/pdf/{src}.pdf"
            filename = f"{src}.pdf"
            return url, filename
        # 判断是否为http 的url
        if src.startswith("http://") or src.startswith("https://"):
            # 从路径中提取文件名 ，如果没有文件名则默认使用 paper.pdf
            parsed = urlparse(src)
            filename = os.path.basename(parsed.path) or "paper.pdf"
            if not filename.lower().endswith(".pdf"):
                filename = f"{filename}.pdf"
            return src, filename
        # 抛出异常 ，仅支持 arxiv id 或 http url
        raise ValueError("Only arXiv IDs or PDF URLs are supported[仅支持arxiv id 或 http url]")

    def _build_source_file_info(self, source: str, instance_id: str) -> dict:
        """
        根据来源字段进行自动解析url或文件路径，并构建包含文件名、保存文件名、路径、url、类型的字典
            参数:
                source: 原始来源字符串
                instance_id: 聊天实例id
            返回：
                dict: 包含文件名、保存文件名、路径、url、类型的字典
        """
        # 1.解析来源，获取url 与 文件名
        url, filename = self._resolve_source(source)
        # 2.处理文件名中的不合法字符
        safe_name = self._safe_filename(filename)
        # 3.处理来源字符串中的不合法字符
        source_tag = self._safe_source_tag(source)
        # 4.构建保存文件名 ，用户id_来源标签 
        saved_name = f"{instance_id}_{source_tag}"
        # 5.如果保存文件名 不是 pdf 格式 ，则添加 .pdf 后缀
        if not saved_name.lower().endswith(".pdf"):
            saved_name = f"{saved_name}.pdf"
        # 6.设置保存路径
        file_path = settings.UPLOAD_DIR / saved_name
        print(f'app/server/document_service.py : _build_source_file_info : 文件名：{safe_name}，保存文件名：{saved_name}，路径：{file_path}，url：{url}，类型：application/pdf')
        # 7.返回包含文件名、保存文件名、路径、url、类型的字典
        return {
            "filename": safe_name,
            "saved_name": saved_name,
            "path": str(file_path),
            "url": url,
            "type": "application/pdf",
        }

    # def build_source_file_info(self, source: str, instance_id: str) -> dict:
    #     # 
    #     return self._build_source_file_info(source, instance_id)

    def download_source(self, source: str, instance_id: str) -> dict:
        """
        下载来源文件到本地
            参数：
                source: 原始来源字符串
                instance_id: 聊天实例id
            返回：
                dict: 包含文件名、保存文件名、路径、url、类型、大小的字典
        """
        # 获取来源文件信息
        file_info = self._build_source_file_info(source, instance_id)
        file_path = file_info["path"]
        total = 0
        # 进行下载文件到本地
        with urlopen(file_info["url"]) as resp, open(file_path, "wb") as f:
            while True:
                chunk = resp.read(8192)
                if not chunk:
                    break
                total += len(chunk)
                # 判断是否超过最大文件大小
                if total > settings.MAX_FILE_SIZE:
                    raise ValueError("Paper file exceeds the size limit[论文文件大小超过最大限制]")
                f.write(chunk)
        file_info["size"] = total
        return file_info

    def _reset_collection(self, instance_id: str) -> None:
        """
            将指定实例ID的Chroma集合重置（删除）。
        """
        name = f"{instance_id}_papers"
        try:
            self.chroma_client.delete_collection(name)
        except Exception:
            # collection may not exist yet
            pass

    def _detect_file_format(self, file_path: str) -> str:
        """
        检测文件实际格式（根据文件头判断）
            参数:
                file_path: 文件路径
            返回:
                str: 文件格式 ('pdf', 'caj', 'text', 'html', 'unknown')
        """
        try:
            with open(file_path, 'rb') as f:
                header = f.read(100)  # 读取前100字节
                
            # PDF 文件: 以 %PDF- 开头
            if header[:5] == b'%PDF-':
                return 'pdf'
            
            # # CAJ 文件: 以特定字节开头
            # if header[:4] in [b'\xca\x6a\x6c\x00', b'\xca\x6a\x6c\x01']:
            #     return 'caj'
            
            # HTML 文件: 包含 <!DOCTYPE 或 <html
            header_str = header.decode('utf-8', errors='ignore').lower()
            if '<!doctype html' in header_str or '<html' in header_str:
                return 'html'
            
            # 尝试作为文本处理
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    f.read(1000)
                return 'text'
            except:
                try:
                    with open(file_path, 'r', encoding='gbk') as f:
                        f.read(500)
                    return 'text'
                except:
                    return 'text'
                
        except Exception:
            return 'text' 



    def _load_text_file(self, file_path: str, source_name: str) -> list:
        """
        加载纯文本文件
        """
        encodings = ['utf-8', 'gbk', 'gb2312', 'utf-16']
        content = None
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                print(f"成功使用 {encoding} 编码读取文件")
                break
            except UnicodeDecodeError:
                continue
        
        if content is None:
            raise ValueError("无法识别文件编码，请确认文件内容")
        
        # 封装为 Document 对象
        return [Document(
            page_content=content,
            metadata={
                "source": file_path,
                "source_name": source_name,
                "page": 0,
            }
        )]

    def process_pdf(
                        self,
                        file_path: str,
                        instance_id: str,
                        source_name: str | None = None,
                        source_url: str | None = None,
                        source_file: str | None = None,
                        reset_collection: bool = False,
                    ) -> tuple[int, dict]:
        """
        处理PDF文件，进行向量化存储
            1. 重置集合（如果需要）
            2. 使用langchain的文档加载器加载PDF文件
            3. 加载文档
            4. 生成随机的paper_id
            5. 生成显示名称和文件标签
            6. 提取页面号
            7. 计算页面总数
            8. 获取第一页的文本内容
            9. 为每个文档添加元数据
            10. 创建文本切割器对象
            11. 进行文本切割
            12. 添加索引
            13. 获取向量存储对象
            14. 将切割后的文档添加到向量存储中
                参数：
                    file_path: str,  # PDF文件路径
                    instance_id: str,  # 实例ID
                    source_name: str | None = None,  # 来源名称
                    source_url: str | None = None,  # 来源URL
                    source_file: str | None = None,  # 来源文件
                    reset_collection: bool = False,  # 是否重置集合
                返回：
                    tuple[int, dict]: 包含文档数量和元数据的元组
        """
        # 判断是否需要重置集合
        if reset_collection:
            self._reset_collection(instance_id)

        # ========== 检测文件格式并选择加载器 ==========
        
        print('开始解析PDF文件')
        file_format = self._detect_file_format(file_path)
        print(f'检测到文件格式: {file_format}')

        if file_format == 'pdf':
            loader = PyPDFLoader(file_path)
            documents = loader.load()
        elif file_format == 'text':
            documents = self._load_text_file(file_path, source_name or os.path.basename(file_path))
        else:
            raise ValueError(
                f"不支持的文件格式。\n"
                f"当前文件头不是有效的 PDF 格式。\n"
                f"请上传真正的 PDF 文件或纯文本文件。"
            )
        # ==================================================================================================================

        # try: 
        #     # 使用langchain的文档加载器加载PDF文件
        #     loader = PyPDFLoader(file_path)
        # except Exception as e:
        #     raise ValueError(f"无法解析PDF文件：{e}")
        # print('开始加载PDF文件进行解析')
        # try: 
        #     #  加载文档
        #     documents = loader.load()
        # except Exception as e:
        #     raise ValueError(f"无法加载PDF文件：{e}")
        # print(f'app/server/document_service.py : process_pdf :加载PDF文件进行解析：{documents}')
        # 生成随机的paper_id
        paper_id = uuid.uuid4().hex
        # 生成显示名称和文件标签
        display_name = source_name or os.path.basename(file_path)
        file_label = source_file or os.path.basename(file_path)
        # 提取页面号
        page_numbers = [
            doc.metadata.get("page")
            for doc in documents
            if isinstance(doc.metadata.get("page"), int)
        ]
        # 计算页面总数
        page_count = (max(page_numbers) + 1) if page_numbers else len(documents)
        # 获取第一页的文本内容
        first_page_text = documents[0].page_content if documents else ""
        # print(f'app/server/document_service.py : process_pdf :加载PDF文件进行解析：{documents}')
        print('\n\n\n=====获取第一页信息====')
        # print(f'app/server/document_service.py : process_pdf :获取第一页的文本内容：{documents[0].page_content}')
        # 为每个文档添加元数据
        for doc in documents:
            doc.metadata["paper_id"] = paper_id
            doc.metadata["source_name"] = display_name
            doc.metadata["source_file"] = file_label
            doc.metadata["source_path"] = file_path
            doc.metadata["page_count"] = page_count
            if source_url:
                doc.metadata["source_url"] = source_url
        print('===== 加载元数据====')
        # 创建文本切割器对象
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )
        print('===== 文本切割====')
        # 进行文本切割
        splits = text_splitter.split_documents(documents)
         

        # 添加索引
        for idx, doc in enumerate(splits):
            doc.metadata["chunk"] = idx
        print('=== 开始向量存储')
        # 获取向量存储对象
        vectorstore = self._get_vectorstore(instance_id)
        print('存储对象：vectorstore')
        # 将切割后的文档添加到向量存储中
        try: 
            vectorstore.add_documents(splits)
        except Exception as e:
            raise ValueError(f"向量化存储处理失败：{e}")
        print(f'===== 向量化存储处理：{len(splits)} 个文档====')
        # 返回处理结果
        return len(splits), {
            "paper_id": paper_id, # 文档的唯一标识符
            "source_name": display_name,# 文档的显示名称
            "source_file": file_label,# 文档的文件标签
            "source_path": file_path,# 文档的文件路径
            "source_url": source_url,# 文档的URL
            "page_count": page_count,# 文档的总页数
            "first_page_text": first_page_text,# 文档的第一页文本内容
        }

    def process_source(self, source: str, instance_id: str):
        """
        将来源文件进行下载并进行向量化存储处理
            参数：
                source: str,  # 来源字符串
                instance_id: str,  # 实例ID
            返回：
                tuple[dict, int, dict]: 包含文件信息、文档数量和元数据的元组
        """
        # 进行文件下载
        file_info = self.download_source(source, instance_id)
        # 进行向量化存储处理 
        chunk_count, meta = self.process_pdf(
            file_info["path"],
            instance_id,
            source_name=file_info["filename"],
            source_url=file_info.get("url"),
            source_file=file_info.get("saved_name"),
            reset_collection=False,
        )
        print(f'app/server/document_service.py : process_source : 向量化存储处理：{chunk_count}')
        return file_info, chunk_count, meta

    def get_retriever(self, instance_id: str, paper_id: str | None = None):
        """
        获取向量检索器
            参数:
                instance_id: 聊天实例id
                paper_id: 论文id
            返回:
                retriever: 向量检索器
        """ 
        # 创建一个Chroma向量存储对象
        vectorstore = self._get_vectorstore(instance_id)
        # 设置检索参数 
        # k: 检索返回的文档数量
        search_kwargs = {"k": 5}
        if paper_id:
            search_kwargs["filter"] = {"paper_id": paper_id}
        # 返回一个基于向量存储的相似度检索器对象 ,检索文档数量为5
        return vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs=search_kwargs,
        )

 