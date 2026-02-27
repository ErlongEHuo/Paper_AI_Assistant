# 导入 datetime 用于时间戳
from datetime import datetime
# 导入 Optional 用于类型标注
from typing import Optional
# 导入 Streamlit 用于界面渲染
import streamlit as st

# 导入 ChatInstance 类型用于类型标注
from app.models.chat import ChatInstance
# 导入 AI 服务与聊天管理器
from app.server.chat_service import ai_service, chat_manager
# 导入 Redis 聊天历史与元数据工具
from app.server.redis_service import chat_message_history, redis_service
from langchain_core.messages import AIMessage
# 导入文件上传工具
from app.utils.file_uploader import file_uploader


# 定义兼容不同版本 Streamlit 的重运行函数
def _rerun():
    # 判断是否存在新版 rerun API
    if hasattr(st, "rerun"):
        # 使用新版 API 触发重运行
        st.rerun()
    # 否则回退到旧版 API
    else:
        # 使用旧版 API 触发重运行
        st.experimental_rerun()


# 从持久化存储加载聊天实例
def _load_instances() -> list[ChatInstance]:
    """
    从后端存储加载所有聊天实例，确保至少存在一个默认实例。
    
    步骤：
    1. 从 Redis 强制刷新实例数据
    2. 获取所有实例对象
    3. 若无实例则创建默认实例
    4. 尝试按创建时间排序
    
    Returns:
        list[ChatInstance]: 按创建时间排序的聊天实例列表，至少包含一个默认实例
    
    Raises:
        Exception: 当从 Redis 加载失败时显示错误信息，但会继续执行并返回默认实例
    """  
    # 尝试从后端重新加载实例
    try:
        # 强制从存储刷新实例
        chat_manager.load_instances()
    # 捕获加载异常
    except Exception as exc:
        # 向页面报告错误
        st.error(f"streamlit_app.py/_load_instances 加载聊天实例失败: {exc}")


    # 读取全部实例
    instances = chat_manager.get_all_instances()

    # 若无实例则创建默认实例
    if not instances:
        # 创建并保存默认实例
        instances = [chat_manager.create_instance("Default Chat")]

    # 尝试按创建时间排序
    try:
        # 按 created_at 字段排序
        instances.sort(key=lambda inst: inst.created_at)
    # 排序失败时忽略
    except Exception:
        # 排序异常时不处理
        pass
    # 返回实例列表
    return instances


# 确保当前实例 ID 有效并写入会话状态
def _ensure_current_instance(instances: list[ChatInstance]) -> Optional[str]:
    """
        1.将实例ID写入会话状态\n
        2.从会话中获取当前实例id\n
        3.若无实例使用实例列表中的第一个实例\n
        return:当前会话聊天实例 ID\n
    """
    # 组装实例 ID 列表
    instance_ids = [inst.id for inst in instances]
    # 若无实例直接返回 None
    if not instance_ids:
        # 提示调用方无实例
        return None
    

    # 从会话状态读取当前实例 ID
    current_id = st.session_state.get("current_instance_id")
    # 若当前 ID 不存在或无效则重置
    if current_id not in instance_ids:
        # 默认选中第一个实例
        st.session_state.current_instance_id = instance_ids[0]
    # 返回当前实例 ID
    return st.session_state.current_instance_id


# 创建新聊天并更新当前实例 ID
def _create_new_chat() -> None:
    """
        1.创建新的聊天实例
        2.将新实例设为当前实例
        3.同步更新实例选择器状态
    """
    # 创建新的聊天实例
    new_instance = chat_manager.create_instance("New Chat")
    # 将新实例设为当前实例
    st.session_state.current_instance_id = new_instance.id
    # 同步更新实例选择器状态
    st.session_state.instance_selector = new_instance.id


