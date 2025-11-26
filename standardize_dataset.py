import os
import json
import re
import pandas as pd
from openai import OpenAI
from pathlib import Path
import time
from typing import Set, List, Dict, Any

# --- 1. 配置  ---
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
if not DEEPSEEK_API_KEY:
    raise ValueError("错误：请设置 'DEEPSEEK_API_KEY' 环境变量。")

client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com"
)


# --- 2. 核心函数：一次性规范化一行中的多个字段 ---

def build_normalization_prompt(raw_data: Dict[str, Any]) -> tuple[str, str]:
    """
    构建一个动态的提示，要求LLM规范化一个字典中所有需要规范化的字段。
    """
    system_prompt = """
    你是一个高精度的中文数据规范化引擎。你的唯一任务是将用户提供的JSON对象中，所有“raw_”开头的字段，转换成结构化的中文输出。
    严格按照指定的JSON格式返回，只返回JSON对象，不要有任何其他解释。

    **规范化规则 (必须严格遵守):**

    1.  **"raw_data_size"** (例如: "164个问题", "约1000+", "3135.95GB的30种编程语言"):
        - 规范为 `{"quantity": <number | null>, "unit": "<string | null>"}`
        - `quantity` 是核心数值 (例如 164, 1000, 3135.95)。
        - `unit` **仅仅**是 **quantity 的直接计量单位** (例如 "个问题", "GB", "TB", "个样本")。
        - **[重要!]** `unit` 字段**绝不能**包含除直接计量单位之外的任何其他描述性信息（例如 "的30种编程语言代码" 这种信息是无关的，必须丢弃）。
        - 如果没有数值，`quantity` 必须为 null。

    2.  **"raw_last_updated"** (例如: "2024.09", "July 2021", "2021"):
        - 规范为 `{"year": <number | null>, "month": <number | null>, "day": <number | null>}`
        - 如果某部分未知，将其设为 null (例如 "2021" -> {"year": 2021, "month": null, "day": null})。

    3.  **"raw_language"**, **"raw_dimension"**, **"raw_evaluation_metrics"**, **"raw_problem_domain"**, **"raw_source_type"**:
        - 这些是“多选”字段。
        - 规范为 **JSON列表 (Array)**，包含所有提取到的中文关键词。
        - 例如: "Python, C++ 和多语言" -> `["Python", "C++", "多语言"]`
        - 例如: "pass@1, pass@10 和 CodeBLEU" -> `["pass@1", "pass@10", "CodeBLEU"]`
        - 如果找不到，返回空列表 `[]`。

    4.  **"raw_problem_difficulty"**, **"raw_context_dependency"**, **"raw_task_granularity"**, **"raw_input_modality"**, **"raw_output_modality"**, **"raw_execution_environment"**, **"raw_dataset_license"**, **"raw_contamination_status"**, **"raw_task_io_type"**:
        - 这些是“单选”分类字段。
        - 规范为 **中文枚举值** (从以下对应列表选一个最接近的):
        - `problem_difficulty`: `"入门级"`, `"竞赛级"`, `"工程级"`, `"未知"`
        - `context_dependency`: `"单函数"`, `"单文件"`, `"多文件/项目级"`, `"未知"`
        - `task_granularity`: `"代码生成"`, `"代码补全"`, `"代码修复"`, `"代码翻译"`, `"代码总结"`, `"未知"`
        - `task_io_type`: `"文本到代码"`, `"代码到代码"`, `"代码到文本"`, `"图文到代码"`, `"未知"`
        - `input_modality`: `"自然语言"`, `"代码与自然语言"`, `"代码与图像"`, `"未知"`
        - `output_modality`: `"代码"`, `"自然语言"`, `"JSON"`, `"未知"`
        - `execution_environment`: `"标准库"`, `"需要特定依赖"`, `"Docker容器"`, `"未知"`
        - `dataset_license`: `"MIT"`, `"Apache 2.0"`, `"GPL-3.0"`, `"BSD"`, `"CC-BY-SA 4.0"`, `"仅供学术研究"`, `"未知"`
        - `contamination_status`: `"高污染风险"`, `"抗污染设计"`, `"未知"`

    **输出JSON结构 (必须严格遵守):**
    {
      "data_size": {"quantity": <number | null>, "unit": "<string | null>"},
      "last_updated": {"year": <number | null>, "month": <number | null>, "day": <number | null>},
      "language": ["<string>", "..."],
      "dimension": ["<string>", "..."],
      "evaluation_method": ["<string>", "..."],
      "problem_domain": ["<string>", "..."],
      "source_type": ["<string>", "..."],
      "problem_difficulty": "<中文枚举值>",
      "context_dependency": "<中文枚举值>",
      "task_granularity": "<中文枚举值>",
      "input_modality": "<中文枚举值>",
      "output_modality": "<中文枚举值>",
      "task_io_type": "<中文枚举值>",
      "execution_environment": "<中文枚举值>",
      "dataset_license": "<标准标识符>",
      "contamination_status": "<中文枚举值>"
    }
    """

    # 将原始数据字典转换为JSON字符串作为用户输入
    user_prompt = json.dumps(raw_data, ensure_ascii=False)

    return system_prompt, user_prompt


