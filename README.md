# CompilerMind

面向 C-Minus 语言的编译原理教学平台。覆盖词法分析、LL(1) 与 LR(1) 语法分析、语义分析、P-Code 中间代码生成，集成 DeepSeek 实现自动出题与 AI 辅助学习。

## 架构

```
frontend (Vue 3 + Element Plus + Vite, port 5173)
    │  /api 代理
backend  (FastAPI + Python, port 9001)
    │
    ├── compiler/     词法、LL/LR 语法、语义、P-Code、AST 对比
    ├── core/         DeepSeek LLM 调用（出题、答案生成、诊断报告）
    └── api/          REST 路由
```

## 快速启动

### 开发环境

**后端**

```bash
cd backend
conda activate hermesfitness
uvicorn app.main:app --host 0.0.0.0 --port 9001
```

**前端**

```bash
cd frontend
npm install
npm run dev
```

浏览器打开 `http://localhost:5173`。

### Docker 部署

```bash
git clone https://github.com/paxtonbacon/CompilerMind.git && cd CompilerMind

# 配置 DeepSeek API Key（编辑 backend/app/config.py）
# DEEPSEEK_API_KEY = "your-key"

docker compose up -d --build
```

访问 `http://<服务器IP>`，前端运行在 8096 端口，后端在 9001 端口。nginx 自动将 `/api/` 请求代理到后端容器。
访问 `http://<服务器IP>:8096` 即可访问页面
（如若修改，请在docker-compose中修改8096:80为其他:80）

## 编译流水线

| 阶段           | 模块                        | 说明                                               |
| -------------- | --------------------------- | -------------------------------------------------- |
| 词法分析       | `compiler/lexer.py`       | 正则匹配，输出 Token 序列（类型、字面值、行列号）  |
| LL(1) 语法分析 | `compiler/ll_parser.py`   | 手写递归下降，计算 FIRST/FOLLOW/预测分析表         |
| LR 语法分析    | `compiler/lr_parser.py`   | SLR(1) 状态机，构造项目集规范族和分析表            |
| 语义分析       | `compiler/semantic.py`    | 作用域栈式符号表，检测变量重定义与未声明引用       |
| 中间代码       | `compiler/pcode.py`       | 三地址码 P-Code 生成                               |
| AST 对比       | `compiler/ast_compare.py` | 简化 Zhang-Shasha 树编辑距离，输出相似度与差异标注 |

## API 端点

| 方法 | 路径                             | 用途                         |
| ---- | -------------------------------- | ---------------------------- |
| POST | `/api/tokenize`                | 词法分析                     |
| POST | `/api/ll_parse`                | LL(1) 解析                   |
| POST | `/api/lr_parse`                | LR(1) 解析                   |
| POST | `/api/compare_ast`             | AST 树对比                   |
| POST | `/api/generate_problem`        | 指定生成题目                 |
| GET  | `/api/generate_random_problem` | 随机生成题目                 |
| POST | `/api/generate_answer`         | 生成参考答案（可选文法约束） |
| POST | `/api/generate_report`         | 生成诊断报告                 |
| POST | `/api/generate_guidance`       | 生成个性化指导               |
| POST | `/api/chat`                    | AI 助教聊天                  |
| GET  | `/api/grammar_info`            | 文法规则与解析数据           |
| POST | `/api/grammar_analyze`         | 自定义文法分析               |

## LLM 集成

使用 DeepSeek API（OpenAI 兼容格式），配置在 `backend/app/config.py`。实现了文法约束校验：LLM 生成代码后，由 LL(1) 预测分析表逐 Token 验证 FIRST 集合法性，对越界 Token 触发自动修正与重试。

对照实验脚本：`backend/experiments/grammar_constraint_experiment.py`

## 前端页面

| 路由              | 功能                                       |
| ----------------- | ------------------------------------------ |
| `/home`         | 工作台：题目描述 + 代码编辑 + 编译结果面板 |
| `/grammar`      | LL(1) 与 LR 文法规约参考                   |
| `/lexer`        | 词法规则分类与 DFA 状态转换                |
| `/ll-parser`    | LL(1) FIRST/FOLLOW 集与预测分析表          |
| `/lr-parser`    | LR(0) 项目集规范族与分析表                 |
| `/semantic`     | 语义分析知识点                             |
| `/llm-analysis` | AI 助教对话                                |

## 技术栈

- 前端：Vue 3, Element Plus, Vue Router, Monaco Editor, Marked, Axios, Vite
- 后端：FastAPI, Uvicorn, OpenAI SDK (DeepSeek)
- 语言：Python 3.11, JavaScript
