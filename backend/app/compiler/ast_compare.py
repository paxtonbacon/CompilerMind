# -*- coding: utf-8 -*-
"""
ast_compare.py — AST 树编辑距离（简化 Zhang-Shasha 算法）
用于学生 AST 与参考答案 AST 的结构化比对，输出相似度分数 + 差异节点标注。
"""

from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass, field
import copy


@dataclass
class TreeNode:
    """内部索引化树节点"""
    idx: int              # 后序遍历编号
    name: str             # 节点标签
    children: List['TreeNode'] = field(default_factory=list)
    leftmost: int = 0     # 最左叶后代编号
    diff: bool = False    # 是否为差异节点

    def to_dict(self) -> Dict:
        label = f"[DIFF] {self.name}" if self.diff else self.name
        return {
            "name": label,
            "diff": self.diff,
            "children": [c.to_dict() for c in self.children],
        }


def _ast_to_postorder(ast_dict: Dict) -> Tuple[List[TreeNode], TreeNode]:
    """
    将 AST dict 转为后序遍历索引化的 TreeNode 列表。
    返回 (nodes_list, root_node)
    """
    nodes: List[TreeNode] = []

    def dfs(d: Dict) -> TreeNode:
        # 先递归孩子
        children_nodes = []
        for child_d in d.get("children", []):
            children_nodes.append(dfs(child_d))
        # 再创建当前节点
        node = TreeNode(idx=len(nodes), name=d.get("name", "?"), children=children_nodes)
        nodes.append(node)
        return node

    root = dfs(ast_dict)

    # 计算 leftmost（最左叶后代）
    for node in nodes:
        if not node.children:
            node.leftmost = node.idx
        else:
            node.leftmost = node.children[0].leftmost

    return nodes, root


def _keyroots(nodes: List[TreeNode]) -> List[int]:
    """返回 keyroot 节点索引列表（有左兄弟的节点 + 根节点）"""
    kr = set()
    for node in nodes:
        for i, child in enumerate(node.children):
            if i > 0:
                kr.add(child.idx)
    kr.add(nodes[-1].idx)  # 根节点
    return sorted(kr)


