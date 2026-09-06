"""API 路由层：战役大厅 + 多人跑团 + 场景卡 + 剧情树 + TTS。

全部按"战役（game/session）"隔离：
  /api/roles                预设角色目录
  /api/games                战役列表 / 新建
  /api/games/{gid}          战役详情（含成员）
  /api/games/{gid}/join     选择角色加入
  /api/games/{gid}/players  战役内玩家
  /api/games/{gid}/messages 消息历史（多人轮询，after_id 增量）
  /api/games/{gid}/chat     SSE 流式剧情（多玩家）
  /api/games/{gid}/story    剧情分支树
  /api/games/{gid}/scene    场景卡（触发 + 状态查询）
  /api/tts                  语音合成
"""
import re
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, Response, StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session as DbSession

from src.infra import player_repository, session_repository
from src.infra.database import get_db
from src.services import dice_service, dm_engine, scene_service, story_tree, tts_service
from src.services.role_catalog import ROLES, get_role

router = APIRouter(prefix="/api")

DbDep = Annotated[DbSession, Depends(get_db)]


def _msg_to_dict(m) -> dict:
    """消息序列化（供多人轮询与前端渲染）。"""
    return {
        "id": m.id,
        "role": m.role,
        "player": m.player,
        "content": m.content,
        "nonce": m.nonce,
        "created_at": m.created_at.isoformat() if m.created_at else "",
    }


def _player_to_dict(p) -> dict:
    """玩家序列化。"""
    return {
        "id": p.id,
        "role_key": p.role_key,
        "name": p.name,
        "color": p.color,
    }


def _game_to_dict(db: DbSession, session) -> dict:
    """战役详情（含成员与统计）。"""
    players = player_repository.list_players(db, session.id)
    messages = session_repository.list_messages(db, session.id)
    return {
        "id": session.id,
        "name": session.name,
        "scene": session.scene,
        "created_at": session.created_at.isoformat() if session.created_at else "",
        "player_count": len(players),
        "message_count": len(messages),
        "players": [_player_to_dict(p) for p in players],
    }


def _get_game_or_404(db: DbSession, gid: int):
    """取战役会话，不存在返回 404 响应。"""
    session = session_repository.get_session(db, gid)
    if session is None:
        return JSONResponse(status_code=404, content={"detail": "战役不存在"})
    return session


class CreateGameRequest(BaseModel):
    """新建战役请求体。"""

    name: str


class JoinRequest(BaseModel):
    """加入战役请求体。"""

    role_key: str


class ChatRequest(BaseModel):
    """对话请求体。"""

    content: str = ""  # 玩家行动内容（resolve=True 时忽略）
    player_name: str = "冒险者"  # 多玩家：当前行动玩家（角色代号）
    nonce: str = ""  # 客户端请求标识（多端去重）
    resolve: bool = False  # True=只结算最近一次掷骰，不再追加新行动


def _strip_action_prefix(text: str) -> str:
    """去掉消息存储用的 [名字的行动] 前缀。"""
    return re.sub(r"^\[[^\]]*\]\s*", "", text)


class RollRequest(BaseModel):
    """掷骰检定请求体。"""

    player_name: str
    formula: str = "1d20"  # 骰子公式，如 1d20 / 2d6 / 1d20+3
    difficulty: int = 12  # 难度 DC
    nonce: str = ""


INTRO_TEMPLATE = (
    "夜色把这座城吞进霓虹里，雨丝混着冷却液的气味落在你的肩头。"
    "一条新的委托正等在暗处——你们的队伍已经集结，第一步，往哪走？"
)

# 外部大模型不可用时的本地兜底剧情（让演示/离线也能继续推进）
FALLBACK_DM = (
    "雨陡然大了，霓虹在水洼里碎成一片一片。巷口传来轮胎碾过积水的闷响——"
    "一辆没有牌照的黑色浮空车停在暗处，车灯闪了两下，像在等人上车。"
    "后视镜里，有人正朝你们的方向走来。你们打算怎么办？"
)


@router.get("/roles")
def list_roles():
    """预设角色目录（进入战役前选择）。"""
    return {
        "roles": [
            {
                "key": r.key,
                "name": r.name,
                "callsign": r.callsign,
                "title": r.title,
                "emoji": r.emoji,
                "color": r.color,
                "skills": list(r.skills),
                "desc": r.desc,
            }
            for r in ROLES
        ]
    }