# 渲染侧边栏并返回选中的实例 ID
def _render_sidebar(instances: list[ChatInstance]) -> str:
    """
        1.设置标题\n
        2.渲染新建按钮\n
        3.渲染实例选择器并处理选择器的默认选择实例逻辑\n
        return:\n
            str: 选中的实例 ID
    """

    # ========== 渲染侧边栏，包括新建按钮 ========== 
    # 设置侧边栏标题
    st.sidebar.title("AI智能论文助手")
    # 渲染新建按钮并绑定回调
    st.sidebar.button("新建聊天", key="new_chat_button", on_click=_create_new_chat)


    # ========== 渲染聊天实例选择器，控制用户使用那个聊天实例进行交互 ==========
    # 提取实例 ID 列表
    instance_ids = [inst.id for inst in instances]

    # # 统计实例名称出现次数
    # name_counts = {}
    # # 遍历实例统计名称
    # for inst in instances:
    #     # 递增名称计数
    #     name_counts[inst.name] = name_counts.get(inst.name, 0) + 1

    # # 构造展示标签映射
    # label_map = {}
    # # 遍历实例生成展示标签
    # for inst in instances:
    #     # 判断是否存在重名
    #     if name_counts.get(inst.name, 0) > 1:
    #         # 使用名称加短 ID 作为展示
    #         label_map[inst.id] = f"{inst.name} ({inst.id[:6]})"
    #     # 无重名则直接使用名称
    #     else:
    #         # 使用名称作为展示
    #         label_map[inst.id] = inst.name
    
    # 构造展示标签映射
    label_map = {}
    # 遍历实例生成展示标签
    for inst in instances:
        label_map[inst.id] = f"{inst.name} ({inst.id[:6]})"


    # 若没有实例则返回空字符串
    if not instance_ids:
        # 返回空 ID 给调用方,退出函数
        print('streamlit_app.py/_render_sidebar 无实例异常！')
        return ""
    
    # ========== 处理实例选择器功能，解决特殊异常情况导致无聊天实例时处理 ==========
    # 获取选择器中的当前值
    current_id = st.session_state.get("instance_selector")
    # 若选择器状态不存在则回退到当前实例
    if current_id is None:
        # 使用当前实例或第一个实例作为默认值
        current_id = st.session_state.get("current_instance_id", instance_ids[0])
    # 若当前实例 ID 不在列表中则修正
    if current_id not in instance_ids:
        # 回退到第一个实例
        current_id = instance_ids[0]
        # 同步修正到会话状态
        st.session_state.current_instance_id = current_id
        # 同步修正到选择器状态
        st.session_state.instance_selector = current_id

    # ========== 渲染聊天实例选择器，控制用户使用那个聊天实例进行交互 ==========
    # 渲染实例单选框并绑定选择器状态
    selected_id = st.sidebar.radio(
        # 设置选择器标题
        "聊天实例列表",
        # 设置选项列表 信息
        instance_ids,
        # 指定默认选中索引
        index=instance_ids.index(current_id),
        # 指定展示名称格式
        # lambda instance_id: 匿名函数，参数=instance_id ，通过label_map.get获取instance_id的值，如果没有返回instance_id
        format_func=lambda instance_id: label_map.get(instance_id, instance_id), 
        # 绑定会话状态 key
        key="instance_selector",
        # 结束单选框参数定义
    )
    # 将选择结果同步到当前实例 ID
    st.session_state.current_instance_id = selected_id



    # 返回选中的实例 ID
    return selected_id


