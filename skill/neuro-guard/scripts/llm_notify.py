"""Generate fun, contextual notification messages via Gemini.

Falls back to static messages if the API is unavailable or the token
is missing. The daemon's core lock/unlock logic is never blocked by LLM calls.
"""

from __future__ import annotations

import json
import os
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

# API base URL from env; no default to avoid exposing production URL in open source
API_BASE = (os.environ.get("NEURO_GUARD_API_URL") or "").rstrip("/")
GEMINI_ENDPOINT = f"{API_BASE}/proxy/gemini/v1/chat/completions" if API_BASE else ""
TOKEN_PATH = Path.home() / ".neuro-guard-api-token"

STATIC_FALLBACK = {
    "WARN":       "明天有重要日程。建议开始收尾当前工作。",
    "DIM":        "距离必须休息时间不远了。请保存工作进度。",
    "FINAL_WARN": "最后提醒！15 分钟后将锁屏。请立即保存所有工作。",
    "LOCK":       "时间到。锁屏执行中。晚安。",
    "SNOOZE_OFFER": "你解锁了。需要延长时间吗？",
    "RE_LOCK":    "Grace period 结束。重新锁屏。",
}

TIER_PERSONA = {
    "WARN":       "友好的朋友，语气轻松幽默，带一点关心",
    "DIM":        "贴心的管家，语气温和但有紧迫感",
    "FINAL_WARN": "严肃的教练，语气坚定但有创意，不拖泥带水",
    "LOCK":       "一句话终结者，干脆利落，可以冷幽默",
    "SNOOZE_OFFER": "理解但坚定的谈判专家",
    "RE_LOCK":    "冷幽默旁白，'我说过的'既视感",
}


def _load_token() -> str | None:
    if TOKEN_PATH.exists():
        t = TOKEN_PATH.read_text().strip()
        return t if t else None
    return None


def _build_prompt(
    tier: str,
    now: datetime,
    event_time: str | None = None,
    event_title: str | None = None,
    warn_count: int = 0,
    snooze_count: int = 0,
) -> str:
    persona = TIER_PERSONA.get(tier, "友好的助手")
    weekday = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][now.weekday()]
    time_str = now.strftime("%H:%M")

    ctx_parts = [
        f"现在是{weekday} {time_str}",
        f"提醒级别: {tier}",
    ]
    if event_time:
        ctx_parts.append(f"明天最早的重要日程: {event_time}")
    if event_title:
        ctx_parts.append(f"日程内容: {event_title}")
    if warn_count > 0:
        ctx_parts.append(f"今天已经提醒了 {warn_count} 次")
    if snooze_count > 0:
        ctx_parts.append(f"已 snooze {snooze_count} 次")

    context = "\n".join(f"- {p}" for p in ctx_parts)

    return f"""你是一个 Mac 桌面通知文案生成器。角色设定: {persona}。

根据以下上下文，生成一条简短、有趣、中文的桌面通知文案（50字以内）。
不要加引号、不要加 emoji（macOS 通知不适合太多 emoji）、不要解释，直接输出文案。

上下文:
{context}

要求:
- 每次生成不同的内容，避免重复
- 可以引用当前时间、星期、日程等信息增加真实感
- {tier} 级别越高，语气越紧迫
- 偶尔可以用比喻、反问、或者吐槽的方式"""


def generate_message(
    tier: str,
    now: datetime | None = None,
    event_time: str | None = None,
    event_title: str | None = None,
    warn_count: int = 0,
    snooze_count: int = 0,
) -> str:
    """Generate a notification message. Returns static fallback on any failure."""
    if now is None:
        now = datetime.now()

    token = _load_token()
    if not token or not GEMINI_ENDPOINT:
        return STATIC_FALLBACK.get(tier, "")

    prompt = _build_prompt(tier, now, event_time, event_title, warn_count, snooze_count)

    payload = json.dumps({
        "model": "gemini-2.0-flash",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 100,
        "temperature": 0.9,
    }).encode()

    req = urllib.request.Request(
        GEMINI_ENDPOINT,
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read())
            msg = data["choices"][0]["message"]["content"].strip()
            # Trim quotes if the model wraps in them
            if msg.startswith('"') and msg.endswith('"'):
                msg = msg[1:-1]
            if msg.startswith("「") and msg.endswith("」"):
                msg = msg[1:-1]
            return msg
    except Exception as e:
        print(f"  [LLM] Fallback due to: {e}")
        return STATIC_FALLBACK.get(tier, "")
