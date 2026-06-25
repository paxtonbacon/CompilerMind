from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import asyncio # 用于模拟大模型生成的延迟
from ..compiler.lexer import tokenize as my_tokenize, Token
from ..compiler.ll_parser import LL1CompilerEngine
from ..compiler.lr_parser import LRParserEngine
from ..compiler.lr_grammar import C_MINUS_GRAMMAR, START_SYMBOL as LR_START
from ..core.llm_works import generate_specific_problem, generate_random_problem
from ..core.llm_answer import generate_answer as llm_generate_answer, generate_report as llm_generate_report, generate_guidance as llm_generate_guidance
from ..compiler.ast_compare import compare_ast_trees
from ..compiler.ll_grammar import GRAMMAR_RULES as LL_GRAMMAR, TERMINALS as LL_TERMS, NON_TERMINALS as LL_NTS, START_SYMBOL as LL_START
from ..config import get_credentials, update_credentials

print("router 对象已创建", flush=True)

router = APIRouter(prefix="/api")
engine = LL1CompilerEngine()
slr_engine = LRParserEngine(C_MINUS_GRAMMAR, start_symbol=LR_START)


# ── 认证 ──
class LoginRequest(BaseModel):
    username: str
    password: str

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str
    new_username: str = ""

@router.post("/login")
async def login(req: LoginRequest):
    creds = get_credentials()
    if req.username == creds["username"] and req.password == creds["password"]:
        return {"success": True, "username": creds["username"]}
    raise HTTPException(status_code=401, detail="用户名或密码错误")

@router.post("/change_password")
async def change_password(req: ChangePasswordRequest):
    creds = get_credentials()
    if req.old_password != creds["password"]:
        raise HTTPException(status_code=401, detail="原始密码错误")
    if len(req.new_password) < 3:
        raise HTTPException(status_code=400, detail="新密码至少3位")
    new_user = req.new_username.strip() if req.new_username.strip() else creds["username"]
    update_credentials(new_user, req.new_password)
    return {"success": True, "username": new_user}


# ── 文法信息 ──
@router.get("/grammar_info")
async def grammar_info():
    """返回 LL(1) 和 LR 文法 + FIRST/FOLLOW + 预测表 + LR 项目集/分析表"""
    ll_grammar_display = {k: v for k, v in LL_GRAMMAR.items()}
    lr_grammar_display = {}
    for line in C_MINUS_GRAMMAR.strip().split('\n'):
        line = line.strip()
        if '→' in line:
            lhs, rhs = line.split('→', 1)
            lr_grammar_display[lhs.strip()] = [a.strip() for a in rhs.strip().split('|')]

    first_table = [{"nt": k, "first": sorted(list(v))} for k, v in engine.first_sets.items() if k in LL_NTS]
    follow_table = [{"nt": k, "follow": sorted(list(v))} for k, v in engine.follow_sets.items()]
    predict_table = engine.get_serializable_table()

    # LR 数据
    lr_item_sets = slr_engine.get_serialized_states()
    lr_table = slr_engine.get_flat_table()

    return {
        "ll_grammar": ll_grammar_display,
        "lr_grammar": lr_grammar_display,
        "first_table": first_table,
        "follow_table": follow_table,
        "predict_table": predict_table,
        "lr_item_sets": lr_item_sets,
        "lr_table": lr_table,
    }


class GrammarAnalyzeRequest(BaseModel):
    grammar_text: str

@router.post("/grammar_analyze")
async def grammar_analyze(req: GrammarAnalyzeRequest):
    """分析自定义文法：检测左递归、计算 FIRST/FOLLOW/预测表、冲突"""
    try:
        from ..compiler.ll_parser import LL1CompilerEngine as LLTemp
        from ..compiler.ll_grammar import GRAMMAR_RULES as _G

        # 简单解析用户文法
        lines = [l.strip() for l in req.grammar_text.split('\n') if l.strip() and '→' in l]
        first_table = []
        errors = []

        for line in lines:
            if '→' not in line: continue
            lhs, rhs = line.split('→', 1)
            lhs = lhs.strip()
            prods = [p.strip().split() for p in rhs.split('|')]
            # 检测直接左递归
            for prod in prods:
                if prod and prod[0] == lhs:
                    errors.append(f"直接左递归: {lhs} → {' '.join(prod)}")

        if errors:
            return {"errors": errors, "firstTable": []}

        # 尝试用 LL 引擎分析
        try:
            # 构造临时文法
            temp_rules = {}
            for line in lines:
                lhs, rhs = line.split('→', 1)
                lhs = lhs.strip()
                prods = []
                for p in rhs.split('|'):
                    tokens = [t.strip() for t in p.strip().split() if t.strip()]
                    prods.append(tokens if tokens else ["ε"])
                temp_rules[lhs] = prods

            temp_engine = LLTemp.__new__(LLTemp)
            temp_engine.rules = temp_rules
            temp_engine.start_symbol = list(temp_rules.keys())[0]
            temp_engine.non_terminals = set(temp_rules.keys())
            temp_engine.terminals = set()
            for prods in temp_rules.values():
                for prod in prods:
                    for sym in prod:
                        if sym != "ε" and sym not in temp_engine.non_terminals:
                            temp_engine.terminals.add(sym)
            temp_engine.first_sets = {}
            temp_engine.follow_sets = {}
            temp_engine.predict_table = {}
            temp_engine.conflicts = []
            temp_engine._compute_first_sets()
            temp_engine._compute_follow_sets()
            temp_engine._build_predict_table()

            for nt in temp_engine.non_terminals:
                first_table.append({
                    "nt": nt,
                    "first": ", ".join(sorted(temp_engine.first_sets.get(nt, set()))),
                    "follow": ", ".join(sorted(temp_engine.follow_sets.get(nt, set()))),
                })

            if temp_engine.conflicts:
                errors.extend(temp_engine.conflicts[:5])
        except Exception as ex:
            errors.append(f"分析异常: {str(ex)}")

        return {"errors": errors, "firstTable": first_table}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
