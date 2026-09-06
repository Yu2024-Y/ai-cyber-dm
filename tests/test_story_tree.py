"""S3-6 剧情分支树单测。"""
from src.services.story_tree import StoryTree, tree_from_messages


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


def test_add_branch_kind_marker() -> None:
    """节点类型标记：scene/action/story。"""
    tree = StoryTree()
    root = tree.add_branch("开局", kind="scene")
    tree.add_branch("玩家行动", root, kind="action")
    node = tree.to_dict()
    assert node["kind"] == "scene"
    assert node["children"][0]["kind"] == "action"


def test_tree_from_messages_chain() -> None:
    """一问一答从会话历史重建为推进链。"""
    result = tree_from_messages(
        "赛博酒馆",
        [
            {"role": "user", "content": "[刀锋的行动] 我走进酒馆"},
            {"role": "assistant", "content": "酒保抬起头，霓虹灯下他低声说道……"},
            {"role": "user", "content": "[陈昱彤的行动] 我问发生了什么"},
            {"role": "assistant", "content": "一场袭击正在酝酿，他递给你一把钥匙。"},
        ],
    )
    assert result["kind"] == "scene"
    assert result["title"] == "赛博酒馆"
    action = result["children"][0]
    assert action["kind"] == "action"
    story = action["children"][0]
    assert story["kind"] == "story"
    assert story["children"][0]["kind"] == "action"
    assert result["children"][0]["title"] == "[刀锋的行动] 我走进酒馆"


def test_tree_from_messages_trims_long_text() -> None:
    """超长剧情被截断为标题（…收尾）。"""
    long_text = "酒保" + "神秘的低语" * 20  # 60+ 字符
    result = tree_from_messages("开局", [{"role": "assistant", "content": long_text}])
    assert result["children"][0]["title"].endswith("…")
    assert len(result["children"][0]["title"]) <= 41


def test_tree_from_messages_parallel_actions_fork() -> None:
    """同一剧情节点下多个玩家行动 → 真实分支。"""
    result = tree_from_messages(
        "废墟",
        [
            {"role": "user", "content": "[A的行动] 我去撬门"},
            {"role": "user", "content": "[B的行动] 我在旁警戒"},
        ],
    )
    assert len(result["children"]) == 2  # 两个行动并行 → 两个子节点
