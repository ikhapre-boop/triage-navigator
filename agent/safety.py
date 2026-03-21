from __future__ import annotations
import re
from dataclasses import dataclass
from enum import Enum


class RiskLevel(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SafetyAssessment:
    risk_level: RiskLevel
    categories: list[str]
    should_escalate: bool
    escalation_message: str | None
    resources: list[dict]
    safe_to_proceed: bool


CRITICAL_SIGNALS = {
    "suicide": ["suicid", "kill myself", "end my life", "don't want to live",
                "want to die", "better off dead", "no reason to live", "taking my life"],
    "self_harm": ["cut myself", "hurt myself", "self harm", "self-harm", "burning myself"],
    "immediate_danger": ["someone is hurting me", "being abused right now", "help me please",
                         "he's going to kill", "she's going to kill", "in danger right now",
                         "call the police", "being attacked"],
    "child_danger": ["my child is", "my kids are", "child abuse", "someone touched",
                     "hurting my baby"],
}

HIGH_SIGNALS = {
    "domestic_violence": ["hitting me", "beats me", "afraid of my partner",
                          "domestic violence", "abusive relationship", "he hits", "she hits"],
    "homelessness_crisis": ["sleeping on the street", "nowhere to sleep tonight",
                            "living in my car", "evicted today", "kicked out tonight"],
    "severe_mental_health": ["having a breakdown", "can't stop crying", "panic attack",
                             "hearing voices", "seeing things", "psychosis"],
}

MEDIUM_SIGNALS = {
    "food_insecurity": ["can't afford food", "out of food", "hungry", "no groceries",
                        "food stamps", "snap benefits", "food bank"],
    "housing": ["eviction", "evicted", "behind on rent", "foreclosure", "homeless",
                "shelter", "affordable housing"],
    "mental_health": ["depressed", "anxiety", "mental health", "therapist",
                      "counseling", "feeling hopeless", "overwhelmed"],
    "substance_abuse": ["addiction", "alcoholic", "drug problem", "rehab",
                        "recovery", "withdrawal", "sober"],
    "financial": ["can't pay bills", "debt", "utilities shut off", "can't afford",
                  "financial help", "assistance"],
}

CRISIS_RESOURCES = {
    "suicide": [
        {"name": "988 Suicide & Crisis Lifeline", "action": "Call or text 988", "note": "Free, confidential, 24/7"},
        {"name": "Crisis Text Line", "action": "Text HOME to 741741", "note": "Free, confidential, 24/7"},
    ],
    "domestic_violence": [
        {"name": "National Domestic Violence Hotline", "action": "Call 1-800-799-7233", "note": "Free, confidential, 24/7"},
        {"name": "Crisis Text Line", "action": "Text START to 88788", "note": "If it's not safe to call"},
    ],
    "immediate_danger": [
        {"name": "Emergency Services", "action": "Call 911", "note": "For immediate physical danger"},
        {"name": "National Domestic Violence Hotline", "action": "Call 1-800-799-7233", "note": "24/7 safety planning"},
    ],
    "child_danger": [
        {"name": "Emergency Services", "action": "Call 911", "note": "For immediate danger"},
        {"name": "Childhelp National Child Abuse Hotline", "action": "Call 1-800-422-4453", "note": "24/7"},
    ],
}


def assess_safety(message: str) -> SafetyAssessment:
    msg = message.lower()
    found_categories: list[str] = []

    for category, signals in CRITICAL_SIGNALS.items():
        if any(signal in msg for signal in signals):
            found_categories.append(category)

    if found_categories:
        resources = []
        for cat in found_categories:
            resources.extend(CRISIS_RESOURCES.get(cat, CRISIS_RESOURCES.get("suicide", [])))
        seen = set()
        unique_resources = []
        for r in resources:
            if r["name"] not in seen:
                seen.add(r["name"])
                unique_resources.append(r)

        return SafetyAssessment(
            risk_level=RiskLevel.CRITICAL,
            categories=found_categories,
            should_escalate=True,
            escalation_message=_build_escalation_message(found_categories, unique_resources),
            resources=unique_resources,
            safe_to_proceed=False,
        )

    high_found = []
    for category, signals in HIGH_SIGNALS.items():
        if any(signal in msg for signal in signals):
            high_found.append(category)

    if high_found:
        resources = []
        for cat in high_found:
            resources.extend(CRISIS_RESOURCES.get(cat, []))

        return SafetyAssessment(
            risk_level=RiskLevel.HIGH,
            categories=high_found,
            should_escalate=True,
            escalation_message=_build_high_risk_message(high_found, resources),
            resources=resources,
            safe_to_proceed=True,
        )

    medium_found = []
    for category, signals in MEDIUM_SIGNALS.items():
        if any(signal in msg for signal in signals):
            medium_found.append(category)

    return SafetyAssessment(
        risk_level=RiskLevel.MEDIUM if medium_found else RiskLevel.NONE,
        categories=medium_found,
        should_escalate=False,
        escalation_message=None,
        resources=[],
        safe_to_proceed=True,
    )


def _build_escalation_message(categories: list[str], resources: list[dict]) -> str:
    lines = [
        "I want to make sure you get the right support right away.",
        "",
        "**If you or someone you know is in immediate danger, please call 911.**",
        "",
        "Here are free, confidential resources available right now:",
        "",
    ]
    for r in resources:
        lines.append(f"🆘 **{r['name']}** — {r['action']}  \n   _{r['note']}_")
        lines.append("")
    lines += [
        "---",
        "I'm still here and can help you find additional local resources once you're safe.",
    ]
    return "\n".join(lines)


def _build_high_risk_message(categories: list[str], resources: list[dict]) -> str:
    lines = [
        "Before we look for resources together, I want to share some immediate options:",
        "",
    ]
    for r in resources:
        lines.append(f"📞 **{r['name']}** — {r['action']}  \n   _{r['note']}_")
        lines.append("")
    lines += [
        "---",
        "Now let me also search for local resources that might help with your situation.",
    ]
    return "\n".join(lines)


def is_veteran_context(message: str) -> bool:
    signals = ["veteran", "military", "army", "navy", "marines", "air force",
               "coast guard", "va ", "va.", "served in", "deployment"]
    msg = message.lower()
    return any(s in msg for s in signals)