def normalize_row_fields(row: pd.Series, fields_to_normalize: list) -> Dict[str, Any]:
    """
    为DataFrame的 *每一行* 调用LLM，规范化所有指定的字段。
    """

    # 1. 准备要发送给LLM的原始数据
    data_to_normalize = {}
    for field in fields_to_normalize:
        raw_value = row.get(field)
        if pd.isna(raw_value) or str(raw_value).strip() == "":
            raw_value = None  # 将空的/NaN值设为None
        data_to_normalize[f"raw_{field}"] = raw_value

    # 2. 构建提示
    system_prompt, user_prompt = build_normalization_prompt(data_to_normalize)

    # 3. 调用API
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0,
            stream=False,
            response_format={"type": "json_object"}  # 使用JSON模式
        )

        response_content = response.choices[0].message.content
        normalized_data = json.loads(response_content)

        # 4. 扁平化LLM的返回结果，以便加入DataFrame
        flat_result = {}
        for main_key, value in normalized_data.items():
            if main_key in ["data_size", "last_updated"] and isinstance(value, dict):
                # 规范化 "data_size" -> "data_size_quantity", "data_size_unit"
                # 规范化 "last_updated" -> "last_updated_year", "last_updated_month", ...
                for sub_key, sub_value in value.items():
                    flat_result[f"{main_key}_{sub_key}"] = sub_value
            elif isinstance(value, list):
                # 规范化 "language" -> "language_normalized" (保存为列表的字符串形式)
                flat_result[f"{main_key}_normalized"] = str(value)  # 保存为 '["Python", "C++"]'
            else:
                # 规范化 "problem_difficulty" -> "problem_difficulty_normalized" (保存为 "入门级")
                flat_result[f"{main_key}_normalized"] = value

        return flat_result

    except Exception as e:
        print(f"  规范化失败 (输入: {user_prompt}): {e}")
        return {"error": str(e)}


# --- 新增：加载现有JSON的辅助函数 ---
def load_existing_json_db(json_path: Path) -> (List[Dict[str, Any]], Set[str]):
    """
    加载现有的 *规范化后* 的JSON数据库。
    返回数据列表和已处理过的 'source_paper' 路径集合。
    """
    if not json_path.exists():
        print(f"未找到现有的规范化JSON数据库：{json_path}。将创建新文件。")
        return [], set()
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if not isinstance(data, list):
            raise json.JSONDecodeError("JSON 顶层不是一个列表", "", 0)

        # 'source_paper' 是我们用来判断是否处理过的唯一ID
        processed_paths = set(item.get('source_paper') for item in data if item.get('source_paper'))
        print(f"成功加载规范化JSON数据库，已包含 {len(data)} 条记录。")
        return data, processed_paths
    except json.JSONDecodeError:
        print(f"警告：规范化JSON文件 {json_path} 为空或已损坏。将创建新文件。")
        return [], set()
    except Exception as e:
        print(f"加载 {json_path} 失败: {e}。将创建新文件。")
        return [], set()


