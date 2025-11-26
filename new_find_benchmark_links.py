import os
import json
import re  # 导入正则表达式库
from openai import OpenAI
import pandas as pd
from pathlib import Path
import time
from typing import Set, List, Dict, Any

# --- 1. 配置 (已改进) ---
# 最佳实践：从环境变量读取API Key，而不是硬编码。
# 请在运行脚本前在终端设置环境变量：
# (PowerShell): $env:DEEPSEEK_API_KEY="sk-..."
# (CMD): set DEEPSEEK_API_KEY=sk-...
# (Linux/macOS): export DEEPSEEK_API_KEY="sk-..."
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
if not DEEPSEEK_API_KEY:
    raise ValueError("错误：请设置 'DEEPSEEK_API_KEY' 环境变量。")

client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com"
)


# --- 2. 新增函数 (减少Token) ---
def preprocess_text(full_text: str) -> str:
    """
    在将文本发送给LLM之前对其进行预处理。
    1. 删除参考文献、附录等噪音部分。
    2. 截取核心部分（例如前5000字符）以节省Token。
    """
    # 定义停止词/章节标题，匹配到这些词时，后续内容将被截断
    # 使用正则表达式，(?im) 标志表示忽略大小写(i)和多行模式(m)
    # \s* 表示匹配任意空白符（包括换行）
    stop_patterns = [
        r"^\s*References\s*$",
        r"^\s*Bibliography\s*$",
        r"^\s*Acknowledgements\s*$",
        r"^\s*Acknowledgments\s*$",
        r"^\s*Appendix\s*$",
        r"^\s*附录\s*$",
        r"^\s*参考文献\s*$"
    ]

    # 将所有模式合并为一个正则表达式
    # (?:...) 是一个非捕获组
    stop_regex = re.compile(r"(\n\s*(?:" + "|".join(stop_patterns) + r")\s*\n)", re.IGNORECASE | re.MULTILINE)

    # 按第一个匹配到的停止词分割文本，只保留[0]（即停止词之前的内容）
    cleaned_text = stop_regex.split(full_text, maxsplit=1)[0]

    # 截取前16000个字符，这通常足以覆盖摘要、引言和方法部分
    # 16000字符大约对应 3000-4000 个Token，是一个合理的范围
    snippet = cleaned_text[:16000]  # 这里使用16000字符以适应更长的文本需求

    if len(snippet) < len(full_text) and len(snippet) > 0:
        print(f"文本已预处理：从 {len(full_text)} 字符缩减到 {len(snippet)} 字符 (已移除参考文献等)。")
    elif len(snippet) == 0 and len(full_text) > 0:
        print(f"警告：预处理后文本为空！可能切分逻辑有误。将使用原始文本的前5000字符。")
        snippet = full_text[:5000]  # Fallback
    else:
        print(f"文本已预处理：保留原文 {len(snippet)} 字符。")

    return snippet