# 单例初始化，仅计算一遍Follow集等

class SourceCode(BaseModel):
    code: str

# 响应体模型（复用 lexer.Token 或定义新的 Pydantic 模型）
class TokenOut(BaseModel):
    type: str
    value: str
    line: int
    column: int

class TokenizeResponse(BaseModel):
    tokens: List[TokenOut]

class SyntaxResponse(BaseModel):
    first_sets: Dict[str, List[str]]
    follow_sets: Dict[str, List[str]]
    predict_table: List[Dict[str, str]]
    conflicts: List[Any]
    ast: Dict[str, Any] = None
    derivation_steps: List[str]
    text_tree: str = ""
    syntax_errors: List[str]
    symbol_table: List[Dict[str, str]] = []
    semantic_errors: List[str] = []
    pcode: List[str] = []

class LRResponse(BaseModel):
    item_sets: Dict[int, List[str]]        # LR(0) 项集族状态定义
    lr_table: List[Dict[str, Any]]         # 扁平化整合后的 ACTION / GOTO 分析表
    conflicts: List[str]
    parsing_steps: List[Dict[str, Any]]    # 包含句柄定位的最左归约可视化步骤
    ast: Optional[Dict[str, Any]] = None   # 兼容 ECharts Tree 数据格式
    text_tree: str                         # 纯文本骨架树
    syntax_errors: List[str]

# 定义前端传过来的请求体格式
class ProblemRequest(BaseModel):
    difficulty: str
    requirements: str

# 定义返回的数据格式（非必须，但符合规范）
class ProblemResponse(BaseModel):
    markdown: str

# ── 答案生成 ──
class AnswerRequest(BaseModel):
    problem_markdown: str
    use_grammar_constraint: bool = False

class AnswerResponse(BaseModel):
    answer_code: str
    raw_code: str = ""
    use_constraint: bool = False
    is_valid: Optional[bool] = None
    corrections: List[Dict[str, str]] = []
    validation_log: List[str] = []
    retry_history: List[Dict[str, Any]] = []



@router.post("/generate_answer", response_model=AnswerResponse)
async def api_generate_answer(req: AnswerRequest):
    try:
        result = await llm_generate_answer(
            problem_markdown=req.problem_markdown,
            use_grammar_constraint=req.use_grammar_constraint
        )
        return AnswerResponse(**result)
    except Exception as e:
        print(f"答案生成失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"答案生成失败: {str(e)}")




@router.post("/tokenize", response_model=TokenizeResponse)
async def tokenize_endpoint(src: SourceCode):
    try:
        tokens = my_tokenize(src.code)
        # 将 dataclass 转换为 Pydantic 模型（或直接返回字典）
        return {"tokens": [TokenOut(**t.__dict__) for t in tokens]}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))



@router.post("/ll_parse", response_model=SyntaxResponse)
async def analyze_syntax(src: SourceCode):
    try:
        tokens = my_tokenize(src.code)
        result = engine.parse(tokens)
        return SyntaxResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))



@router.post("/lr_parse", response_model=LRResponse)
async def lr_parser(src: SourceCode):
    # 1. 词法切分
    tokens = my_tokenize(src.code)
    
    # 2. 调用底层的 SLR(1) 状态机引擎，获取完整前端数据
    result = slr_engine.get_frontend_data(tokens)
    
    return LRResponse(**result)


# ── AST 对比请求/响应 ──
class ASTCompareRequest(BaseModel):
    student_code: str
    reference_code: str

class ASTCompareResponse(BaseModel):
    similarity: float
    edit_distance: int
    edit_operations: List[Dict[str, Any]] = []
    student_ast: Dict[str, Any] = {}
    reference_ast: Dict[str, Any] = {}
    student_diff_count: int = 0
    reference_diff_count: int = 0
    student_tree: str = ""
    reference_tree: str = ""



