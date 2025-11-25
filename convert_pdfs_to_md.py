import os
from pathlib import Path
import fitz  # PyMuPDF
import time

def convert_all_pdfs_to_text(pdf_source_folder: Path, text_output_folder: Path):
    """
    递归查找 'pdf_source_folder' 中的所有 .pdf 文件,
    提取它们的纯文本内容,并保存到 'text_output_folder'。
    
    为了与你现有的 'mineru' 工作流兼容,
    它会为每个PDF创建一个 *子文件夹* 来存放 .md 文件。
    """
    
    print(f"正在 {pdf_source_folder} 中搜索 PDF 文件...")
    
    pdf_files = list(pdf_source_folder.glob("**/*.pdf"))
    
    if not pdf_files:
        print("未找到任何 PDF 文件。请检查 'pdf_source_folder' 路径。")
        return

    print(f"找到 {len(pdf_files)} 个 PDF 文件。开始转换...")
    
    text_output_folder.mkdir(exist_ok=True)
    
    for pdf_path in pdf_files:
        start_time = time.time()
        output_subfolder_name = pdf_path.stem + "_output"
        output_subfolder_path = text_output_folder / output_subfolder_name
        output_subfolder_path.mkdir(exist_ok=True)
        
        output_md_path = output_subfolder_path / "content.md"
        
    
        if output_md_path.exists():
            print(f"文件 {output_md_path.name} 已存在，跳过 {pdf_path.name}")
            continue
            
        print(f"\n--- 正在处理: {pdf_path.name} ---")
        
        try:
            doc = fitz.open(pdf_path)
            all_text = []
            print(f"  共 {doc.page_count} 页...")
            
            for page_num in range(doc.page_count):
                page = doc.load_page(page_num)
                all_text.append(page.get_text("text"))
            
            doc.close()

            # 将所有页面的文本合并并写入 .md 文件
            final_text = "\n\n".join(all_text)
            output_md_path.write_text(final_text, encoding='utf-8')
            
            end_time = time.time()
            print(f"  成功！文本已保存到: {output_md_path}") # 更新了打印消息
            print(f"  耗时: {end_time - start_time:.2f} 秒")
            
        except Exception as e:
            print(f"  处理文件 {pdf_path.name} 时发生错误: {e}")
            try:
                doc.close()
            except:
                pass

    print("\n--- 所有 PDF 处理完毕！ ---")


def run_convert():
    script_path = Path(__file__).resolve()
    project_root = script_path.parent

    pdf_source_folder = project_root / "papers"
    text_output_folder = project_root / "new_papers_info"

    if not pdf_source_folder.exists():
        print(f"错误：未找到PDF源文件夹: {pdf_source_folder}")
        print("请在项目根目录创建 'papers_pdf_source' 文件夹，并把你所有的PDF论文放进去。")
    else:
        convert_all_pdfs_to_text(pdf_source_folder, text_output_folder)


if __name__ == "__main__":
    run_convert()