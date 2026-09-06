"""预设角色目录单测：数量、唯一性、查询。"""
from src.services.role_catalog import ROLES, get_role


def test_roles_enough_for_team() -> None:
    """角色数不少于 3（团队最少 3 人）+ 每人一句介绍。"""
    assert len(ROLES) >= 6
    assert all(r.desc for r in ROLES)
    assert all(r.skills for r in ROLES)


def test_roles_unique_keys_names_colors() -> None:
    """key / 中文名 / 颜色都唯一（避免多人辨识冲突）。"""
    keys = [r.key for r in ROLES]
    names = [r.name for r in ROLES]
    colors = [r.color for r in ROLES]
    assert len(keys) == len(set(keys))
    assert len(names) == len(set(names))
    assert len(colors) == len(set(colors))


def test_get_role_known_and_unknown() -> None:
    """get_role 命中已知角色、未知返回 None。"""
    blade = get_role("blade")
    assert blade is not None and blade.name == "刀锋"
    assert get_role("nobody") is None