@router.get("/games")
def list_games(db: DbDep):
    """战役列表（大厅展示，新的在前）。"""
    return {
        "games": [_game_to_dict(db, s) for s in session_repository.list_sessions(db)]
    }


@router.post("/games")
def create_game(req: CreateGameRequest, db: DbDep):
    """新建一场战役，返回详情与开场白。"""
    name = req.name.strip() or "无名委托"
    session = session_repository.create_session(db, name)
    return {"game": _game_to_dict(db, session), "intro": INTRO_TEMPLATE}


@router.get("/games/{gid}")
def get_game(gid: int, db: DbDep):
    """战役详情。"""
    session = _get_game_or_404(db, gid)
    if isinstance(session, JSONResponse):
        return session
    return {"game": _game_to_dict(db, session)}


@router.post("/games/{gid}/join")
def join_game(gid: int, req: JoinRequest, db: DbDep):
    """选择预设角色加入战役。角色名已被占用则 409。"""
    session = _get_game_or_404(db, gid)
    if isinstance(session, JSONResponse):
        return session
    role = get_role(req.role_key.strip())
    if role is None:
        return JSONResponse(status_code=400, content={"detail": "未知角色"})
    if player_repository.name_taken(db, gid, role.name):
        return JSONResponse(
            status_code=409,
            content={"detail": f"角色「{role.name}」已被其他玩家加入"},
        )
    player = player_repository.add_player(
        db, gid, role_key=role.key, name=role.name, color=role.color
    )
    return {"player": _player_to_dict(player)}


@router.get("/games/{gid}/players")
def list_game_players(gid: int, db: DbDep):
    """战役内玩家（多端加入名单）。"""
    session = _get_game_or_404(db, gid)
    if isinstance(session, JSONResponse):
        return session
    return {"players": [_player_to_dict(p) for p in player_repository.list_players(db, gid)]}


@router.get("/games/{gid}/messages")
def game_messages(gid: int, after_id: int = 0, db: DbDep = None):
    """消息历史（增量：只返回 id>after_id 的），供多人轮询。"""
    session = _get_game_or_404(db, gid)
    if isinstance(session, JSONResponse):
        return session
    msgs = session_repository.list_messages_after(db, gid, after_id)
    return {"messages": [_msg_to_dict(m) for m in msgs]}


@router.post("/games/{gid}/chat")
def chat(gid: int, req: ChatRequest, db: DbDep):
    """玩家输入 → DM 剧情生成（SSE 流式），保存到该战役历史。"""
    session = _get_game_or_404(db, gid)
    if isinstance(session, JSONResponse):
        return session

    # 读取该战役完整历史（多人共享同一上下文）
    msgs = session_repository.list_messages(db, gid)
    history = [{"role": m.role, "content": m.content} for m in msgs]

    # 战役内玩家名单（DM 状态栏使用，增强队伍感）
    roster = [p.name for p in player_repository.list_players(db, gid)]

    if req.resolve:
        # 结算模式：不追加新行动，直接结算该玩家最近一次掷骰
        dice = next(
            (
                m
                for m in reversed(msgs)
                if m.role == "user"
                and m.player == req.player_name
                and "🎲" in m.content
            ),
            None,
        )
        if dice is None:
            return JSONResponse(status_code=400, content={"detail": "请先掷骰（🎲），我再帮你结算"})
        user_input = _strip_action_prefix(dice.content)
    else:
        # 保存玩家本次行动（含玩家名与 nonce，供追溯/去重）
        session_repository.save_message(
            db,
            gid,
            "user",
            f"[{req.player_name}的行动] {req.content}",
            player=req.player_name,
            nonce=req.nonce,
        )
        user_input = req.content

    try:
        stream = dm_engine.generate_stream(
            session,
            history,
            user_input,
            player_name=req.player_name,
            roster=roster,
        )

        def gen_with_fallback():
            """流式输出剧情，结束后保存 DM 回复（沿用同一 nonce）。

            模型异常（网络/额度/无 Key）时降级为本地预设剧情，
            保证演示现场对话永不中断、不红屏。
            """
            collected: list[str] = []
            try:
                for chunk in stream:
                    collected.append(chunk)
                    yield chunk
            except Exception:  # noqa: BLE001  外部模型异常 → 本地兜底
                suffix = "" if collected else "\n（此刻你耳边只有雨声和远处警笛的回响……）"
                text = FALLBACK_DM + suffix
                if text not in collected:
                    collected.append(text)
                    yield text
            if collected:
                session_repository.save_message(
                    db, gid, "assistant", "".join(collected), nonce=req.nonce
                )

        return StreamingResponse(gen_with_fallback(), media_type="text/event-stream")
    except dm_engine.InputError as e:
        return JSONResponse(status_code=400, content={"detail": str(e)})