@router.post("/diagnose")
async def diagnose(src: SourceCode):
    return {"diagnosis": "TODO"}


@router.post("/compare_ast", response_model=ASTCompareResponse)
async def compare_ast(req: ASTCompareRequest):
    """对比学生代码与参考答案的 SLR(1) AST"""
    try:
        # 解析学生代码
        student_tokens = my_tokenize(req.student_code)
        student_result = slr_engine.get_frontend_data(student_tokens)
        student_ast = student_result.get("ast", {})

        # 解析参考答案
        ref_tokens = my_tokenize(req.reference_code)
        ref_result = slr_engine.get_frontend_data(ref_tokens)
        ref_ast = ref_result.get("ast", {})

        # 树编辑距离对比
        comparison = compare_ast_trees(student_ast, ref_ast)
        return ASTCompareResponse(**comparison)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"AST 对比失败: {str(e)}")


@router.post("/generate_problem", response_model=ProblemResponse)
async def api_generate_problem(req: ProblemRequest):
    try:
        # 调用 DeepSeek 生成指定题目
        markdown_content = await generate_specific_problem(
            difficulty=req.difficulty, 
            requirements=req.requirements
        )
        return ProblemResponse(markdown=markdown_content)
    
    except Exception as e:
        # 打印错误到终端方便排查，同时返回给前端 500
        print(f"LLM 接口调用出错: {str(e)}")
        raise HTTPException(status_code=500, detail="题目生成失败，请检查模型 API 设置。")


@router.get("/generate_random_problem", response_model=ProblemResponse)
async def api_generate_random_problem():
    try:
        # 调用 DeepSeek 生成随机题目
        markdown_content = await generate_random_problem()
        return ProblemResponse(markdown=markdown_content)
        
    except Exception as e:
        print(f"LLM 接口调用出错: {str(e)}")
        raise HTTPException(status_code=500, detail="随机抽取失败，请检查模型 API 设置。")


# ── 大模型诊断报告 ──
class ReportRequest(BaseModel):
    student_code: str
    problem_markdown: str = ""
    syntax_errors: List[str] = []
    semantic_errors: List[str] = []
    ast_similarity: float = 0.0
    ast_edit_ops: List[Dict[str, Any]] = []

class ParsedReport(BaseModel):
    score: int = 0
    level: str = "medium"
    comment_text: str = ""
    suggestion: str = ""
    errors: List[Dict[str, Any]] = []

class ReportResponse(BaseModel):
    raw_report: str = ""
    parsed: ParsedReport = ParsedReport()


@router.post("/generate_report", response_model=ReportResponse)
async def api_generate_report(req: ReportRequest):
    try:
        result = await llm_generate_report(
            student_code=req.student_code,
            problem_markdown=req.problem_markdown,
            syntax_errors=req.syntax_errors,
            semantic_errors=req.semantic_errors,
            ast_similarity=req.ast_similarity,
            ast_edit_ops=req.ast_edit_ops,
        )
        return ReportResponse(**result)
    except Exception as e:
        print(f"报告生成失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"报告生成失败: {str(e)}")


# ── 个性化指导 ──
class GuidanceRequest(BaseModel):
    student_code: str
    problem_markdown: str = ""
    syntax_errors: List[str] = []
    semantic_errors: List[str] = []
    ast_similarity: float = 0.0
    history_summaries: List[str] = []

class GuidanceResponse(BaseModel):
    markdown: str = ""


@router.post("/generate_guidance", response_model=GuidanceResponse)
async def api_generate_guidance(req: GuidanceRequest):
    try:
        markdown = await llm_generate_guidance(
            student_code=req.student_code,
            problem_markdown=req.problem_markdown,
            syntax_errors=req.syntax_errors,
            semantic_errors=req.semantic_errors,
            ast_similarity=req.ast_similarity,
            history_summaries=req.history_summaries,
        )
        return GuidanceResponse(markdown=markdown)
    except Exception as e:
        print(f"指导生成失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"指导生成失败: {str(e)}")


# ── LLM 聊天 ──
class ChatRequest(BaseModel):
    message: str
    context: str = ""  # 可附带当前题目/代码上下文

class ChatResponse(BaseModel):
    reply: str = ""


@router.post("/chat", response_model=ChatResponse)
async def api_chat(req: ChatRequest):
    try:
        from ..core.llm_answer import _call_llm
        system_prompt = (
            "你是 CompilerMind 编译原理教学助教。请用中文回答学生问题，语气亲切专业。"
        )
        user_msg = req.message
        if req.context:
            user_msg = f"【当前上下文】\n{req.context}\n\n【学生问题】\n{req.message}"

        reply = await _call_llm([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg},
        ])
        return ChatResponse(reply=reply)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"聊天失败: {str(e)}")