# llm_works.py
from openai import AsyncOpenAI
from ..config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, MODEL_NAME

# 初始化异步客户端
client = AsyncOpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL
)

# 核心系统指令：强制约束大模型的输出格式
SYSTEM_PROMPT = """你是一个严谨的 C Minus语言在线判题系统（OJ）的出题专家。注意必须要出能使用C Minus语言完成的题目，只涉及float和num，不涉及字符和字符串。
由于C Minus没有设置输入输出。所以输入必须是main函数params位置能容纳的int或者float，输出必须是return可以的。（int/float或者相应数组，各类型题目输入输出都转化成这种格式）
你必须严格按照以下 Markdown 格式输出题目（由于输出不支持latex解析，所以不要用latex符号），不要添加任何额外的问候语、自我介绍或总结：

## 在此生成有极客感的题目名称
> 难度：[在此填入难度等级]

### 题目内容
[在此详细描述题目背景、具体要求和需要实现的功能]

### 考点和输入输出注意
- **考点**：[列出核心考察点]
- **输入说明**：[描述输入格式]
- **输出说明**：[描述输出格式与限制]
"""

async def generate_specific_problem(difficulty: str, requirements: str) -> str:
    """
    指定生成逻辑
    """
    user_prompt = f"请为我生成一道难度为“{difficulty}”的题目。特殊要求如下：{requirements}"
    
    response = await client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.6, # 温度适中，保证题目逻辑严密
    )
    return response.choices[0].message.content


async def generate_random_problem() -> str:
    """
    随机生成逻辑
    """
    user_prompt = "请随机生成一道关于C Minus语言的题目。难度请随机设定。"
    
    response = await client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.9, # 温度调高，增加题目的多样性和随机性
    )
    return response.choices[0].message.content