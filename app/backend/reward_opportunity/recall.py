"""Broad recall logic for reward-opportunity candidates."""

from __future__ import annotations

from typing import Any


RECALL_RULES = [
    {
        "label": "suspected_invite_reward",
        "opportunity_type": "invite_reward",
        "keywords": ("invite", "refer", "referral", "朋友", "邀请", "拉新"),
        "reward_keywords": ("reward", "bonus", "cash", "prize", "airdrop", "earn", "$", "奖励", "返现", "奖金"),
        "needs_detail_fetch": True,
    },
    {
        "label": "suspected_registration_reward",
        "opportunity_type": "registration_reward",
        "keywords": ("register", "sign up", "signup", "new user", "注册", "开户", "新用户"),
        "reward_keywords": ("reward", "bonus", "gift", "coupon", "cash", "奖励", "礼金", "券"),
        "needs_detail_fetch": True,
    },
    {
        "label": "suspected_task_reward",
        "opportunity_type": "task_reward",
        "keywords": ("task", "quest", "complete", "submit", "test", "check in", "mission", "任务", "投稿", "试玩", "打卡", "测试"),
        "reward_keywords": ("reward", "bounty", "points", "airdrop", "cash", "prize", "earn", "奖励", "积分", "赏金"),
        "needs_detail_fetch": True,
    },
]

NON_TARGET_HINTS = ("news", "analysis", "commentary", "rumor", "资讯", "评测", "讨论", "测评")


def recall_candidate_from_document(document: dict[str, Any]) -> dict[str, Any] | None:
    title = str(document.get("title") or "").strip()
    body = str(document.get("body") or "").strip()
    tags = " ".join(str(value) for value in (document.get("tags") or []))
    external_link_titles = " ".join(str(value) for value in (document.get("external_link_titles") or []))
    haystack = " ".join(part for part in (title, body, tags, external_link_titles) if part).lower()

    if not haystack:
        return None

    if any(hint in haystack for hint in NON_TARGET_HINTS) and not any(
        keyword in haystack for keyword in ("reward", "bonus", "cash", "$", "奖励", "返现", "积分", "赏金")
    ):
        return None

    best_match: dict[str, Any] | None = None
    best_score = 0
    for rule in RECALL_RULES:
        keyword_hits = [keyword for keyword in rule["keywords"] if keyword in haystack]
        reward_hits = [keyword for keyword in rule["reward_keywords"] if keyword in haystack]
        score = len(keyword_hits) * 2 + len(reward_hits)
        if keyword_hits and reward_hits and score > best_score:
            best_score = score
            best_match = {
                "source_platform": document["source_platform"],
                "source_url": document["source_url"],
                "title": title or str(document.get("source_url") or ""),
                "recall_label": rule["label"],
                "opportunity_type": rule["opportunity_type"],
                "recall_reason": f"matched {', '.join(keyword_hits[:2])} + {', '.join(reward_hits[:2])}",
                "trigger_patterns": keyword_hits[:3] + reward_hits[:3],
                "needs_detail_fetch": rule["needs_detail_fetch"],
            }

    return best_match
