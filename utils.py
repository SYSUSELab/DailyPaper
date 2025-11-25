import re
import json


def save_last_position(position):
    """保存jsonl文件当前处理位置"""
    with open("process_state.txt", 'w') as f:
        f.write(str(position))


def load_last_position():
    """加载上次处理到的文件位置"""
    try:
        with open("process_state.txt", 'r') as f:
            return int(f.read().strip())
    except (FileNotFoundError, ValueError):
        return 0


def safe_json_loads(json_string):
    """
    安全地解析 JSON 字符串，尝试修复常见问题
    """
    if not json_string or not isinstance(json_string, str):
        return None

    # 尝试直接解析
    try:
        return json.loads(json_string)
    except json.JSONDecodeError as e:
        print(f"JSON 解析错误: {e}")
        print(f"问题字符串: {json_string}")

    # 尝试修复常见问题
    try:
        # 修复1: 将单引号替换为双引号
        fixed_string = json_string.replace("'", '"')

        # 修复2: 确保属性名有双引号
        # 匹配没有引号的属性名并添加双引号
        fixed_string = re.sub(r'(\w+)\s*:', r'"\1":', fixed_string)

        # 修复3: 处理尾随逗号
        fixed_string = re.sub(r',\s*}', '}', fixed_string)
        fixed_string = re.sub(r',\s*]', ']', fixed_string)

        return json.loads(fixed_string)
    except json.JSONDecodeError as e:
        print(f"修复后仍然解析错误: {e}")
        return json_string

