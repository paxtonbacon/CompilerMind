// 预置 C-Minus 示例代码，供各页面一键加载
export const presetExamples = [
  {
    name: 'Hello World',
    desc: '最简单的 main 函数',
    code: 'int main(void) {\n  return 0;\n}',
    tags: ['入门', '函数']
  },
  {
    name: '变量声明与赋值',
    desc: '基本变量操作',
    code: 'int main(void) {\n  int x;\n  x = 42;\n  return x;\n}',
    tags: ['变量', '赋值']
  },
  {
    name: 'if-else 分支',
    desc: '条件判断语句',
    code: 'int main(void) {\n  int a;\n  int b;\n  a = 10;\n  b = 5;\n  if (a > b) {\n    return a;\n  }\n  else {\n    return b;\n  }\n}',
    tags: ['条件', '分支']
  },
  {
    name: 'while 循环',
    desc: '循环累加计算',
    code: 'int main(void) {\n  int i;\n  int sum;\n  i = 0;\n  sum = 0;\n  while (i < 10) {\n    sum = sum + i;\n    i = i + 1;\n  }\n  return sum;\n}',
    tags: ['循环', 'while']
  },
  {
    name: 'for 循环',
    desc: 'for 循环示例（含声明）',
    code: 'int main(void) {\n  int sum;\n  sum = 0;\n  for (int i = 0; i < 10; i = i + 1) {\n    sum = sum + i;\n  }\n  return sum;\n}',
    tags: ['循环', 'for']
  },
  {
    name: '数组访问',
    desc: '数组声明与访问',
    code: 'int main(void) {\n  int a[5];\n  a[0] = 1;\n  a[1] = 2;\n  return a[0] + a[1];\n}',
    tags: ['数组']
  },
  {
    name: '函数调用',
    desc: '带参数函数',
    code: 'int add(int x, int y) {\n  return x + y;\n}\n\nint main(void) {\n  return add(3, 4);\n}',
    tags: ['函数', '调用']
  },
  {
    name: '嵌套 if-while',
    desc: 'if 内嵌 while 循环',
    code: 'int main(void) {\n  int x;\n  int y;\n  x = 5;\n  y = 0;\n  if (x > 0) {\n    while (y < x) {\n      y = y + 1;\n    }\n  }\n  return y;\n}',
    tags: ['嵌套', '综合']
  },
  {
    name: '语法错误示例',
    desc: '含未声明变量（语义错误）',
    code: 'int main(void) {\n  int x;\n  x = y + 1;\n  return x;\n}',
    tags: ['错误', '语义']
  },
  {
    name: '复杂表达式',
    desc: '多运算符表达式',
    code: 'int main(void) {\n  int a;\n  int b;\n  int c;\n  a = 10;\n  b = 3;\n  c = a * b + a / b - (a + b);\n  return c;\n}',
    tags: ['表达式', '运算符']
  },
]