@router.post("/games/{gid}/roll")
def roll_dice(gid: int, req: RollRequest, db: DbDep):
    """掷骰检定：真随机判定 + 记录入库 + 广播给全队。

    掷骰作为一条行动消息落库（队友轮询可见、后续进入 DM 上下文）。
    """
    session = _get_game_or_404(db, gid)
    if isinstance(session, JSONResponse):
        return session
    if not 1 <= req.difficulty <= 30:
        return JSONResponse(status_code=400, content={"detail": "难度需在 1~30 之间"})
    try:
        check = dice_service.perform_check(req.formula, req.difficulty)
    except dice_service.DiceError as e:
        return JSONResponse(status_code=400, content={"detail": str(e)})

    verdict = "成功" if check.success else "失败"
    content = (
        f"[{req.player_name}的行动] 🎲 骰子检定 {check.formula}"
        f" 结果 {check.result}（难度 {check.difficulty}）→ {verdict}"
    )
    msg = session_repository.save_message(
        db, gid, "user", content, player=req.player_name, nonce=req.nonce
    )
    session_repository.save_dice_roll(
        db,
        gid,
        formula=check.formula,
        result=check.result,
        difficulty=check.difficulty,
        success=check.success,
        reason=f"{req.player_name} 请求检定",
    )
    return {
        "dice": {
            "formula": check.formula,
            "result": check.result,
            "difficulty": check.difficulty,
            "success": check.success,
        },
        "message": _msg_to_dict(msg),
    }


@router.get("/games/{gid}/story")
def game_story(gid: int, db: DbDep):
    """剧情分支树：由该战役历史重建，供前端可视化。"""
    session = _get_game_or_404(db, gid)
    if isinstance(session, JSONResponse):
        return session
    messages = [
        {"role": m.role, "content": m.content}
        for m in session_repository.list_messages(db, gid)
    ]
    tree = story_tree.tree_from_messages(session.name, messages)
    return {"game_id": gid, "title": session.name, "tree": tree}


@router.post("/games/{gid}/scene")
def trigger_scene(gid: int, force: bool = False, db: DbDep = None):
    """触发生成场景图：用最近一段 DM 剧情做生图 Prompt，返回待轮询任务。

    异步执行不阻塞对话；同战役去重 + 冷却（见 SceneCards.ensure）。
    force=True 用于前端"再画一张"按钮，无视冷却立即新建。
    """
    session = _get_game_or_404(db, gid)
    if isinstance(session, JSONResponse):
        return session
    stories = [
        m.content
        for m in session_repository.list_messages(db, gid)
        if m.role == "assistant"
    ]
    if not stories:
        return JSONResponse(
            status_code=400, content={"detail": "还没有剧情，先让 DM 推进一段剧情"}
        )
    task_id = scene_service.scene_cards.ensure(
        gid, session.scene, stories[-1], force=force
    )
    return scene_service.scene_cards.task(task_id)


@router.get("/games/{gid}/scene/task/{task_id}")
def scene_task(gid: int, task_id: int):
    """查询生图任务状态（前端轮询）。"""
    task = scene_service.scene_cards.task(task_id)
    if task is None:
        return JSONResponse(status_code=404, content={"detail": "任务不存在"})
    return task


@router.get("/tts")
def tts(text: str) -> Response:
    """语音合成：把文本转成 mp3 音频返回（edge-tts）。"""
    if not text or not text.strip():
        return JSONResponse(status_code=400, content={"detail": "文本不能为空"})
    audio = tts_service.synthesize(text[:400])  # 单段上限，前端自行切块
    return Response(content=audio, media_type="audio/mpeg")
