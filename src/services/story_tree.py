"""剧情分支树（S3-6）：记录剧情走向并生成树结构。

- add_branch：添加剧情节点（可指定父节点）
- to_dict：序列化为嵌套字典（前端渲染树形）
"""
from dataclasses import dataclass, field


@dataclass
class BranchNode:
    """剧情分支节点。"""

    node_id: int
    title: str
    parent_id: int | None = None
    children: list["BranchNode"] = field(default_factory=list)


class StoryTree:
    """剧情分支树。"""

    def __init__(self) -> None:
        self._nodes: dict[int, BranchNode] = {}
        self._next_id = 1

    def add_branch(self, title: str, parent_id: int | None = None) -> int:
        """添加剧情节点，返回 node_id。"""
        node = BranchNode(self._next_id, title, parent_id)
        self._nodes[node.node_id] = node
        if parent_id is not None and parent_id in self._nodes:
            self._nodes[parent_id].children.append(node)
        self._next_id += 1
        return node.node_id

    def to_dict(self, root_id: int | None = None) -> dict:
        """序列化为嵌套字典（供前端渲染）。"""
        root_id = root_id or self._find_root()
        node = self._nodes.get(root_id)
        if node is None:
            return {}
        return {
            "id": node.node_id,
            "title": node.title,
            "children": [self.to_dict(c.node_id) for c in node.children],
        }

    def _find_root(self) -> int | None:
        """找到根节点（无 parent 的节点）。"""
        for node in self._nodes.values():
            if node.parent_id is None:
                return node.node_id
        return None

    def size(self) -> int:
        return len(self._nodes)
