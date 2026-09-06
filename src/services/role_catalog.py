"""预设角色目录：玩家进入战役前从这些架空角色中选择（无真实人名）。

字段说明：
  key：稳定标识（存库）
  name：中文代号（作为玩家名发送给 DM 引擎）
  callsign：英文代号（展示用）
  color：队伍列表 / 气泡颜色
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class RoleCard:
    """一张可选的预设角色卡。"""

    key: str
    name: str
    callsign: str
    title: str
    emoji: str
    color: str
    skills: tuple[str, ...]
    desc: str


ROLES: list[RoleCard] = [
    RoleCard(
        key="blade",
        name="刀锋",
        callsign="Blade",
        title="街头快攻手",
        emoji="⚔️",
        color="#f0883e",
        skills=("近身格斗", "撬锁开路", "巷战直觉"),
        desc="从小在这座霓虹城市底层摸爬滚打，拳头比话快，义体老伙计帮你挡住每一次背叛。",
    ),
    RoleCard(
        key="ghost",
        name="幽灵",
        callsign="Ghost",
        title="网络潜行者",
        emoji="👻",
        color="#58a6ff",
        skills=("骇入终端", "窃取情报", "反追踪"),
        desc="防火墙只是劝退书，不是路障。你在数据之海来去无踪，连自己的过去都能抹掉。",
    ),
    RoleCard(
        key="anvil",
        name="铁砧",
        callsign="Anvil",
        title="义体守护者",
        emoji="🛡️",
        color="#8b949e",
        skills=("重装防御", "断后掩护", "危机处理"),
        desc="改装程度高到分不清人与机器的边线。你挡在前面的时候，队伍就没理由回头。",
    ),
    RoleCard(
        key="echo",
        name="灵犀",
        callsign="Echo",
        title="仿生通感者",
        emoji="📡",
        color="#bc8cff",
        skills=("情绪侦测", "唇语破解", "测谎"),
        desc="被植入实验性通感义体后，你能听见心跳的谎言与霓虹的低语——只要别把自己听疯。",
    ),
    RoleCard(
        key="trigger",
        name="扳机",
        callsign="Trigger",
        title="佣兵枪手",
        emoji="🎯",
        color="#3fb950",
        skills=("远程压制", "战术走位", "弹道测算"),
        desc="把押金看得比命重，把目标算得比心准。报酬到账之前，你的准星从不撒谎。",
    ),
    RoleCard(
        key="mist",
        name="迷雾",
        callsign="Mist",
        title="情报掮客",
        emoji="🌫️",
        color="#56d4dd",
        skills=("情报交易", "易容变声", "穿针引线"),
        desc="你贩卖的不是秘密，是选择。这座城市一半的暗流，都从你记不清脸的办公室经过。",
    ),
]

_ROLE_BY_KEY = {r.key: r for r in ROLES}


def get_role(key: str) -> RoleCard | None:
    """按 key 取角色卡；未知返回 None。"""
    return _ROLE_BY_KEY.get(key)
