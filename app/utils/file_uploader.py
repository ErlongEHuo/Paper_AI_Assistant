import os
import uuid
from typing import Any, Dict

from config.settings import settings


class FileUploader:
    """
    文件保存工具
    """ 

    def __init__(self):
        self.upload_dir = settings.UPLOAD_DIR

    def _get_attr(self, obj: Any, *names: str, default: Any = None) -> Any:
        """ 
        循环遍历传递的参数names,判断obj是否有该属性，有则返回该属性值，否则返回默认值
            参数：
                obj: 要检查属性的对象
                names: 要检查的属性名列表
                default: 默认值
            返回：
                第一个存在的属性值，或默认值
        """
        for name in names:
            if hasattr(obj, name):
                return getattr(obj, name)
        return default

    def _read_bytes(self, file_obj: Any) -> bytes:
        """
        读取文件对象的字节内容
            参数：
                file_obj: 要读取的文件对象
            返回：
                bytes 文件的字节内容
        """
        # 情况1: 对象有 getvalue() 方法（如 BytesIO）
        if hasattr(file_obj, "getvalue"):
            return file_obj.getvalue()
        # 情况2: 对象有 read() 方法（如文件句柄）
        if hasattr(file_obj, "read"):
            data = file_obj.read()
            if isinstance(data, bytes):
                return data
        # 情况3: 对象有 file.read() 方法（如 Streamlit 的 UploadedFile）
        if hasattr(file_obj, "file") and hasattr(file_obj.file, "read"):
            return file_obj.file.read()
        
        # 以上情况都不满足，抛出异常
        raise ValueError("app/utils/file_uploader.py: _read_bytes: 不支持文件对象")

    

    def save_file(self, file_obj: Any) -> Dict[str, Any]:
        """
        保存文件到指定目录
            参数：
                file_obj: 要保存的文件对象
            返回：
                Dict[str, Any] 包含文件名、保存名、大小、类型和路径的元数据
        """

        # 步骤1: 检查文件对象是否为 None
        if file_obj is None:
            # 主动抛出异常，提示用户没有上传文件
            raise ValueError("app/utils/file_uploader.py: 没有文件上传")

        # 步骤2: 提取文件名和类型
        filename = self._get_attr(file_obj, "name", "filename")
        content_type = self._get_attr(
            file_obj,
            "type",
            "content_type",
            default="application/octet-stream",
        )

        file_bytes = self._read_bytes(file_obj)
        # 获取文件大小
        file_size = len(file_bytes)

        # 步骤3: 验证文件类型和大小
        if content_type not in settings.ALLOWED_FILE_TYPES:
            raise ValueError("app/utils/file_uploader.py: save_file: 不支持文件类型")
        if file_size > settings.MAX_FILE_SIZE:
            raise ValueError("app/utils/file_uploader.py: save_file: 文件大小超过限制")

        # 提取文件扩展名（如 ".pdf"）
        file_extension = os.path.splitext(filename)[1]
        # 使用 UUID 生成唯一文件名，避免文件名冲突
        saved_filename = f"{uuid.uuid4()}{file_extension}"
        # 构建完整的文件保存路径
        file_path = self.upload_dir / saved_filename

        with open(file_path, "wb") as buffer:
            buffer.write(file_bytes)

        return {
            "filename": filename,# 原始文件名
            "saved_name": saved_filename,# 保存后的文件名（UUID）
            "size": file_size, # 文件大小（字节）
            "type": content_type,  # MIME 类型
            "path": str(file_path),# 完整保存路径
        }


file_uploader = FileUploader()