# --- 3. 主程序 ---
def standardize_dataset():
    try:
        script_path = Path(__file__).resolve()
        project_root = script_path.parent
    except NameError:
        project_root = Path.cwd()  # 适应 .ipynb/.py 交互式环境

    results_folder = project_root / "results"

    # 输入文件：提取脚本的输出
    input_csv_path = results_folder / "benchmarks_database_1125.csv"
    # 输出文件：本脚本的最终产物 (JSON)
    output_json_path = results_folder / "benchmarks_database_1125_normalized.json"

    print(f"读取原始CSV: {input_csv_path}")
    print(f"写入/更新JSON: {output_json_path}")

    # 1. 加载 *输入* 的原始CSV
    if not input_csv_path.exists():
        print(f"错误：未找到输入文件 {input_csv_path}")
        print("请先运行 'new_find_benchmark_links.py' 脚本来生成原始CSV。")
        return
    try:
        df_raw = pd.read_csv(input_csv_path)
    except Exception as e:
        print(f"读取CSV文件 {input_csv_path} 失败: {e}")
        return

    # 将路径规范化，以便比较
    df_raw['source_paper'] = df_raw['source_paper'].apply(lambda p: Path(p).as_posix() if pd.notna(p) else None)
    print(f"成功加载原始CSV，总共 {len(df_raw)} 条记录。")

    # 2. 加载 *输出* 的最终JSON，获取已处理的列表
    existing_normalized_data, processed_paths = load_existing_json_db(output_json_path)

    # 3. 找出需要规范化的新行
    # 遍历原始CSV (df_raw)，检查 'source_paper' 是否不在 processed_paths 集合中
    rows_to_normalize = []
    for index, row in df_raw.iterrows():
        source_paper = row.get('source_paper')
        if source_paper and source_paper not in processed_paths:
            rows_to_normalize.append(row)

    if not rows_to_normalize:
        print("没有找到需要规范化的新记录。")
        return

    print(f"找到 {len(rows_to_normalize)} 条新记录，准备开始规范化... (这将调用 {len(rows_to_normalize)} 次API)")

    # 4. 循环处理新行
    newly_normalized_list = []
    total_rows = len(rows_to_normalize)

    # 定义我们希望LLM规范化的所有列
    fields_to_normalize = [
        'data_size', 'last_updated', 'language', 'dimension', 'task_io_type',
        'evaluation_metrics', 'problem_domain', 'source_type', 'problem_difficulty',
        'context_dependency', 'task_granularity', 'input_modality',
        'output_modality', 'execution_environment', 'dataset_license',
        'contamination_status'
    ]
    # 确保只处理CSV中实际存在的列
    fields_to_normalize_existing = [f for f in fields_to_normalize if f in df_raw.columns]

    for index, row in enumerate(rows_to_normalize):
        print(f"\n--- 正在规范化第 {index + 1}/{total_rows} 条 (Benchmark: {row.get('benchmark_name')}) ---")

        # 1. 获取原始数据 (所有列)
        original_data_dict = row.to_dict()

        # 2. 调用LLM进行规范化
        normalized_result_dict = normalize_row_fields(row, fields_to_normalize_existing)
        print(f"  规范化结果: {normalized_result_dict}")

        # 3. 将规范化结果合并回原始数据字典
        original_data_dict.update(normalized_result_dict)

        # 4. 添加到最终列表
        newly_normalized_list.append(original_data_dict)

        time.sleep(1)  # 速率限制

    # --- 5. 整合数据 (追加并保存) ---
    print("\n--- 规范化完成，正在整合数据 ---")

    # 合并旧数据和新数据
    data_combined = existing_normalized_data + newly_normalized_list

    try:
        with open(output_json_path, 'w', encoding='utf-8') as f:
            json.dump(data_combined, f, ensure_ascii=False, indent=2)

        print(f"\n✅ 成功规范化 {len(newly_normalized_list)} 条新记录。")
        print(f"最终JSON数据库已更新: {output_json_path} (总计 {len(data_combined)} 条)")

        if newly_normalized_list:
            print("\n刚刚添加的最后一条记录 (预览):")
            print(json.dumps(newly_normalized_list[-1], indent=2, ensure_ascii=False))

    except PermissionError:
        print(f"\n❌ 保存失败：[Errno 13] Permission denied: '{output_json_path}'")
        print("  请确保你没有在其他程序中打开这个JSON文件！")
    except Exception as e:
        print(f"\n❌ 最终JSON文件保存失败: {e}")


if __name__ == "__main__":
    standardize_dataset()