# 处理当前聊天实例的文件上传
def _handle_file_upload(instance: ChatInstance,
                         uploaded_file,
                           display_container=None,
                             selected_paper_key: Optional[str] = None
                             ) -> None:
    """
        1.在当前聊天实例内处理上传文件
        2.上传后写入实例与历史
    """
    print('\n==========开始文件上传==========\n')
    # 未选择文件则直接返回
    if uploaded_file is None:
        # 无文件时不处理
        return
    
    # 构造去重标记
    last_key = (uploaded_file.name, uploaded_file.size)
    # 当前实例的去重 key
    last_state_key = f"last_uploaded_{instance.id}"
    # 跳过重复上传
    if st.session_state.get(last_state_key) != last_key:
        # 捕获上传异常
        try:
            # 保存文件并获取信息
            file_info = file_uploader.save_file(uploaded_file)
            # 将文件信息添加到实例
            instance.add_file(file_info["filename"], file_info["saved_name"], file_info["size"], file_info["type"])

            # 立刻在消息框输出上传信息
            upload_note = f"用户上传了{file_info['filename']} 文件，文件上传路径：{file_info.get('path', '未知')}"
            message_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # 添加消息到实例历史
            instance.add_message(instance,
                                  upload_note,
                                    "正在解析论文，请稍候...",
                                      "file",
                                        message_time
                                        )
            # 界面显示解析论文
            if display_container is not None:
                with display_container:
                    with st.chat_message("user"):
                        st.markdown(upload_note)
                    with st.chat_message("assistant"):
                        st.markdown("正在解析论文，请稍候...")

            # 将文件上传，进行向量处理，并且调用LLM进行解析论文首页 的title 与 summary 构建元数据存储在redis中
            ai_upload_response = ai_service.process_file_upload(
                                                            file_info["filename"],
                                                           file_info["path"],
                                                         instance.id
                                                                        )
            
            if isinstance(ai_upload_response, dict) and ai_upload_response.get("error"):
                st.error(ai_upload_response["error"])
            else:
                meta = ai_upload_response.get("meta") if isinstance(ai_upload_response, dict) else None
                done_message = (
                    f"{(meta or {}).get('paper_title', file_info['filename'])}文件上传完成并已向量化，"
                    f"上传路径：{(meta or {}).get('path', file_info.get('path', '未知'))}，"
                    f"文件名：{(meta or {}).get('file_name', file_info['filename'])}"
                )
                message_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                history_client = chat_message_history.get_chat_message_history_client(instance.id)
                history_client.add_message(
                    AIMessage(
                        content=done_message,
                        additional_kwargs={"message_type": "file", "message_time": message_time},
                    )
                )
                if display_container is not None:
                    with display_container:
                        with st.chat_message("assistant"):
                            st.markdown(done_message)
                if meta and meta.get("paper_id") and selected_paper_key:
                    st.session_state[selected_paper_key] = meta.get("paper_id")
            # 记录最近一次上传
            st.session_state[last_state_key] = last_key
        # 处理上传错误
        except Exception as exc:
            # 显示上传失败信息
            st.error(f"上传失败: {exc}")


def _handle_paper_source(instance: ChatInstance, source_text: str, triggered: bool, display_container=None) -> Optional[str]:
    """
    处理论文来源导入（URL 或 arXiv ID）。并进行下载与向量化处理、解析元数据存在redis中。
        参数：
            instance (ChatInstance): 当前聊天实例对象。
            source_text (str): 论文来源（PDF URL 或 arXiv ID）。
            triggered (bool): 是否触发导入。
            display_container (Optional[st.container]): 用于显示导入信息的容器。
        返回：
            Optional[str]: 导入成功时返回论文ID，失败时返回None。
    """

    # 触发导入
    if not triggered:
        return None
    # 来源文件 去空格
    source = (source_text or "").strip()
    # 判断是否输入的来源文件
    if not source:
        st.error("请输入论文来源（PDF URL 或 arXiv ID）。")
        return None
    # 获取最后导入的来源文件状态key
    last_state_key = f"last_source_{instance.id}"
    # 判断是否重复导入
    if st.session_state.get(last_state_key) == source:
        return None
    # 将来源文件 进行处理，获取文件url 文件名，保存路径等信息
    preview = ai_service.prepare_paper_source(source, instance.id)
    # 判断是否处理失败
    if isinstance(preview, dict) and preview.get("error"):
        st.error(preview["error"])
        return None
    # 获取处理后的文件信息
    file_info = preview.get("file_info", {}) if isinstance(preview, dict) else {}
    # 构建上传提示信息 ， 时间 ，并将其添加消息中
    upload_note = f"用户上传url/arxiv :{source} ,文件上传路径：{file_info.get('path', '未知')}"
    message_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # 将上传提示信息 添加到消息中 ， 并显示在界面上
    instance.add_message(instance, upload_note, "正在下载并解析论文，请稍候...", "file", message_time)
    # 在UI界面上显示上传提示信息
    if display_container is not None:
        with display_container:
            with st.chat_message("user"):
                st.markdown(upload_note)
            with st.chat_message("assistant"):
                st.markdown("正在下载并解析论文，请稍候...")
    # 将来源文件进行下载与向量化处理，并进行解析元数据存在redis中
    result = ai_service.process_paper_source(source, instance.id)
    # 判断是否处理失败
    if isinstance(result, dict) and result.get("error"):
        st.error(result["error"])
        return None
    # 构建文件下载与向量化存储的提示信息 并将消息存储在历史消息中
    meta = result.get("meta", {}) if isinstance(result, dict) else {}
    done_message = (
        f"{meta.get('paper_title', meta.get('file_name', '论文'))}论文文件已完成上传并进行向量存储，"
        f"上传路径：{meta.get('path', '未知')}，文件名：{meta.get('file_name', '未知')}"
    )
    message_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    history_client = chat_message_history.get_chat_message_history_client(instance.id)
    history_client.add_message(
        AIMessage(
            content=done_message,
            additional_kwargs={"message_type": "file", "message_time": message_time},
        )
    )
    # 在UI界面上显示文件下载与向量化存储的提示信息
    if display_container is not None:
        with display_container:
            with st.chat_message("assistant"):
                st.markdown(done_message)
    # 将最近一次导入的来源文件状态key 更新为当前导入的来源文件
    st.session_state[last_state_key] = source
    # 返回论文id 用于后续的查询
    return meta.get("paper_id")