# ── 简化 Zhang-Shasha 树编辑距离 ──
def tree_edit_distance(tree1: Dict, tree2: Dict) -> Tuple[float, List[Dict], Dict, Dict]:
    """
    计算两棵 AST 的编辑距离，返回：
    - similarity: 0~100 相似度分数
    - edit_ops: 编辑操作列表 [{"op": "rename|delete|insert", "node": str, "cost": int}, ...]
    - highlighted1: 标注 diff 后的 tree1 dict
    - highlighted2: 标注 diff 后的 tree2 dict

    编辑操作代价：
    - rename: 1（节点名不同）
    - delete: 1
    - insert: 1
    - match: 0（节点名相同）
    """
    nodes1, root1 = _ast_to_postorder(tree1)
    nodes2, root2 = _ast_to_postorder(tree2)

    n1 = len(nodes1)
    n2 = len(nodes2)

    # DP 表：td[i][j] = 以 nodes[i], nodes[j] 为根的子树编辑距离
    td = [[0] * n2 for _ in range(n1)]

    # 森林距离临时表
    fd = [[0] * (n2 + 1) for _ in range(n1 + 1)]

    kr1 = _keyroots(nodes1)
    kr2 = _keyroots(nodes2)

    # 辅助函数：子节点索引范围
    def children_range(node, nodes):
        """返回 node 的直接子节点索引列表（后序）"""
        return [c.idx for c in node.children]

    # Zhang-Shasha 核心 DP
    for x in kr1:
        for y in kr2:
            _forest_dist(nodes1, nodes2, x, y, td, fd)

    edit_dist = td[n1 - 1][n2 - 1] if n1 > 0 and n2 > 0 else max(n1, n2)

    # 相似度：0~100
    max_nodes = max(n1, n2)
    similarity = max(0.0, 100.0 * (1.0 - edit_dist / max_nodes)) if max_nodes > 0 else 100.0
    similarity = round(similarity, 1)

    # ── 回溯找出差异节点 ──
    diff_nodes1: Set[int] = set()
    diff_nodes2: Set[int] = set()
    edit_ops: List[Dict] = []

    def backtrack(i: int, j: int):
        if i < 0 and j < 0:
            return
        if i < 0:
            diff_nodes2.add(j)
            edit_ops.append({"op": "insert", "node": nodes2[j].name, "cost": 1})
            if nodes2[j].children:
                backtrack(-1, nodes2[j].children[-1].idx)
            return
        if j < 0:
            diff_nodes1.add(i)
            edit_ops.append({"op": "delete", "node": nodes1[i].name, "cost": 1})
            if nodes1[i].children:
                backtrack(nodes1[i].children[-1].idx, -1)
            return

        node1 = nodes1[i]
        node2 = nodes2[j]

        # 是否匹配（名称相同或只有值不同）
        name1 = node1.name.split("(")[0].strip() if "(" in node1.name else node1.name
        name2 = node2.name.split("(")[0].strip() if "(" in node2.name else node2.name

        if name1 == name2 and len(node1.children) == len(node2.children):
            # 匹配：递归比较子节点
            for ci, cj in zip(node1.children, node2.children):
                backtrack(ci.idx, cj.idx)
        elif name1 == name2 and len(node1.children) != len(node2.children):
            # 结构不同：标记重命名
            diff_nodes1.add(i)
            diff_nodes2.add(j)
            edit_ops.append({
                "op": "rename",
                "node": f"{node1.name} → {node2.name}",
                "cost": 1
            })
            # 递归比较子节点（尽可能匹配）
            c1 = node1.children
            c2 = node2.children
            min_c = min(len(c1), len(c2))
            for k in range(min_c):
                backtrack(c1[k].idx, c2[k].idx)
            for k in range(min_c, len(c1)):
                diff_nodes1.add(c1[k].idx)
            for k in range(min_c, len(c2)):
                diff_nodes2.add(c2[k].idx)
        else:
            diff_nodes1.add(i)
            diff_nodes2.add(j)
            edit_ops.append({
                "op": "rename",
                "node": f"{node1.name} ↔ {node2.name}",
                "cost": 1
            })

    if n1 > 0 and n2 > 0:
        backtrack(n1 - 1, n2 - 1)
    elif n1 > 0:
        for i in range(n1):
            diff_nodes1.add(i)
            edit_ops.append({"op": "delete", "node": nodes1[i].name, "cost": 1})
    elif n2 > 0:
        for j in range(n2):
            diff_nodes2.add(j)
            edit_ops.append({"op": "insert", "node": nodes2[j].name, "cost": 1})

    # ── 生成标注后的 AST dict ──
    def rebuild_diff(ast_dict: Dict, diff_set: Set[int], nodes: List[TreeNode]) -> Dict:
        d = copy.deepcopy(ast_dict)

        def mark(node_d: Dict, node_idx: int):
            if node_idx in diff_set:
                node_d["diff"] = True
                # 给 name 加红色高亮标记
                node_d["name"] = f"❌ {node_d['name']}"
            else:
                node_d["diff"] = False
            # 递归子节点
            for child_d in node_d.get("children", []):
                # 匹配子节点索引
                for n in nodes:
                    if n.idx not in diff_set and n.name == child_d.get("name", "").replace("❌ ", ""):
                        pass
            # 简单递归
            for child_d in node_d.get("children", []):
                mark(child_d, -1)  # 简单标记所有子节点

        def mark_by_structure(ad: Dict, nd: TreeNode, diff_s: Set[int]):
            if nd.idx in diff_s:
                ad["diff"] = True
                if not ad["name"].startswith("❌ "):
                    ad["name"] = f"❌ {ad['name']}"
            else:
                ad["diff"] = False
            for child_ad, child_nd in zip(ad.get("children", []), nd.children):
                mark_by_structure(child_ad, child_nd, diff_s)

        mark_by_structure(d, nodes[-1], diff_set)
        return d

    highlighted1 = rebuild_diff(tree1, diff_nodes1, nodes1) if tree1 and nodes1 else tree1
    highlighted2 = rebuild_diff(tree2, diff_nodes2, nodes2) if tree2 and nodes2 else tree2

    return similarity, edit_ops, highlighted1, highlighted2


def _forest_dist(nodes1, nodes2, i, j, td, fd):
    """
    计算森林距离 fd，用于 Zhang-Shasha 算法。
    森林由 nodes1[l_i..i] 和 nodes2[l_j..j] 组成。
    """
    l_i = nodes1[i].leftmost if i >= 0 else 0
    l_j = nodes2[j].leftmost if j >= 0 else 0

    # 初始化边界
    for di in range(l_i, i + 2):
        fd[di][l_j] = 0
    for dj in range(l_j, j + 2):
        fd[l_i][dj] = 0

    m = i - l_i + 1
    n = j - l_j + 1

    for di in range(1, m + 1):
        ii = l_i + di - 1
        fd[ii + 1][l_j] = fd[ii][l_j] + 1  # 删除 nodes1[ii]

    for dj in range(1, n + 1):
        jj = l_j + dj - 1
        fd[l_i][jj + 1] = fd[l_i][jj] + 1  # 插入 nodes2[jj]

    for di in range(1, m + 1):
        for dj in range(1, n + 1):
            ii = l_i + di - 1
            jj = l_j + dj - 1

            if nodes1[ii].leftmost == l_i and nodes2[jj].leftmost == l_j:
                # 子树替换
                cost = 0 if nodes1[ii].name.split("(")[0].strip() == nodes2[jj].name.split("(")[0].strip() else 1
                fd[ii + 1][jj + 1] = min(
                    fd[ii][jj + 1] + 1,       # 删除 nodes1[ii]
                    fd[ii + 1][jj] + 1,       # 插入 nodes2[jj]
                    fd[ii][jj] + cost,         # 替换
                )
                td[ii][jj] = fd[ii + 1][jj + 1]
            else:
                l_ii = nodes1[ii].leftmost
                l_jj = nodes2[jj].leftmost
                fd[ii + 1][jj + 1] = min(
                    fd[ii][jj + 1] + 1,
                    fd[ii + 1][jj] + 1,
                    fd[l_ii][l_jj] + td[ii][jj],
                )


