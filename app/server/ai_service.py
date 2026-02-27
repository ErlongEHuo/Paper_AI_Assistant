import os
import re
from datetime import datetime
from typing import Iterable

from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.server.document_service import DocumentService
from app.server.redis_service import chat_message_history, redis_service
from app.utils.log_util import time_decorator

from config.settings import settings

class AIService:
    """ 
    功能：
        1. 处理用户问题，根据问题中是否存在触发词，判断是否需要合并历史消息
        2. 调用大模型，获取模型回复
        3. 将模型回复添加到历史消息中
    """

    def __init__(self):
        # 历史消息存储key
        self.MEMORY_KEY = "history_memory"

        # api key
        api_key = os.getenv("DEEPSEEK_API_KEY" ) # 请输入你的api-key
        url_base = os.getenv("DEEPSEEK_BASE_URL" )

        # 流式回复模型
        self.chat_llm = ChatOpenAI(
            model=settings.CHAT_LLM_MODEL,
            api_key=api_key,
            base_url=url_base,
            temperature=0,
            streaming=True,
            # extra_body={"thinking": {"type": "enabled"}},
        )

        # 非流式回复模型
        self.chat_llm_nostream = ChatOpenAI(
            model=settings.CHAT_LLM_MODEL,
            api_key=api_key,
            base_url=url_base,
            temperature=0,
            streaming=False,
        )

        self.doc_service = DocumentService()

    def _is_chinese(self, text: str) -> bool:
        """
            return: 是否包含中文字符
        """
        return any("\u4e00" <= ch <= "\u9fff" for ch in text)

    def _get_history_messages(self, instance_id: str, limit: int = 8):
        """
        获取该聊天实例的历史消息
            参数:
                instance_id: 聊天实例id
                limit: 历史消息数量
            返回：
                List 历史消息列表
        """
        # 1.获取该聊天实例的历史消息客户端
        history_client = chat_message_history.get_chat_message_history_client(instance_id)
        # 2. 从历史消息客户端中获取消息
        messages = history_client.messages
        if not messages:
            return []
        return messages[-limit:]

    def _needs_condense(self, question: str) -> bool:
        """
        判断是否需要合并历史消息 根据问题中是否存在触发词 
            参数:
                question: 用户输入的问题
            返回: 
                boolean 是否需要合并历史消息
        """
        # 1.将消息进行全部转换为小写
        q = question.lower()
        triggers = [
            "this",
            "that",
            "it",
            "its",
            "these",
            "those",
            "they",
            "them",
            "their",
            "above",
            "previous",
            "它",
            "这",
            "该",
            "上述",
            "其",
            "它们",
            "以上",
            "之前",
            "前面提到",
            "前面谈到",
        ]
        # 2. 检查是否包含触发词 或 消息长度小于40 
        return any(t in q for t in triggers) #or len(question) < 40

    def _condense_question(self, question: str, history_messages):
        """
        根据历史消息进行精简问题 ,构建系统提示词，通过非流式模型进行推理，返回合并后的问题
            参数:
                question: 用户输入的问题
                history_messages: 历史消息列表
            返回:
                string 合并后的问题
        """
        # 1. 检查是否有历史消息
        if not history_messages:
            # 2. 如果没有历史消息 则直接返回问题
            return question
        # 2. 构建根据历史消息精简问题的系统提示
        system_prompt = (
            "Rewrite the user's question into a standalone question using the chat history. " # 根据聊天记录将用户的提问改写为一个独立的问题
            "Keep the original language. If it's already standalone, return it unchanged." # 如果已经是独立问题，则原样返回。
        )
        # 3. 进行提示词嵌入
        messages = [SystemMessage(content=system_prompt)] + history_messages + [
            HumanMessage(content=question)
        ]
        # 使用非流式模型进行推理
        try:
            result = self.chat_llm_nostream.invoke(messages)
            # 4. 从结果中提取精简后的问题 并进行前后空格处理
            condensed = getattr(result, "content", "")
            return condensed.strip() or question
        except Exception:
            return question

    def _retrieve(self, query: str, instance_id: str):
        """ 未使用
        获取向量检索器 并调用检索器进行文档检索
            参数:
                query: 用户输入的问题
                instance_id: 聊天实例id
            返回:
                List 检索到的文档列表
        """
        # 1.获取一个向量检索器
        retriever = self.doc_service.get_retriever(instance_id)
        # 2. 调用检索器进行文档检索
        try:
            return retriever.invoke(query)
        except Exception:
            return []

    def _format_context(self, docs, use_chinese: bool):
        """
        格式化上下文 从文档列表中提取有效文档，构建上下文块，并添加页号、总页面、内容
            参数:
                docs: 文档列表
                use_chinese: 是否使用中文
            返回:
                string 格式化后的上下文
        """
        #
        context_blocks = []
        # 1. 过滤掉空内容的文档
        valid_docs = [doc for doc in docs if getattr(doc, "page_content", "").strip()]
        # 2. 遍历有效文档 构建上下文块
        for idx, doc in enumerate(valid_docs, start=1):
            # 提取文档内容 进行.strip() 处理
            content = doc.page_content.strip()
            # 提取元数据
            metadata = doc.metadata or {}
            # 获取页面号
            page = metadata.get("page")
            # 获取页面总数
            page_num = None
            # 判断是否为数字类型
            if isinstance(page, int):
                page_num = page + 1 #累加
            elif page is not None:
                page_num = page
            # 获取论文名称 或 论文的路径名 
            source_name = metadata.get("source_name") or os.path.basename(
                str(metadata.get("source", ""))
            )
            # 获取分块号
            chunk = metadata.get("chunk")
            # 判断是否中文进行分别处理 第idx页 ，总页数为page_num
            if use_chinese:
                if page_num is not None:
                    citation_tag = f"[{idx}页,{page_num}]"
                else:
                    citation_tag = f"[{idx}页]"
            else:
                if page_num is not None:
                    citation_tag = f"[{idx}pag,{page_num}]"
                else:
                    citation_tag = f"[{idx}pag]"
            # 构建上下文块 格式为：分块号 页面号 内容
            context_blocks.append(f"{citation_tag} {content}")
        # 3. 将文档内容进行合并，上下文进行换行
        return "\n\n".join(context_blocks)

    def _build_source_header(self, docs, use_chinese: bool, selected_meta: dict | None = None) -> str:
        """
        构建源标题 根据文档列表中获取的元数据构建源标题 或 已有的选中的元数据 根据use_chinese自动进行中英文切换
            参数:
                docs: 检索的文档内容
                use_chinese: 是否使用中文
                selected_meta: 选中的元数据
            返回:
                string 源标题
        """

        # 如果已有选中的元数据 ，进行解析元数据 ，获取论文标题、文件名、路径 进行返回
        if selected_meta:
            title = selected_meta.get("paper_title") or selected_meta.get("source_name") or "未知"
            file_name = selected_meta.get("file_name") or selected_meta.get("source_file") or "未知"
            path = selected_meta.get("path") or selected_meta.get("source_path") or "未知"
            if use_chinese:
                return f"正在询问的论文名称：{title}，PDF文件：{file_name}，路径：{path}\n\n"
            return f"Paper in focus: {title}, PDF: {file_name}, Path: {path}\n\n"
        # 定义变量
        names = []
        files = []
        paths = []
        # 从检索的文档内容中解析元数据 ，获取论文标题、文件名、路径
        for doc in docs:
            metadata = getattr(doc, "metadata", {}) or {}
            # 获取元数据中的来源名称，获取来源文件路径
            source_name = metadata.get("source_name") or os.path.basename(
                str(metadata.get("source", ""))
            )
            # 获取元数据中的来源路径和文件逻辑
            source_file = (
                metadata.get("source_url")
                or metadata.get("source_file")
                or source_name
            )
            # 获取来源路径
            source_path = metadata.get("source_path")
            if source_name and source_name not in names:
                names.append(source_name)
            if source_file and source_file not in files:
                files.append(source_file)
            if source_path and source_path not in paths:
                paths.append(source_path)

        name_text = "；".join(names) if names else "未知"
        file_text = "；".join(files) if files else "未知"
        path_text = "；".join(paths) if paths else "未知"
        # 进行返回 解析后的元数据信息
        if use_chinese:
            return f"正在询问的论文名称：{name_text}，PDF文件：{file_text}，路径：{path_text}\n\n"
        return f"Paper in focus: {name_text}, PDF: {file_text}, Path: {path_text}\n\n"

    def _build_prompt(self, question: str, context_text: str, use_chinese: bool):
        """
        构建系统提示词和用户提示词
            参数：
                question: 用户问题
                context_text: 检索的论文片段内容
                use_chinese: 是否使用中文
            返回：
                tuple 系统提示词和用户提示词
        """
        if use_chinese:
            system_prompt = (
                "你是一名论文问答助手。你根据提供的论文片段回答。"
                "如果片段中没有答案，你可以参考历史聊天信息进行回复。并说明未在论文中找到相关信息，进行自我解释说明。"
                "使用与用户问题相同的语言作答。"
                "每个关键结论后用片段中的引用标记进行引用，不要编造引用。"
                "引用标记必须包含页码与段落号，并必须使用中文方括号括起来，必须按照该格式输出。例如：【引用1：第4页】、【引用2：第2页】。"
                "在回答中可加入简短的原文引用(尽量短句)，并保持准确。"
                "请识别并在适当时给出关键概念、方法、数据集，并在有价值时补充解释或建议。"
                "你可以在回复完用户消息后，你可以根据用户历史聊天信息上下文中进行自我总结给出一些相关性信息或用户可能感兴趣的问题。使用格式例如：'你可能感兴趣的问题：1.你可能对论文中的方法或数据集感兴趣。 2.问题2 等'"
                # "不要单独列出参考文献或引用位置列表。"
                """将使用到的引用信息，在回复的最后使用以下格式输出，并将引用的信息进行序号排序 “引用序号：引用内容”格式进行输出 ，你必须按照以下格式输出：\n
                ===引用信息如下===：\t\n
                 1. 【引用1：第4页】:引用信息\t\n
                 2. 【引用2：第2页】:引用信息\t\n
                """ 
            )
            user_prompt = (
                f"用户问题：{question}\n\n"
                "你可以参考以下可用论文片段：\n"
                f"{context_text or '（你的问题在论文中未找到相关片段）'}\n\n"
                "根据以上要求进行直接回答。如果用户问题与论文内容无关，你可以根据用户历史聊天信息上下文中进行自我总结给出一些相关性信息。但不能脱离上下文进行回答。"
            )
        else:
            system_prompt = (
                "You are a paper QA assistant. Answer only from the provided paper snippets. "
                "If there is no answer in the fragment, you can refer to the historical chat information to reply. And explain that the relevant information was not found in the paper, and provide an explanation for yourself. "
                "Respond in the same language as the user. "
                "The citation marks must include page numbers and paragraph numbers, and must be enclosed within Chinese square brackets. They must be presented in this format. For example: 【Citation 1: Page 4】; 【Citation 2: Page 2】."
                "Use short direct quotes when helpful. "
                "Identify key concepts, methods, and datasets when present, and add brief explanations or suggestions when appropriate. "
                "Do not add a separate references or citations list."
                "After replying to the user's message, you can summarize the context of the user's historical chat information and provide some relevant information or questions that the user might be interested in. Use the format, for example: "
                """TThe referenced information to be used will be output at the end of the reply in the following format: "Reference Number: Reference Content". The referenced information should be sorted in sequence. Please follow this format for output. 
                    ===Reference Information as follows===: \t\n
                    1. 【1: Page 4】: Reference Information \t\n
                    2. 【2: Page 2】: Reference Information \t\n
                """
            )
            user_prompt = (
                f"User question: {question}\n\n"
                "You can refer to the following available paper fragments:\n"
                f"{context_text or '(No relevant passage was found in the paper regarding your question.)'}\n\n"
                "Based on the above requirements, please provide a direct answer. If the user's question is not related to the content of the paper, you can summarize relevant information based on the context of the user's previous chat history. However, you must not answer outside the context."
            )
        return system_prompt, user_prompt

    def _stream_with_sources(self, prompt_messages, use_chinese: bool, header: str) -> Iterable[str]:
        """
        流式返回AI响应内容，支持头部信息 
            参数:
                prompt_messages: 发送给AI模型的提示消息列表
                use_chinese: 是否使用中文模式（当前未使用，保留参数）
                header: 响应头部信息，如加载提示等
                
            返回:
                Iterable[str]: 生成器，逐个产生响应文本片段
        """
        # 如果存在头部信息，首先返回头部
        if header:
            yield header
            
        # 遍历语言模型流式返回的数据块
        for chunk in self.chat_llm.stream(prompt_messages):
            # 获取数据块中的内容，如果不存在则返回None
            content = getattr(chunk, "content", None)
            # 只有当内容不为空时才返回
            if content:
                yield content

    @time_decorator
    def get_response_stream(self, message: str, instance_id: str, paper_id: str | None = None):
        """
        获取流式响应
        1.进行问题处理判断回复的语言 
        2.获取该用户的历史聊天记录 
        3.根据问题进行判断是否需要与历史聊天记录进行精简用户的问题
        4.将问题进行向量化检索文档
        5.获取文档的元数据，目的：ai输出时表明引用的是哪篇论文
        6.将问题、向量化文档、历史聊天记录 进行提示词格式化
        7.进行流式回复
            参数:
                message: 用户输入的问题
                instance_id: 聊天实例id
                paper_id: 论文id
            返回：
                流式响应内容
        """
        # 1. 去除前后空格
        question = message.strip()
        print(f'\n\n\n question: {question}')
        # 2. 检查是否有中文
        use_chinese = self._is_chinese(question)
        # 3. 获取该聊天实例的历史消息
        history_messages = self._get_history_messages(instance_id)

        print(f'history_messages: {history_messages}')
        # 4. 检查是否需要精简问题
        if self._needs_condense(question):
            # 4.1 根据历史消息精简问题
            print('\n\n\n ==============1================= \n\n\n ')
            retrieval_query = self._condense_question(question, history_messages)
        else:
            print('\n\n\n ==============2================= \n\n\n ')
            retrieval_query = question
        print(f'\n\n\n\n retrieval_query: {retrieval_query}')

        # 5. 根据问题进行向量化检索 并根据paper_id 进行筛选向量化的论文
        docs = self._retrieve_with_paper(retrieval_query, instance_id, paper_id)
        # docs = self._retrieve_with_paper(question, instance_id, paper_id)
        print(f'\n\n\n docs: {docs}')

        # 6. 将检索到的文档进行格式化 
        context_text = self._format_context(docs, use_chinese)
        print(f'\n\n\n context_text: {context_text}')
        # 获取该论文的元数据
        selected_meta = None
        if paper_id:
            # 根据论文id + 用户实例id 获取该论文的元数据
            selected_meta = redis_service.get_paper_metadata(instance_id, paper_id)
        # 7. 构建 元数据或文档中获取 源标头信息
        header = self._build_source_header(docs, use_chinese, selected_meta)
        print(f'\n\n\n selected_meta: {selected_meta}')
        print(f'\n\n\n selected_meta-summary: {selected_meta.get("summary")}, selected_meta-title: {selected_meta.get("paper_title")}')
        # 8. 构建提示词
        system_prompt, user_prompt = self._build_prompt(question, context_text, use_chinese)
        prompt_messages = [SystemMessage(content=system_prompt)] + history_messages + [
            HumanMessage(content=user_prompt)
        ]
        print(f'\n\n\n prompt_messages: {prompt_messages}')
        # 9. 调用语言模型流式返回响应内容
        return self._stream_with_sources(prompt_messages, use_chinese, header)

    def get_response(self, message: str, instance_id: str, paper_id: str | None = None) -> str:
        """
        非流式输出时，将流式响应内容拼接成一个字符串
            参数：
                message: 用户输入的问题
                instance_id: 聊天实例id
                paper_id: 论文id
            返回：
                str: 拼接后的响应字符串
        """
        # 初始化空列表
        chunks = []
        # 循环将流式响应内容添加到列表中
        for part in self.get_response_stream(message, instance_id, paper_id):
            chunks.append(part)
        # 将列表中的内容拼接成一个字符串
        return "".join(chunks)

    def _retrieve_with_paper(self, query: str, instance_id: str, paper_id: str | None):
        """
        根据查询字符串进行向量化检索 并根据paper_id 进行筛选向量化的论文
        参数:
            query: 查询字符串
            instance_id: 聊天实例id
            paper_id: 论文id
        返回：
            List:检索到的文档列表
        """
        # 1. 获取检索器
        retriever = self.doc_service.get_retriever(instance_id, paper_id)
        
        print(f'\n ===== \n instance_id:{instance_id} , paper_id:{paper_id}')
        print(f'\n\n\n retriever: {retriever}')
        # 2. 进行向量化检索
        try:
            return retriever.invoke(query)
        except Exception:
            return []

    def _summarize_paper(self, 
                         first_page_text: str,
                           fallback_title: str,
                             use_chinese: bool) -> tuple[str, str]:
        """
        解析获取出论文的元数据 包含标题 与 摘要
            1.根据参数 use_chinese 生成使用中文/英文 系统提示词
            2.构造用户输入首页信息
            3.调用LLM进行解析title 与 summary 
            4.解析LLM返回的结果，提取title 与 summary
                输入：
                    first_page_text: 首页文本
                    fallback_title: 标题
                    use_chinese: 是否中文
                输出：
                    title: 标题
                    summary: 摘要
        """
        # 1. 论文首页文本信息
        text = (first_page_text or "").strip()
        # 2. 没有首页信息返回空标题
        if not text:
            return fallback_title, ""
        # 3. 编写系统提示词
        system_prompt = (
            "你是论文解析助手。请根据给定的论文首页内容，提取论文标题并给出一句话摘要。"
            "请输出JSON，格式为：{\"title\": \"...\", \"summary\": \"...\"}。"
            if use_chinese
            else "You are a paper parsing assistant. From the first page text, extract the paper title and a 1-sentence summary. "
            "Return JSON: {\"title\": \"...\", \"summary\": \"...\"}."
        )
        # 4. 进行提示词组合
        messages = [SystemMessage(content=system_prompt), HumanMessage(content=text[:2000])]
        # 5.调用非流式输出LLM 进行解析 
        try:
            result = self.chat_llm_nostream.invoke(messages)
            content = getattr(result, "content", "")
            import json

            data = json.loads(content)
            title = data.get("title") or fallback_title
            summary = data.get("summary") or ""
            return title, summary
        except Exception:
            return fallback_title, ""

    def process_file_upload(self, filename: str, file_path: str, instance_id: str) -> dict:
        """
        处理文件上传 并解析出论文的元数据
        1.使用文本解析器解析pdf文件
        2.获取pdf首页的数据
        3.调用LLM解析论文首页 的title 与 summary
        4.构建论文元数据
        5.将元数据存储在redis中
            输入：
                filename: 文件名
                file_path: 文件路径
                instance_id: 实例ID
            输出：
                dict: 论文元数据
        """
        print(f'\n ===== \n 开始处理文件上传: {filename} , 路径: {file_path} , 实例ID: {instance_id}')
        try:
            print('\n ===== \n 开始解析pdf')
            # 调用pdf解析
            chunk_count, meta = self.doc_service.process_pdf(
                file_path,
                instance_id,
                source_name=filename,
                source_file=os.path.basename(file_path),
                reset_collection=False,
            )
            # print(f'\n ===== \n 解析出的元数据: {chunk_count} , {meta}')
            # 获取 文本内容，并判断是否包含中文字符
            use_chinese = self._is_chinese(meta.get("first_page_text", "") or filename)
            # print(f'\n ===== \n 是否包含中文字符: {use_chinese}')
            # 调用LLM解析论文首页 的title 与 summary
            title, summary = self._summarize_paper(
                meta.get("first_page_text", ""),
                meta.get("source_name") or filename,
                use_chinese,
            )
            print(f'\n ===== \n 解析出的标题: {title} , 摘要: {summary}')
            # 构建论文元数据
            paper_meta = {
                "paper_id": meta.get("paper_id"),
                "instance_id": instance_id,
                "file_id": meta.get("source_file"),
                "file_name": meta.get("source_name"),
                "paper_title": title,
                "page_count": meta.get("page_count"),
                "summary": summary,
                "source_url": meta.get("source_url"),
                "path": meta.get("source_path"),
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            print(f'\n ===== \n 构建的论文元数据: {paper_meta}')
            # 将论文元数据存储在reidis中
            redis_service.add_paper_metadata(instance_id, paper_meta["paper_id"], paper_meta)
            print('\n======\n 论文元数据已存储在redis中')
            # 返回解析后的信息
            return {
                "message": f"文件 '{filename}' 上传成功，已解析 {chunk_count} 个片段。现在可以开始提问。",
                "meta": paper_meta,
            }
        except Exception as exc:
            return {"error": f"文件处理失败: {exc}"}

    def prepare_paper_source(self, source: str, instance_id: str) -> dict:
        """
        准备文件来源，进行将文件来源进行处理 获取文件名、保存文件名、路径、url、类型的字典
            参数：
                source: 原始来源字符串
                instance_id: 聊天实例id
            返回：
                dict: 包含文件名、保存文件名、路径、url、类型的字典
        """
        # 进行将文件来源进行处理 获取文件名、保存文件名、路径、url、类型的字典
        try:
            return {"file_info": self.doc_service._build_source_file_info(source, instance_id)}
        except Exception as exc:
            return {"error": f"论文来源处理失败: {exc}"}

    def process_paper_source(self, source: str, instance_id: str) -> dict:
        """
        进行文件下载与向量化存储，并解析出论文的元数据，并将论文元数据存储在redis中
            参数：
                source: 原始来源字符串
                instance_id: 聊天实例id
            返回：
                dict: 包含文件名、保存文件名、路径、url、类型的字典
        """ 
        try:
            # 调用文档服务处理来源文件进行下载与向量化存储
            file_info, chunk_count, meta = self.doc_service.process_source(source, instance_id)
            # 进行判断是否包含中文字符
            use_chinese = self._is_chinese(meta.get("first_page_text", "") or file_info.get("filename", ""))
            # 调用LLM解析论文首页 的title 与 summary
            title, summary = self._summarize_paper(
                meta.get("first_page_text", ""),
                meta.get("source_name") or file_info.get("filename", ""),
                use_chinese,
            )
            # 构建论文元数据
            paper_meta = {
                "paper_id": meta.get("paper_id"),
                "instance_id": instance_id,
                "file_id": meta.get("source_file"),
                "file_name": meta.get("source_name"),
                "paper_title": title,
                "page_count": meta.get("page_count"),
                "summary": summary,
                "source_url": meta.get("source_url"),
                "path": meta.get("source_path"),
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            # 将论文元数据存储在reidis中
            redis_service.add_paper_metadata(instance_id, paper_meta["paper_id"], paper_meta)
            # 返回解析后的信息
            return {
                "file_info": file_info,
                "chunk_count": chunk_count,
                "meta": paper_meta,
                "message": (
                    f"已导入论文来源 '{file_info['filename']}'，解析 {chunk_count} 个片段。"
                    "现在可以开始提问。"
                ),
            }
        except Exception as exc:
            return {"error": f"论文来源处理失败: {exc}"}