# 渲染选中实例的历史消息
def _render_messages(instance_id: str) -> None:
    """
    ### 功能：
        渲染选中的实例的历史消息，包含用户与助手的交互记录。\n
        如果实例不存在历史消息，则显示欢迎语。
    """


    # 尝试从 Redis 加载聊天历史
    try:
        # 获取对应实例的历史客户端
        history_client = chat_message_history.get_chat_message_history_client(instance_id)
        # 拉取历史消息列表
        messages = history_client.messages
    # 捕获加载错误
    except Exception as exc:
        # 显示加载失败错误
        st.error(f"streamlit_app.py/_render_messages  加载聊天记录失败: {exc}")
        # 直接返回终止渲染
        return
    
    # 没有消息时显示欢迎语
    if not messages:
        # 以助手身份显示欢迎信息
        with st.chat_message("assistant"):
            # 渲染欢迎文本
            st.markdown("你好！我是一个论文智能助手，你可以上传/导入论文向我咨询论文相关问题。")
        # 结束渲染
        return
    
    # 将历史消息进行渲染
    for msg in messages:
        # 根据消息类型决定角色 如果时human则为user 否则为assistant
        role = "user" if msg.type == "human" else "assistant"
        # 使用消息角色渲染气泡
        with st.chat_message(role):
            # 显示消息内容
            st.markdown(msg.content)
            # 初始化消息时间
            message_time = None
            # 检查是否存在扩展字段
            if hasattr(msg, "additional_kwargs"):
                # 从扩展字段取出时间
                message_time = msg.additional_kwargs.get("message_time")
            # 若有时间则显示
            if message_time:
                # 显示时间戳
                st.caption(message_time)