# --- 3. 核心函数 (更丰富维度 + 溯源) ---
def build_benchmark_finder_prompt(text_content: str) -> tuple[str, str]:
    """
    构建一个精确的提示，指导LLM提取 *详细* 信息并 *附带原文位置*。
    增加了针对“数据集原始论文 vs 应用论文”的辨析逻辑。
    """
    system_prompt = """
    你是一位极其细致的科研助理，专注于从学术论文中提取AI代码评测基准的元数据。

    ### 🚨 核心原则：区分“数据集原生属性”与“模型实验设置” (CRITICAL)
    你的首要任务是判断：**这篇论文是“提出/发布”了这个数据集，还是仅仅“使用”它？**

    1. **如果是原始发布论文 (Original Paper)**：
       - 提取该数据集的所有定义特征。

    2. **如果是应用/评测论文 (Evaluation Paper)**：
       - 这种情况极其容易出错！**严禁**将论文中**模型的局限性**或**特定实验的设置**误认为是数据集的属性。
       - **错误示例**：论文说 "We evaluated our model SteloCoder on the Python subset of XLCoST"（我们在XLCoST的Python子集上测试了模型）。
         - **错误提取**：language: "Python" (这是实验设置，不是数据集全貌)。
         - **正确行为**：寻找文中是否有描述数据集完整情况的句子（如 "XLCoST covers 7 languages..."）。如果文中完全未提及数据集的全貌，仅提到了实验子集，请在 value 中明确备注 **"文中仅提及实验子集(Python)，未描述完整数据集"**，或者将该字段留为 null，不要编造。

    你的任务是：针对提供的论文文本，找出其中描述的 *每一个* 字段，并同时提供：
    1. 提取的 **值 (value)**。
    2. 支持该值的 **原文引述 (source_quote)**，即你从文本中看到该信息的依据。

    严格按照指定的嵌套JSON格式返回。如果某个字段的信息在文中 *明确* 找不到，请将 "value" 和 "source_quote" 均设为 null。

    **需要提取的JSON结构:**
    {
      "benchmark_name": {
        "value": "评测基准的官方名称 (例如 'HumanEval', 'MBPP')",
        "source_quote": "原文中定义或提到该名称的句子 (例如 'We introduce HumanEval, a new evaluation set...')"
      },
      "is_original_proposal": {
        "value": "【布尔值或说明】这篇论文是否是该数据集的原始发布论文？(例如 'Yes' 或 'No, 本文是使用该数据集进行评测')",
        "source_quote": "原文中表明身份的句子 (例如 'We propose a new dataset...' 或 'We evaluate on XLCoST...')"
      },
      "dataset_url": {
        "value": "官网链接或代码仓库URL (例如 'https://github.com/openai/human-eval')",
        "source_quote": "原文中提供该URL的句子 (例如 'The full dataset is available at https://github.com/...')"
      },
      "task_description": {
        "value": "【请用中文描述】该评测基准旨在解决的主要任务（指数据集本身设计的用途，而非本文模型做的任务）",
        "source_quote": "原文中描述其任务的句子 (例如 '...measure functional correctness for synthesizing programs from docstrings.')"
      },
      "dimension": {
        "value": "【请用中文描述】评测维度或关注点 (例如 '代码生成正确性', '多语言能力')",
        "source_quote": "原文中描述其评测维度的句子"
      },
      "evaluation_method": {
        "value": "【请用中文描述】评估方法 (例如 'pass@k', '执行单元测试', '代码BLEU分数')",
        "source_quote": "原文中描述其如何评估的句子 (例如 'We use the pass@k metric, where k=1, 10, 100.')"
      },
      "context_dependency": {
        "value": "【请用中文描述】上下文依赖范围 (例如 '单函数', '多文件项目')",
        "source_quote": "原文中描述其上下文需求的句子 (例如 'The problems are single-function...')"
      },
      "problem_domain": {
        "value": "【请用中文描述】问题所属专业领域 (例如 '算法', 'Web开发', '数据科学')",
        "source_quote": "原文中描述其问题类型的句子 (例如 '...tasks are algorithmic in nature...')"
      },
      "problem_difficulty": {
        "value": "【请用中文描述】任务难度 (例如 '入门级', '竞赛级', '工程级')",
        "source_quote": "原文中描述其难度的句子 (例如 '...consists of 974 entry-level tasks...')"
      },
      "language": {
        "value": "【请用中文描述】涉及的主要编程语言",
        "source_quote": "原文中提到语言的句子 (例如 'The dataset consists of 164 Python programming problems.')"
      },
      "data_size": {
        "value": "【请用中文描述】数据集规模描述",
        "source_quote": "原文中提到数据规模的句子 (例如 'It includes 974 entry-level tasks...')"
      },
      "source_type": {
        "value": "【请用中文描述】数据来源描述",
        "source_quote": "原文中描述数据来源的句子 (例如 'Tasks were constructed manually...')"
      },
      "last_updated": {
        "value": "最后更新或发布时间 (例如 '2021', '2024.09')",
        "source_quote": "原文中提到日期的句子 (例如 'The dataset was collected in September 2024...')"
      },
      "build_type": {
        "value": "【请用中文描述】构建类型 (例如 '官方自建', '社区贡献')",
        "source_quote": "原文中描述构建者身份的句子"
      },
      "contamination_status": {
        "value": "【请用中文描述】数据污染状态 (例如 '高污染风险', '抗污染设计')",
        "source_quote": "原文中讨论数据污染或新鲜度的句子 (例如 '...designed to be contamination-free...')"
      },
      "dataset_license": {
        "value": "【请用中文描述】数据集的许可证 (例如 'MIT', '仅供学术研究')",
        "source_quote": "原文中提及许可证的句子 (例如 'The dataset is released under the MIT License.')"
      },
      "task_granularity": { 
        "value": "【中文描述】(例如 '代码生成', '代码补全', '代码修复')", 
        "source_quote": "原文中描述任务粒度的句子 (例如 'This task involves generating the full function body...')" 
      },
      "evaluation_metrics": { 
        "value": "【中文描述】(例如 'pass@1, pass@10', 'CodeBLEU')", 
        "source_quote": "原文中提到具体评估指标的句子 (例如 'We evaluate functional correctness using pass@1.')" 
      },
      "input_modality": { 
        "value": "【中文描述】(例如 '自然语言', '代码与自然语言')", 
        "source_quote": "原文中描述输入类型的句子 (例如 'The input is a natural language docstring...')" 
      },
      "output_modality": { 
        "value": "【中文描述】(例如 '代码', '自然语言')", 
        "source_quote": "原文中描述期望输出的句子 (例如 'The model is expected to output a block of Python code.')" 
      },
      "task_io_type": { 
        "value": "【中文描述】任务的输入输出类型 (例如 '文本到代码', '代码到代码','代码到文本')", 
        "source_quote": "原文中描述输入输出模态的句子 (例如 '...synthesizing programs from docstrings.')" 
      },
      "execution_environment": { 
        "value": "【中文描述】(例如 '标准库', '需要特定依赖')", 
        "source_quote": "原文中描述执行环境的句子 (例如 'The generated code is executed in a sandboxed environment with no external libraries.')" 
      }
      "unique_features": {
        "value": "【请用中文描述】该基准的独特之处或额外信息 (即'额外列')",
        "source_quote": "原文中描述其特殊性的句子 (例如 'Unlike previous benchmarks, RMCBench focuses on malicious code generation.')"
      }
    }
    """
    user_prompt = f"**请分析以下论文文本，并严格按照JSON结构提取所有字段及其原文引述:**\n---\n{text_content}\n---"
    return system_prompt, user_prompt


