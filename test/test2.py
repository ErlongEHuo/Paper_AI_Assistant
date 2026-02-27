


# def _detect_file_format( file_path: str) -> str:
#     """
#     检测文件实际格式（根据文件头判断）
#         参数:
#             file_path: 文件路径
#         返回:
#             str: 文件格式 ('pdf', 'caj', 'text', 'html', 'unknown')
#     """
#     try:
#         print('开始pdf')
#         with open(file_path, 'rb') as f:
#             header = f.read(100)  # 读取前100字节
            
#         # PDF 文件: 以 %PDF- 开头
#         if header[:5] == b'%PDF-':
#             return 'pdf'
        
#         print('开始html')
#         # # CAJ 文件: 以特定字节开头
#         # if header[:4] in [b'\xca\x6a\x6c\x00', b'\xca\x6a\x6c\x01']:
#         #     return 'caj'
        
#         # HTML 文件: 包含 <!DOCTYPE 或 <html
#         header_str = header.decode('utf-8', errors='ignore').lower()
#         if '<!doctype html' in header_str or '<html' in header_str:
#             return 'html'
#         print('开始text')
#         # 尝试作为文本处理
#         try:
#             with open(file_path, 'r', encoding='utf-8') as f:
#                 f.read(1000)
#             return 'text'
#         except:
#             try:
#                 with open(file_path, 'r', encoding='gbk') as f:
#                     f.read(500)
#                 return 'text'
#             except:
#                 return 'unknown'
            
#     except Exception:
#         return 'unknown' 


if __name__ == "__main__": 
    # file_path = r"E:\代码\Paper_AI_Assistant\database\download\47c15e83-46d5-4c37-9821-90dd73dd7769.pdf"
    # file_path=r'E:\代码\Paper_AI_Assistant\database\download\0758238a-b826-4605-90ff-b33a55ef196a.pdf'
    file_path =r'C:/Users/HEL/Desktop/基于大数据的转底炉工艺智能化应用探讨_郑君.pdf'
    
    # file_format = _detect_file_format(file_path) 
    # print(file_format)

    # with open(file_path, 'r' ,encoding='ANSI') as f:
    #         text = f.read(1000)
    #         print(text)
        # return 'text'
    
    # with open(file_path, 'rb') as f:
    #     header = f.read(100)  # 读取前100字节
    #     print(header)
    #     print( header[:5])

    # with open(file_path, 'rb') as f:
    #     header = f.read(100)
    
    # print(header)
    # # PDF 文件
    # if header[:5] == b'%PDF-': 
    #     print('pdf')
    
    # # CAJ 文件（启用此检测）
    # if header[:4] in [b'\xca\x6a\x6c\x00', b'\xca\x6a\x6c\x01']: 
    #     print('caj')

    # import PyPDF2
    # with open(file_path, "rb") as f:
    #     print(f"PDF 文件: {file_path}")
    #     reader = PyPDF2.PdfReader(f)
    #     print(f"页数: {len(reader)}")
    #     for page in reader.pages:
    #         text = page.extract_text()
    #         print(text)

    import pdfplumber

    with pdfplumber.open(file_path) as pdf:
        print('开始')
        for page in pdf.pages:
            text = page.extract_text()
            print(text)