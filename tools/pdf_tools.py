import logging
from pathlib import Path
import time

try:
    from typing import Annotated, Optional
except ImportError:
    from typing_extensions import Annotated, Optional

from langchain_core.tools import tool
from api.monitor import monitor
from api.context import get_session_context
from utils.path_utils import resolve_path


@tool
def convert_md_to_pdf(
        md_filename: Annotated[str, "要转换的Markdown文档路径（包含.md后缀）"],
        pdf_filename: Annotated[Optional[str], "输出的PDF文件路径（可选，默认与源文件同名）"] = None
) -> str:
    """
    读取已生成的Markdown文档（.md），并将其转换为PDF文件。
    核心优化：基于Path对象处理路径，跨平台兼容；完善资源释放和异常处理。
    """
    monitor.report_tool("Markdown转PDF工具")

    # ====================== 1. 路径预处理（基于Path） ======================
    # 补全md后缀 + 解析安全路径
    md_path = Path(md_filename)
    if md_path.suffix.lower() != '.md':
        md_path = md_path.with_suffix('.md')

    # 解析会话目录下的绝对路径
    session_dir = get_session_context()
    md_abs_path = Path(resolve_path(str(md_path), session_dir))

    # ====================== 2. 检查源文件是否存在（含等待逻辑） ======================
    if not md_abs_path.exists():
        logging.warning(f"源文件不存在，等待5秒重试：{md_abs_path}")
        for _ in range(5):
            time.sleep(1)
            if md_abs_path.exists():
                break
        else:
            return f"错误：找不到源文件 '{md_abs_path}'。请确保文件已生成。"

    # ====================== 3. 处理PDF输出路径 ======================
    if pdf_filename is None:
        # 默认：替换md后缀为pdf
        pdf_abs_path = md_abs_path.with_suffix('.pdf')
    else:
        # 自定义路径：补全pdf后缀 + 解析安全路径
        pdf_path = Path(pdf_filename)
        if pdf_path.suffix.lower() != '.pdf':
            pdf_path = pdf_path.with_suffix('.pdf')
        pdf_abs_path = Path(resolve_path(str(pdf_path), session_dir))

    # ====================== 4. 检查依赖 ======================
    try:
        import markdown
        import win32com.client
        import pythoncom
    except ImportError as e:
        return f"转换失败：缺少必要库 → {str(e)}。请执行：pip install markdown pywin32"

    # ====================== 5. MD转HTML ======================
    temp_html_path = md_abs_path.with_suffix('.temp.html')
    word_app = None  # 初始化Word对象，方便finally中释放

    try:
        # 读取MD内容（UTF-8编码，兼容中文）
        with open(md_abs_path, 'r', encoding='utf-8') as f:
            md_content = f.read()

        # 转换为带样式的HTML
        html_body = markdown.markdown(md_content, extensions=['tables', 'fenced_code'])
        html_content = f"""
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: "Microsoft YaHei", "SimHei", sans-serif; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid black; padding: 8px; }}
                pre {{ background-color: #f5f5f5; padding: 10px; border-radius: 4px; }}
                code {{ font-family: "Consolas", "Monaco", monospace; }}
            </style>
        </head>
        <body>
            {html_body}
        </body>
        </html>
        """

        # 保存临时HTML文件（确保父目录存在）
        temp_html_path.parent.mkdir(parents=True, exist_ok=True)
        with open(temp_html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        # ====================== 6. HTML转PDF（调用Word COM） ======================
        pythoncom.CoInitialize()
        # 创建Word应用对象（不可见模式）
        word_app = win32com.client.Dispatch('Word.Application')
        word_app.Visible = False
        word_app.DisplayAlerts = False  # 关闭弹窗提示

        # 打开HTML文件
        doc = word_app.Documents.Open(str(temp_html_path))

        # 保存为PDF（wdFormatPDF = 17）
        doc.SaveAs(str(pdf_abs_path), FileFormat=17)

        # 关闭文档（不保存更改）
        doc.Close(SaveChanges=0)

        # ====================== 7. 验证PDF生成结果 ======================
        if pdf_abs_path.exists():
            return f"成功将 '{md_abs_path}' 转换为 '{pdf_abs_path}' (使用 Word 引擎)。"
        else:
            return f"转换流程完成，但未找到生成的PDF文件：{pdf_abs_path}"

    except Exception as e:
        logging.error(f"PDF转换失败：{str(e)}", exc_info=True)
        return f"转换PDF失败：{str(e)}"

    finally:
        # ====================== 8. 资源兜底释放 ======================
        # 关闭Word应用
        if word_app is not None:
            try:
                word_app.Quit()
            except:
                pass

        # 清理临时HTML文件（容错处理）
        try:
            if temp_html_path.exists():
                temp_html_path.unlink()
                logging.info(f"临时文件已清理：{temp_html_path}")
        except Exception as e:
            logging.warning(f"清理临时文件失败：{str(e)}")

        # 释放COM资源
        try:
            pythoncom.CoUninitialize()
        except:
            pass


# ====================== 测试入口（可选） ======================
if __name__ == '__main__':
    # 1. 固定 session_dir（你要的赋值）
    def get_session_context():
        return "./test_session_123"

    md_path = "sub_dir/测试文件.md"
    pdf_path = "sub_dir/测试文件.pdf"

    # 测试调用
    result = convert_md_to_pdf.invoke({
        "md_filename": md_path,
        "pdf_filename": pdf_path
    })
    print(result)