# --- 4. 核心函数：调用API (保持不变) ---
def find_benchmark_info_in_text(text: str) -> dict:
    """
    使用 DeepSeek 模型从论文文本中查找代码评测基准详细信息。
    """
    if not text.strip():
        print("警告：输入的文本为空。")
        return {}

    system_prompt, user_prompt = build_benchmark_finder_prompt(text)

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",  # 确保你使用的是有权限且能力足够的模型
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0,  # 提取任务使用低温
            stream=False
        )
        response_content = response.choices[0].message.content
        cleaned_response = response_content.strip().replace('```json', '').replace('```', '').strip()
        if cleaned_response.startswith('"') and cleaned_response.endswith('"'):
            cleaned_response = cleaned_response[1:-1].replace('\\"', '"')

        extracted_json = json.loads(cleaned_response)

        # 检查最关键的字段
        if not extracted_json.get("benchmark_name") or not extracted_json.get("benchmark_name").get("value"):
            print("警告：未能从文本中明确提取到 benchmark_name 的值。")
        return extracted_json

    except json.JSONDecodeError as json_err:
        print(f"JSON解析错误: {json_err}")
        print("--- 原始模型输出 ---")
        print(response_content if 'response_content' in locals() else "N/A")
        print("--------------------")
        return {"error": "JSONDecodeError",
                "original_response": response_content if 'response_content' in locals() else "N/A"}
    except Exception as e:
        print(f"处理文本时发生API或其他错误: {e}")
        return {"error": str(e), "original_response": "API call failed"}