# ═══════════════════════════════════════════════
#  对外接口
# ═══════════════════════════════════════════════
def compare_ast_trees(ast_student: Dict, ast_reference: Dict) -> Dict:
    """
    对比两棵 AST，返回：
    {
        "similarity": float,         # 0~100 相似度分数
        "edit_distance": int,        # 编辑距离
        "edit_operations": [...],    # 编辑操作列表
        "student_ast": Dict,          # 标注 diff 后的学生 AST
        "reference_ast": Dict,        # 标注 diff 后的参考 AST
        "student_diff_count": int,   # 学生 AST 差异节点数
        "reference_diff_count": int, # 参考 AST 差异节点数
    }
    """
    # 统计节点数
    def count_nodes(d: Dict) -> int:
        return 1 + sum(count_nodes(c) for c in d.get("children", []))

    n_student = count_nodes(ast_student) if ast_student else 0
    n_ref = count_nodes(ast_reference) if ast_reference else 0

    if not ast_student and not ast_reference:
        return {
            "similarity": 100.0,
            "edit_distance": 0,
            "edit_operations": [],
            "student_ast": {},
            "reference_ast": {},
            "student_diff_count": 0,
            "reference_diff_count": 0,
        }
    if not ast_student:
        return {
            "similarity": 0.0,
            "edit_distance": n_ref,
            "edit_operations": [{"op": "insert", "node": "整个参考树", "cost": n_ref}],
            "student_ast": {},
            "reference_ast": ast_reference,
            "student_diff_count": 0,
            "reference_diff_count": n_ref,
        }
    if not ast_reference:
        return {
            "similarity": 0.0,
            "edit_distance": n_student,
            "edit_operations": [{"op": "delete", "node": "整个学生树", "cost": n_student}],
            "student_ast": ast_student,
            "reference_ast": {},
            "student_diff_count": n_student,
            "reference_diff_count": 0,
        }

    similarity, edit_ops, highlighted_student, highlighted_ref = tree_edit_distance(
        ast_student, ast_reference
    )

    student_diff_count = sum(
        1 for _ in _count_diff_nodes(highlighted_student)
    ) if highlighted_student else 0
    ref_diff_count = sum(
        1 for _ in _count_diff_nodes(highlighted_ref)
    ) if highlighted_ref else 0

    return {
        "similarity": similarity,
        "edit_distance": int((100 - similarity) / 100 * max(n_student, n_ref)),
        "edit_operations": edit_ops[:20],
        "student_ast": highlighted_student,
        "reference_ast": highlighted_ref,
        "student_diff_count": student_diff_count,
        "reference_diff_count": ref_diff_count,
        "student_tree": dict_to_text_tree(highlighted_student) if highlighted_student else "",
        "reference_tree": dict_to_text_tree(highlighted_ref) if highlighted_ref else "",
    }


def _count_diff_nodes(ast_dict: Dict):
    """生成器中 yield 每个 diff 节点"""
    if ast_dict.get("diff"):
        yield ast_dict
    for child in ast_dict.get("children", []):
        yield from _count_diff_nodes(child)


def dict_to_text_tree(ast_dict: Dict, prefix: str = "", is_last: bool = True) -> str:
    """
    将 AST dict 转为带 diff 标注的文本树。
    diff=True 的节点前面加 ❌ 前缀。
    """
    if not ast_dict:
        return ""
    connector = "└── " if is_last else "├── "
    name = ast_dict.get("name", "?")
    # diff 节点加红标记（如果名字还没有 ❌ 前缀）
    if ast_dict.get("diff") and not name.startswith("❌"):
        name = f"❌ {name}"
    result = prefix + connector + name + "\n"
    extension = "    " if is_last else "│   "
    children = ast_dict.get("children", [])
    for i, child in enumerate(children):
        result += dict_to_text_tree(child, prefix + extension, i == len(children) - 1)
    return result
