"""剧情分支树（S3-6）：记录剧情走向并生成树结构。

- add_branch：添加剧情节点（可指定父节点、节点类型）
- to_dict：序列化为嵌套字典（前端渲染树形）
- tree_from_messages：从会话历史重建剧情树（前端可视化集成）
"""
from dataclasses import dataclass, field

# 节点类型：scene 开场 / action 玩家行动 / story DM 剧情
NODE_KINDS = ("scene", "action", "story")


@dataclass
class BranchNode:
    """剧情分支节点。"""

    node_id: int
    title: str
    parent_id: int | None = None
    kind: str = "story"
    children: list["BranchNode"] = field(default_factory=list)


class StoryTree:
    """剧情分支树。"""

    def __init__(self) -> None:
        self._nodes: dict[int, BranchNode] = {}
        self._next_id = 1

    def add_branch(
        self, title: str, parent_id: int | None = None, *, kind: str = "story"
    ) -> int:
        """添加剧情节点，返回 node_id。

        参数：
            title：节点标题
            parent_id：父节点 id（None 表示根节点）
            kind：节点类型 scene/action/story
        """
        if kind not in NODE_KINDS:
            kind = "story"
        node = BranchNode(self._next_id, title, parent_id, kind)
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
            "kind": node.kind,
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


def _trim(text: str, max_len: int = 40) -> str:
    """压缩空白并截断为单行标题。"""
    text = " ".join(text.split())
    if len(text) <= max_len:
        return text
    return text[:max_len] + "…"


def tree_from_messages(root_title: str, messages: list[dict], *, max_len: int = 40) -> dict:
    """从会话历史重建剧情树（供前端可视化）。

    结构规则：
      - 开场节点 kind="scene"（根）
      - 玩家行动（role=user）→ kind="action"，挂在最近剧情节点下
      - DM 剧情（role=assistant）→ kind="story"，挂在玩家行动下

    连续两个玩家行动（都挂在同一剧情节点下）会形成真实分支；
    常规一问一答则呈现为剧情推进链。
    """
    tree = StoryTree()
    root = tree.add_branch(root_title, kind="scene")
    last_action: int | None = None
    last_story: int | None = None
    for msg in messages:
        content = _trim(msg.get("content", "") or "", max_len)
        role = msg.get("role")
        if role == "user":
            last_action = tree.add_branch(
                content, parent_id=last_story or root, kind="action"
            )
        elif role == "assistant":
            last_story = tree.add_branch(
                content, parent_id=last_action or root, kind="story"
            )
    return tree.to_dict(root)
