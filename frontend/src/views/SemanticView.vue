<template>
  <div class="sv-page">

    <el-scrollbar class="sv-body">
      <div class="cards-grid">

        <!-- 1. 概述 -->
        <div class="card card-wide">
          <div class="card-head">语义分析概述</div>
          <div class="card-body">
            <p>语法分析验证代码<strong>结构正确</strong>，语义分析验证代码<strong>含义正确</strong>。C-Minus 编译器的语义分析器以 AST 为输入，逐节点遍历，完成以下检查：</p>
            <ul>
              <li>构建符号表，记录每个标识符的名称、类型、类别与作用域</li>
              <li>检测未声明引用：变量在使用前必须已声明</li>
              <li>检测重定义：同一作用域内不允许声明同名变量</li>
              <li>类型兼容性检查：void 类型不能用于变量声明，函数返回类型需匹配</li>
            </ul>
          </div>
        </div>

        <!-- 2. 符号表与作用域 -->
        <div class="card">
          <div class="card-head">符号表与作用域管理</div>
          <div class="card-body">
            <p>符号表采用栈式结构管理嵌套作用域。每进入一个复合语句 <code>{ ... }</code>，压入新作用域；离开时弹出。</p>
            <pre class="code-block">[Global]
  └── [func_main]
       ├── a: int  (Variable)
       └── [block_0]
            └── x: int  (Variable)</pre>
            <p>变量查找遵循"由内向外"原则：从当前作用域开始，逐层向外搜索，直到全局作用域。</p>
          </div>
        </div>

        <!-- 3. 重定义检测 -->
        <div class="card card-error">
          <div class="card-head">变量重定义检测</div>
          <div class="card-body">
            <p>在同一作用域内声明同名变量将触发重定义错误。若同名变量位于不同作用域，则允许（内层变量遮蔽外层）。</p>
            <pre class="code-block bad">int main(void) {
    int x;
    int x;    // 错误: 变量 'x' 在当前作用域中已声明
    return 0;
}</pre>
            <pre class="code-block good">int main(void) {
    int x;
    {
        int x;   // 合法: 不同作用域，内层 x 遮蔽外层 x
    }
    return 0;
}</pre>
          </div>
        </div>

        <!-- 4. 未声明引用 -->
        <div class="card card-error">
          <div class="card-head">未声明引用检测</div>
          <div class="card-body">
            <p>变量在赋值或表达式使用前，必须在当前或外层作用域中已完成声明。函数参数在函数作用域内自动声明。</p>
            <pre class="code-block bad">int main(void) {
    int x;
    y = 5;     // 错误: 变量 'y' 在使用前未声明
    return x;
}</pre>
            <pre class="code-block good">int add(int a, int b) {
    return a + b;   // a, b 已作为参数声明，合法
}</pre>
          </div>
        </div>

        <!-- 5. 类型检查 -->
        <div class="card">
          <div class="card-head">类型兼容性检查</div>
          <div class="card-body">
            <p>C-Minus 支持 <code>int</code>、<code>float</code>、<code>void</code> 三种基本类型。<code>void</code> 只能用于函数返回类型或参数列表，不可用于变量声明。数组声明格式为 <code>type ID [ INTEGER ]</code>，类型记为 <code>type[]</code>。</p>
            <pre class="code-block bad">void main(void) {
    void x;    // 错误: 不能用 void 声明变量
    return 0;
}</pre>
            <pre class="code-block good">int main(void) {
    int a;
    float b;
    int arr[10];   // 数组类型 int[]
    return 0;
}</pre>
          </div>
        </div>

        <!-- 6. 执行流程 -->
        <div class="card card-wide">
          <div class="card-head">语义分析执行流程</div>
          <div class="card-body">
            <pre class="flow-block">
  AST 根节点
    │
    ▼
  push_scope("Global")
    │
    ▼
  遍历 AST 节点树
    │
    ├── fun_declaration  ── 声明函数，push 函数作用域
    ├── var_declaration  ── 提取类型与变量名，调用 declare()
    ├── compound_stmt    ── push_scope() / pop_scope()
    ├── param            ── 提取参数类型与名称，调用 declare()
    └── ID (表达式)      ── 调用 lookup()，未找到则报告语义错误
    │
    ▼
  输出: 符号表 + 语义错误列表</pre>
          </div>
        </div>

      </div>
    </el-scrollbar>
  </div>
</template>

<script setup>
</script>

<style scoped>
.sv-page { height: 100%; display: flex; flex-direction: column; background: #f8fafc; border-radius: 8px; overflow: hidden; }
.sv-title { font-size: 18px; font-weight: 700; color: #1e293b; padding: 16px 24px; background: #fff; border-bottom: 1px solid #e2e8f0; flex-shrink: 0; }
.sv-body { flex: 1; padding: 16px 24px; min-height: 0; }

.cards-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.card { background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; }
.card-wide { grid-column: 1 / -1; }
.card-error { border-left: 4px solid #dc2626; }

.card-head { padding: 12px 16px; font-size: 15px; font-weight: 700; color: #1e293b; background: #f8fafc; border-bottom: 1px solid #f1f5f9; }
.card-body { padding: 12px 16px; font-size: 14px; color: #475569; line-height: 1.8; text-align: left; }
.card-body p { margin: 0 0 8px; }
.card-body ul { margin: 6px 0; padding-left: 22px; }
.card-body li { margin-bottom: 4px; }

.code-block { background: #1e293b; color: #e2e8f0; padding: 10px 14px; border-radius: 6px; font-family: 'Fira Code', monospace; font-size: 13px; line-height: 1.6; margin: 8px 0; white-space: pre; overflow-x: auto; }
.code-block.bad { border-left: 4px solid #ef4444; }
.code-block.good { border-left: 4px solid #22c55e; }

.flow-block { background: #f8fafc; color: #475569; padding: 12px 16px; border-radius: 6px; font-family: 'Fira Code', monospace; font-size: 13px; line-height: 1.6; margin: 0; white-space: pre; overflow-x: auto; border: 1px solid #e2e8f0; }
</style>
