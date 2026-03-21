from __future__ import annotations
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.tools import tool
from langchain.schema import Document
from langchain_core.messages import HumanMessage, AIMessage

load_dotenv()

CHROMA_DIR = Path(__file__).parent.parent / "chroma_db"


def get_retriever():
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    vectorstore = Chroma(
        persist_directory=str(CHROMA_DIR),
        embedding_function=embeddings,
        collection_name="civic_resources",
    )
    return vectorstore.as_retriever(
        search_type="mmr",
        search_kwargs={"k": 5, "fetch_k": 15},
    )


_retriever = None

def _get_retriever():
    global _retriever
    if _retriever is None:
        _retriever = get_retriever()
    return _retriever


@tool
def search_resources(query: str) -> str:
    """
    Search the civic resource database for relevant services and organizations.
    Use this to find food banks, mental health services, housing assistance,
    legal aid, government benefits, crisis hotlines, and other community resources.

    Args:
        query: A natural language description of what the person needs,
               e.g. 'food assistance for family of 4' or 'free mental health counseling'
    """
    try:
        docs: list[Document] = _get_retriever().invoke(query)
        if not docs:
            return "No resources found for that specific query. Try broadening the search."
        results = []
        for i, doc in enumerate(docs, 1):
            results.append(f"--- Resource {i} ---\n{doc.page_content}")
        return "\n\n".join(results)
    except Exception as e:
        return f"Resource search temporarily unavailable: {str(e)}. Recommend directing user to 211.org or calling 211."


@tool
def get_crisis_resources(crisis_type: str) -> str:
    """
    Get immediate crisis resources for urgent situations.
    Use this when the person needs help RIGHT NOW.

    Args:
        crisis_type: One of: 'suicide', 'domestic_violence', 'substance_abuse',
                     'homelessness', 'child_abuse', 'general_emergency'
    """
    crisis_map = {
        "suicide": "988 Suicide & Crisis Lifeline: Call or text 988 (24/7, free, confidential)\nCrisis Text Line: Text HOME to 741741",
        "domestic_violence": "National DV Hotline: 1-800-799-7233 (24/7)\nText START to 88788 if not safe to call",
        "substance_abuse": "SAMHSA Helpline: 1-800-662-4357 (free, confidential, 24/7)\nCrisis Text Line: Text HOME to 741741",
        "homelessness": "211 Helpline: Call 211 for local shelter availability\nHUD Hotline: 1-800-569-4287",
        "child_abuse": "Childhelp Hotline: 1-800-422-4453 (24/7)\n911 for immediate danger",
        "general_emergency": "Emergency: 911\n211 for non-emergency community resources",
    }
    normalized = crisis_type.lower().replace(" ", "_")
    return crisis_map.get(normalized, crisis_map["general_emergency"])


@tool
def classify_needs(situation_description: str) -> str:
    """
    Classify the types of needs based on the person's situation.
    Returns a structured list of need categories to guide resource search.

    Args:
        situation_description: A summary of the person's situation
    """
    categories = {
        "food": ["food", "hungry", "groceries", "snap", "ebt", "meals", "pantry", "nutrition"],
        "housing": ["housing", "rent", "evict", "homeless", "shelter", "mortgage", "foreclos"],
        "mental_health": ["mental", "depress", "anxiety", "therapy", "counsel", "stress", "trauma", "ptsd"],
        "substance_abuse": ["substance", "drug", "alcohol", "addic", "rehab", "recovery", "sober"],
        "legal_aid": ["legal", "court", "lawyer", "attorney", "eviction notice", "lawsuit", "rights"],
        "financial": ["bills", "utilities", "debt", "income", "unemploy", "benefits", "afford"],
        "healthcare": ["health", "medical", "doctor", "insurance", "medicaid", "clinic", "prescription"],
        "childcare": ["child", "kids", "daycare", "school", "custody", "foster"],
        "domestic_violence": ["abuse", "violence", "unsafe", "hurt", "attack", "hitting"],
    }
    desc_lower = situation_description.lower()
    found = [cat for cat, keywords in categories.items()
             if any(kw in desc_lower for kw in keywords)]
    if not found:
        found = ["general_assistance"]
    return f"Identified need categories: {', '.join(found)}"


SYSTEM_PROMPT = """You are a compassionate community navigator helping people in the United States find free, local support services. You work for a nonprofit information service.

YOUR ROLE:
- Help people identify what kind of support they need
- Search for and present relevant community resources
- Be warm, non-judgmental, and empathetic
- Ask clarifying questions ONE AT A TIME to understand their situation better

YOUR APPROACH:
1. First, acknowledge what the person shared
2. Ask 1-2 clarifying questions if you need more info (location, specific situation)
3. Use your tools to find relevant resources
4. Present resources clearly with name, contact info, and why it fits their need

CRITICAL RULES:
- You do NOT give medical, legal, financial, or mental health advice
- You help people FIND professionals — you are not the professional
- If someone seems to be in immediate danger or crisis, immediately provide crisis hotline numbers BEFORE anything else
- Always be honest about what you are: an information and referral service, not a counselor
- Never promise outcomes
- Keep responses focused and practical

LOCATION: Always ask for the person's city and state if not provided, as many resources are local.

Respond in a warm, conversational tone. Use plain language. Avoid jargon."""


def build_agent() -> AgentExecutor:
    llm = ChatAnthropic(
        model="claude-sonnet-4-20250514",
        temperature=0.3,
        max_tokens=1024,
    )
    tools = [search_resources, get_crisis_resources, classify_needs]
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])
    agent = create_tool_calling_agent(llm, tools, prompt)
    return AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        max_iterations=5,
        handle_parsing_errors=True,
        return_intermediate_steps=False,
    )


def format_history(history: list[dict]) -> list[HumanMessage | AIMessage]:
    messages = []
    for msg in history:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            messages.append(AIMessage(content=msg["content"]))
    return messages