# --- 5. 新增函数 (加入原文位置：扁平化数据以便存入CSV) ---
def flatten_extracted_data(nested_data: dict, source_paper: str) -> dict:
    """
    将LLM返回的嵌套JSON扁平化，以便存入CSV。
    例如：{"benchmark_name": {"value": "...", "source_quote": "..."}}
    变为：{"benchmark_name": "...", "benchmark_name_quote": "..."}
    """
    flat_data = {"source_paper": source_paper}

    # 注意：LLM 返回的 true/false 在 JSON 中是布尔值
    is_original_item = nested_data.get("is_original_proposal", {})
    if isinstance(is_original_item, dict):
        flat_data["is_original_proposal"] = is_original_item.get("value")
        flat_data["is_original_proposal_quote"] = is_original_item.get("source_quote")
    else:
        flat_data["is_original_proposal"] = None
        flat_data["is_original_proposal_quote"] = None

    # 遍历所有在prompt中定义的键
    all_fields = [
        "benchmark_name", "is_original_proposal", "dataset_url", "task_description", "dimension",
        "evaluation_method", "context_dependency", "problem_domain",
        "problem_difficulty", "language", "data_size", "source_type",
        "last_updated", "build_type", "contamination_status",
        "dataset_license", "task_granularity", "evaluation_metrics", "input_modality",
        "output_modality", "task_io_type", "execution_environment", "unique_features"
    ]

    for field in all_fields:
        item = nested_data.get(field)

        if isinstance(item, dict):
            # 正常情况：提取 value 和 source_quote
            flat_data[field] = item.get("value")
            flat_data[f"{field}_quote"] = item.get("source_quote")
        else:
            # 异常情况：LLM可能返回了 null 或其他非字典结构
            flat_data[field] = item  # 可能是 null
            flat_data[f"{field}_quote"] = None

    # 检查是否有错误信息
    if "error" in nested_data:
        flat_data["error"] = nested_data.get("error")
        flat_data["original_response"] = nested_data.get("original_response")

    return flat_data


def load_existing_csv(csv_path: Path) -> (pd.DataFrame, Set[str]):
    """
    加载现有的原始CSV，返回DataFrame和已处理过的 'source_paper' 路径集合。
    """
    if not csv_path.exists():
        print(f"未找到现有CSV数据库：{csv_path}。将创建新文件。")
        return pd.DataFrame(), set()
    try:
        df = pd.read_csv(csv_path)
        if 'source_paper' not in df.columns:
            print("警告：现有CSV没有 'source_paper' 列，将重新处理所有文件。")
            return pd.DataFrame(), set()
        # 将路径规范化为 posix 格式 (/)，以便跨平台比较
        processed_paths = set(Path(p).as_posix() for p in df['source_paper'].astype(str))
        print(f"成功加载原始CSV，已包含 {len(df)} 条记录。")
        return df, processed_paths
    except pd.errors.EmptyDataError:
        print(f"警告：原始CSV文件 {csv_path} 为空。将创建新文件。")
        return pd.DataFrame(), set()
    except Exception as e:
        print(f"加载 {csv_path} 失败: {e}。将创建新文件。")
        return pd.DataFrame(), set()


