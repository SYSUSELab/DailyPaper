import openai  # 导入openai库，用于与OpenAI的API进行交互
from openai import OpenAI  # 从openai库中导入OpenAI类
import time  # 导入time模块，用于处理时间相关操作
import os
from utils import safe_json_loads
api_key = os.environ.get("MY_API_KEY")

def call_chatgpt(prompt, model='gpt-5-mini', temperature=0., top_p=1.0,
                 max_tokens=1024):
    """
    调用ChatGPT API以生成文本响应。

    参数:
    - prompt: 提示信息，作为生成文本的基础。
    - model: 使用的模型名称。
    - temperature: 采样温度，控制生成文本的随机性。
    - top_p: 样本的累积概率，控制生成文本的多样性。
    - max_tokens: 生成文本的最大token数。
    """

    client = OpenAI(api_key=api_key,
                    base_url="https://api.agicto.cn/v1")  # 创建OpenAI客户端实例

    try:

        response = client.chat.completions.create(
            model=model,  # 指定使用的模型
            messages=prompt,  # 提供的提示信息
            max_tokens=max_tokens,  # 设置最大token数
            temperature=temperature,  # 设置采样温度
            top_p=top_p,  # 设置top-p采样参数
        )
        response_content = response.choices[0].message.content
        cleaned_response = response_content.strip().replace('```json', '').replace('```', '').strip()
        if cleaned_response.startswith('"') and cleaned_response.endswith('"'):
            cleaned_response = cleaned_response[1:-1].replace('\\"', '"')
        extracted_json = safe_json_loads(cleaned_response)
        return extracted_json

    except openai.RateLimitError as e:  # 捕获API速率限制错误
        time.sleep(2)  # 等待一段时间后重试，请求间隔逐渐增加