# 主入口函数
def main():
    # 配置页面标题与布局
    st.set_page_config(page_title="AI智能论文助手", layout="wide")


    # 加载实例列表
    instances: list[ChatInstance] = _load_instances()

    # 确保当前实例有效
    current_id = _ensure_current_instance(instances)

    # 无实例时提示并返回
    if current_id is None:
        # 显示错误提示
        st.error("streamlit-ai-paper/main 没有可用的聊天实例。")
        # 提前结束程序
        return
    
    # 渲染侧边栏（新建聊天按钮，聊天实例单选列表）并获取选中 ID
    selected_id = _render_sidebar(instances)

    # 重新加载实例确保包含新建实例
    instances = _load_instances()


    # 使用最新的当前实例 ID 修正选择
    selected_id = st.session_state.get("current_instance_id", selected_id)
    # 构建实例映射
    instance_map = {inst.id: inst for inst in instances}
    # 获取当前实例对象
    current_instance = instance_map.get(selected_id)
    # 未找到实例时提示并返回
    if current_instance is None:
        # 显示错误信息
        st.error("未找到选中的聊天实例。")
        # 提前结束
        return
    
    # 显示当前实例标题
    st.title(current_instance.name+  f" ({current_instance.id[:6]})"+' 实例智能助手')
    # 隐藏上传提示文案与灰色框，仅保留上传按钮
    st.markdown(
        """
        <style>
        div[data-testid="stFileUploaderDropzone"] {
            padding: 0 !important;
            border: none !important;
            background: transparent !important;
            box-shadow: none !important;
            min-height: 0 !important;
            height: auto !important;
            display: flex !important;
            align-items: center !important;
        }
        div[data-testid="stFileUploaderDropzone"] > div {
            padding: 0 !important;
            border: none !important;
            background: transparent !important;
        }
        div[data-testid="stFileUploaderDropzoneInstructions"],
        div[data-testid="stFileUploaderDropzoneHint"],
        div[data-testid="stFileUploaderDropzoneText"] {
            display: none !important;
        }
        div[data-testid="stFileUploader"] {
            margin-top: 0 !important;
        }
        div[data-testid="stFileUploaderDropzone"] button {
            margin: 0 !important;
            height: 2.4rem !important;
            line-height: 2.4rem !important;
            padding-top: 0 !important;
            padding-bottom: 0 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


    # 渲染当前实例历史消息（固定高度滚动）
    chat_container = st.container(height=450)

    with chat_container:
        _render_messages(selected_id)
        # 预留新消息显示区域（确保出现在输入框上方）
        new_message_container = st.container()

    # 会话状态键：选中的论文 ID（每个实例独立）
    selected_paper_key = f"selected_paper_{current_instance.id}"

    # 构建输入区：输入框 + 发送按钮 + 右侧上传按钮
    input_container = st.container()

    with input_container:
        # 三列布局：输入框、发送、上传
        col_prompt, col_send, col_upload = st.columns([8.5, 1, 0.5])
        # 为每个实例使用独立的输入 key
        prompt_key = f"user_prompt_{current_instance.id}"
        # 发送触发器 key
        send_trigger_key = f"send_trigger_{current_instance.id}"

        # 发送回调（按钮/回车共用）
        def _trigger_send(instance_id: str) -> None:
            # 从会话状态获取用户输入key
            prompt_state_key = f"user_prompt_{instance_id}"
            # 从会话状态获取用户输入文本key
            send_payload_key = f"send_payload_{instance_id}" 
            text = st.session_state.get(prompt_state_key, "")
            st.session_state[send_payload_key] = text
            st.session_state[f"send_trigger_{instance_id}"] = True
            st.session_state[prompt_state_key] = ""

        # 渲染输入框
        col_prompt.text_input(
            "输入消息",
            key=prompt_key,
            label_visibility="collapsed",
            placeholder="请输入你的问题",
            on_change=_trigger_send,
            args=(current_instance.id,),
        )

        # 渲染发送按钮
        col_send.button(
            "发送",
            key=f"send_{current_instance.id}",
            on_click=_trigger_send,
            args=(current_instance.id,),
        )

        # 渲染上传按钮（位于输入框右侧）
        uploaded_file = col_upload.file_uploader(
            "上传论文",
            key=f"file_uploader_{current_instance.id}",
            label_visibility="collapsed",
        )

    # 处理文件上传（立刻解析）
    _handle_file_upload(current_instance,  # 当前的聊天实例
                        uploaded_file, # 上传文件按钮
                         new_message_container, # 新消息显示容器
                           selected_paper_key # 会话状态键：选中的论文 ID（每个实例独立）
                           )
    
    # 论文来源输入（URL 或 arXiv ID）放在输入框下方
    source_container = st.container()
    with source_container:
        col_source, col_source_btn = st.columns([8, 1])
        source_key = f"paper_source_{current_instance.id}"
        source_trigger_key = f"source_trigger_{current_instance.id}"
        source_payload_key = f"source_payload_{current_instance.id}"

        def _trigger_source_import(instance_id: str) -> None:
            input_key = f"paper_source_{instance_id}"
            payload_key = f"source_payload_{instance_id}"
            text = st.session_state.get(input_key, "")
            st.session_state[payload_key] = text
            st.session_state[f"source_trigger_{instance_id}"] = True
            st.session_state[input_key] = ""

        col_source.text_input(
            "论文来源",
            key=source_key,
            label_visibility="collapsed",
            placeholder="输入 arXiv ID 或 PDF URL",
        )
        col_source_btn.button(
            "导入",
            key=f"import_source_{current_instance.id}",
            on_click=_trigger_source_import,
            args=(current_instance.id,),
        )
    selected_paper_key = f"selected_paper_{current_instance.id}"
    if st.session_state.get(source_trigger_key):
        st.session_state[source_trigger_key] = False
        source_text = st.session_state.get(source_payload_key, "")
        st.session_state[source_payload_key] = ""
        new_paper_id = _handle_paper_source(current_instance, source_text, True, new_message_container)
        if new_paper_id:
            st.session_state[selected_paper_key] = new_paper_id

    # 论文选择列表（位于来源输入下方）
    papers = redis_service.list_paper_metadata(current_instance.id)
    if papers:
        # 排序：按创建时间
        try:
            papers.sort(key=lambda p: p.get("created_at") or "")
        except Exception:
            pass
        paper_ids = [p.get("paper_id") for p in papers if p.get("paper_id")]
        paper_label_map = {}
        for p in papers:
            pid = p.get("paper_id")
            if not pid:
                continue
            title = p.get("paper_title") or p.get("file_name") or pid[:6]
            pages = p.get("page_count")
            if pages:
                paper_label_map[pid] = f"{title} (页数 {pages})"
            else:
                paper_label_map[pid] = title
        if paper_ids:
            if st.session_state.get(selected_paper_key) not in paper_ids:
                st.session_state[selected_paper_key] = paper_ids[-1]
            st.radio(
                "选择论文",
                options=paper_ids,
                key=selected_paper_key,
                format_func=lambda pid: paper_label_map.get(pid, pid),
            )
    # 若触发发送则处理
    if st.session_state.get(send_trigger_key):
        # 重置触发器
        st.session_state[send_trigger_key] = False
        send_payload_key = f"send_payload_{current_instance.id}"
        payload = st.session_state.get(send_payload_key, "")
        st.session_state[send_payload_key] = ""
        # 有效输入才发送
        if payload and payload.strip():
            # 显示用户消息气泡
            with new_message_container:
                with st.chat_message("user"):
                    # 渲染用户输入文本
                    st.markdown(payload)
            # 初始化响应变量
            response = None
            # 显示助手消息气泡
            with new_message_container:
                with st.chat_message("assistant"):
                    # 显示思考中的加载动画
                    with st.spinner("Thinking..."):
                        # 调用 AI 服务获取响应
                        try:
                            # 获取询问的论文id
                            selected_paper_id = st.session_state.get(selected_paper_key)
                            # 判断是否支持流式输出
                            if hasattr(ai_service, "get_response_stream"):
                                # 流式输出并获取完整响应
                                response = st.write_stream(
                                    ai_service.get_response_stream(payload, selected_id, selected_paper_id)
                                )
                            # 不支持流式则使用普通输出
                            else:
                                # 获取 AI 回复
                                response = ai_service.get_response(payload, selected_id, selected_paper_id)
                                # 渲染 AI 回复
                                st.markdown(response)
                        # 捕获 AI 错误
                        except Exception as exc:
                            # 显示错误信息
                            st.error(f"AI 错误: {exc}")
            # 若响应存在则写入历史
            if response is not None:
                # 获取当前时间戳
                message_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                # 获取当前实例对象
                instance = instance_map.get(selected_id)
                # 实例缺失时提示并返回
                if instance is None:
                    # 显示错误提示
                    st.error("未找到选中的聊天实例。")
                    # 提前结束
                    return
                # 写入历史消息记录
                instance.add_message(instance, payload, response, "text", message_time)


# 以脚本方式运行时执行 main
if __name__ == "__main__":
    # 调用主函数启动应用
    main()