def extract_benchmark():
    try:
        script_path = Path(__file__).resolve()
        project_root = script_path.parent
    except NameError:
        # 适应 .ipynb/.py 交互式环境
        project_root = Path.cwd()

    papers_folder = project_root / "new_papers_info"  # 现在指向正确的父文件夹
    results_folder = project_root / "results"
    results_folder.mkdir(exist_ok=True)

    # 定义输出文件名
    output_filename = results_folder / "benchmarks_database_1125.csv"

    df_existing, processed_paths = load_existing_csv(output_filename)
    print(f"已处理的文件: {len(processed_paths)} 个")
    print(f"正在文件夹 '{papers_folder}' 及其所有子文件夹中递归搜索 .md 文件...")
    # 查找 .md 文件
    input_files = list(papers_folder.glob("**/*.md"))

    if not input_files:
        print(f"错误：在 '{papers_folder}' 及其子文件夹中没有找到任何 .md 文件。")
        exit()

    # 过滤出需要处理的新文件
    new_files_to_process = []
    for file_path in input_files:
        # 将路径规范化为 posix 格式 (/)，以便与 set 中的路径比较
        relative_path_str = file_path.relative_to(papers_folder).as_posix()

        if file_path.is_file() and relative_path_str not in processed_paths:
            new_files_to_process.append((file_path, relative_path_str))

    if not new_files_to_process:
        print("没有找到需要提取的新文件。所有文件均已处理。")
        exit()  # 正常退出

    print(f"成功找到 {len(input_files)} 个总文件，其中 {len(new_files_to_process)} 个是新文件。准备开始处理...")

    new_benchmarks_flat = []  # 只存储新文件的结果

    # 只循环处理新文件
    for file_path, relative_path_str in new_files_to_process:

        print(f"\n--- 正在处理新文件: {relative_path_str} ---")
        try:
            full_text = file_path.read_text(encoding='utf-8')
            text_snippet = preprocess_text(full_text)
            nested_benchmark_info = find_benchmark_info_in_text(text_snippet)

            # 使用 relative_path_str 确保路径格式一致
            flat_benchmark_info = flatten_extracted_data(nested_benchmark_info, relative_path_str)

            # --- 新增过滤逻辑 ---
            is_original = flat_benchmark_info.get("is_original_proposal")

            # 严格模式：如果不确定或不是原始论文，则发出警告并不保存（或者保存但你知道它是脏数据）
            if is_original is False:
                print(f"⚠️ 跳过: {relative_path_str} 似乎不是数据集的原始出处 (is_original_proposal=False)。")
                print(f"   理由: {flat_benchmark_info.get('is_original_proposal_quote')}")
                continue  # 跳过当前循环，不添加到 new_benchmarks_flat

            # --------------------

            print("提取结果 (扁平化):", json.dumps(flat_benchmark_info, indent=2, ensure_ascii=False))

            if flat_benchmark_info.get("benchmark_name"):
                new_benchmarks_flat.append(flat_benchmark_info)
            elif "error" in flat_benchmark_info:
                print(f"处理文件 {relative_path_str} 时遇到错误，已跳过。")
            else:
                print(f"在文件 {relative_path_str} 中未提取到 benchmark_name，已跳过。")

        except Exception as e:
            print(f"读取或处理文件 '{relative_path_str}' 时发生未知错误: {e}")

        time.sleep(1)  # 增加速率限制，防止API过载

    # --- 保存结果（合并） ---
    if new_benchmarks_flat:
        df_new = pd.DataFrame(new_benchmarks_flat)

        # 合并旧数据和新数据
        df_combined = pd.concat([df_existing, df_new], ignore_index=True)

        print(f"\n✅ 成功提取 {len(new_benchmarks_flat)} 条新记录。")
    else:
        print("\n❌ 未能从新文件中成功提取任何数据。")
        df_combined = df_existing  # 即使没有新数据，也要确保后续步骤能运行

    # --- 保存结果 (列顺序已更新) ---
    if not df_combined.empty:

        # 定义基础列 (丰富了维度)
        base_columns = [
            "benchmark_name", "is_original_proposal", "dataset_url", "task_description", "dimension",
            "evaluation_method", "context_dependency", "problem_domain",
            "problem_difficulty", "language", "data_size", "source_type",
            "last_updated", "build_type", "contamination_status",
            "dataset_license", "task_granularity", "evaluation_metrics", "input_modality",
            "output_modality", "task_io_type", "execution_environment", "unique_features"  # "额外列"
        ]

        # 动态生成带引述的完整列列表 (实现请求 3)
        desired_columns = ['source_paper']
        for col in base_columns:
            if col in df_combined.columns:  # 检查列是否存在
                desired_columns.append(col)
                if f"{col}_quote" in df_combined.columns:
                    desired_columns.append(f"{col}_quote")  # 为每个字段添加引述列

        # 排序
        existing_columns_ordered = [col for col in desired_columns if col in df_combined.columns]
        other_columns = [col for col in df_combined.columns if col not in existing_columns_ordered]
        final_columns = existing_columns_ordered + other_columns
        # 确保只使用 df_combined 中实际存在的列
        final_columns_existing = [col for col in final_columns if col in df_combined.columns]
        df_combined = df_combined[final_columns]

        df_combined.to_csv(output_filename, index=False, encoding='utf-8-sig')

        print(f"数据集已更新并保存到: {output_filename}")
        print(f"数据库总条目数: {len(df_combined)}")
        print("\n结果预览 (前5行，部分核心列):")
        preview_cols = ['source_paper', 'benchmark_name', 'dataset_url', 'task_description', 'evaluation_method',
                        'context_dependency']
        print(df_combined.head()[preview_cols].to_markdown(index=False))
    else:
        print(f"\n❌ 未能从 {len(input_files)} 个路径中成功识别出有效的代码评测基准信息。")


# --- 6. 主程序 (已更新) ---
if __name__ == "__main__":
    extract_benchmark()