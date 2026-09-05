"""S3-6 剧情分支树单测。"""
from src.services.story_tree import StoryTree


def test_add_branch_returns_id() -> None:
    """添加节点返回自增 id。"""
    tree = StoryTree()
    assert tree.add_branch("开局") == 1
    assert tree.add_branch("分支A", parent_id=1) == 2
    assert tree.size() == 2


def test_tree_structure() -> None:
    """能构建父子层级。"""
    tree = StoryTree()
    root = tree.add_branch("进入酒馆")
    a = tree.add_branch("点一杯酒", root)
    tree.add_branch("询问传闻", root)
    tree.add_branch("酒保透露情报", a)

    assert len(tree._nodes[root].children) == 2
    assert tree.size() == 4


def test_to_dict_nested() -> None:
    """序列化为嵌套结构。"""
    tree = StoryTree()
    root = tree.add_branch("进入酒馆")
    child = tree.add_branch("点一杯酒", root)
    tree.add_branch("酒保透露情报", child)

    result = tree.to_dict()
    assert result["title"] == "进入酒馆"
    assert result["children"][0]["title"] == "点一杯酒"
    assert result["children"][0]["children"][0]["title"] == "酒保透露情报"


def test_empty_tree() -> None:
    """空树返回空 dict。"""
    tree = StoryTree()
    assert tree.to_dict() == {}
