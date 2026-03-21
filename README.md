# 🧭 Community Triage Navigator

> A RAG-powered AI agent that helps people in underserved communities find free, local support resources — with built-in safety guardrails for crisis situations.

**Live demo:** [your-app.streamlit.app](https://streamlit.io) *(deploy and update this link)*

---

## What It Does

People in crisis often don't know what kind of help exists or how to access it. 211 hotlines are overloaded, Google returns noise, and resource databases are stale. This app puts a conversational AI triage layer on top of verified civic resource data, so someone can describe their situation in plain language and get immediate, relevant help.

**Key capabilities:**
- Conversational triage — asks clarifying questions to understand the situation
- Semantic resource retrieval — finds the most relevant resources, not just keyword matches
- Multi-category support — food, housing, mental health, legal aid, utilities, healthcare, domestic violence
- Crisis escalation — immediately surfaces hotlines when someone is in danger, *before* any RAG lookup
- Veteran detection — flags VA-specific resources when relevant
- Feedback collection — thumbs up/down on every response

---

## Architecture

```
User Message
     │
     ▼
┌─────────────────────┐
│   Safety Layer      │  ← Runs FIRST on every message
│   (agent/safety.py) │    Rule-based + keyword classifier
└─────────┬───────────┘
          │
    ┌─────┴──────┐
    │            │
CRITICAL      SAFE TO
RISK?         PROCEED
    │            │
    ▼            ▼
Show 988/911  LangChain Agent
immediately   (claude-sonnet)
              │
              ├─► classify_needs() tool
              ├─► search_resources() tool ──► ChromaDB (RAG)
              └─► get_crisis_resources() tool
                         │
                         ▼
                  Structured response
                  with cited resources
```

### Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| LLM | Claude (claude-sonnet) via Anthropic API | Best-in-class instruction following and empathetic tone |
| Agent framework | LangChain tool-calling agent | Clean tool use, easy to extend |
| Embeddings | OpenAI `text-embedding-3-small` | Fast, cheap, high quality |
| Vector store | ChromaDB (local) | No server needed, fast MMR retrieval |
| Frontend | Streamlit | Rapid deployment, shareable URL |
| Safety layer | Custom rule-based classifier | Fast, deterministic, no LLM latency on critical path |

---

## Data Sources

All free and publicly available:

| Source | Data Type | Access |
|--------|-----------|--------|
| Bundled seed data | 15 national hotlines and directories | Included in repo |
| [SAMHSA Locator API](https://findtreatment.samhsa.gov/developer) | Mental health & substance abuse facilities | Free API key |
| [HUD Housing Locator](https://www.huduser.gov) | Affordable housing resources | Free |
| [211.org](https://www.211.org) | General community resources | Open data |
| [Feeding America](https://www.feedingamerica.org) | Food banks | Public directory |

---

## Responsible AI Design

This project was built with responsible AI as a first-class concern, not an afterthought.

### Safety Layer (Most Important)
The safety classifier runs **before** the LLM on every message. It's rule-based (not LLM-based) so it has:
- Zero latency
- Deterministic behavior
- No dependency on model availability

Crisis signals trigger immediate display of 988/911/DV hotline numbers. The LLM never sees the message until safety is cleared.

### What the App Won't Do
- Give medical, legal, or financial advice
- Store user data
- Make promises about outcomes
- Replace licensed professionals

### Disclaimer
A visible disclaimer appears on every page load. The sidebar always shows crisis numbers regardless of conversation state.

### Feedback Loop
Every response has 👍/👎 buttons. In production, this feeds a database for continuous improvement.

---

## Setup & Installation

### Prerequisites
- Python 3.11+
- Anthropic API key (for Claude)
- OpenAI API key (for embeddings only — ~$0.01 total to build the vector store)

### 1. Clone and install

```bash
git clone https://github.com/yourusername/triage-navigator
cd triage-navigator
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and add your API keys
```

### 3. Build the vector store

```bash
python data/ingest.py
```

This embeds the seed resources and any live API data into ChromaDB. Takes ~30 seconds. Only needs to run once (or when you add new resources).

### 4. Run the app

```bash
streamlit run ui/app.py
```

Open [http://localhost:8501](http://localhost:8501)

### 5. Run tests

```bash
pytest tests/ -v
```

---

## Deploying to Streamlit Cloud (Free)

1. Push this repo to GitHub *(make sure `.env` is in `.gitignore`)*
2. Go to [share.streamlit.io](https://share.streamlit.io) → New app
3. Point to `ui/app.py`
4. Add your API keys in **Settings → Secrets**:
   ```toml
   ANTHROPIC_API_KEY = "sk-ant-..."
   OPENAI_API_KEY = "sk-..."
   ```
5. Deploy — you get a public URL instantly

**Note on ChromaDB:** For Streamlit Cloud, the vector store rebuilds on each cold start. For production, swap ChromaDB for a hosted vector DB like Pinecone or Weaviate.

---

## Project Structure

```
triage-navigator/
├── agent/
│   ├── safety.py          # Crisis detection + escalation (runs first)
│   └── triage_agent.py    # LangChain agent + tools
├── data/
│   ├── ingest.py          # Vector store builder
│   └── seed_resources.json # 15 national resources (no API key needed)
├── ui/
│   └── app.py             # Streamlit frontend
├── tests/
│   └── test_safety.py     # Safety layer unit tests
├── .streamlit/
│   └── config.toml        # Theme config
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Extending the Project

Ideas for taking this further:

- **Add more data sources** — scrape local United Way directories, county social services sites
- **Location-aware filtering** — use `geopy` to filter resources by proximity to user's zip code
- **Map view** — `streamlit-folium` is already in requirements, add a map of nearby resources
- **Multilingual support** — Claude handles Spanish natively, add a language selector
- **Admin dashboard** — view aggregated (anonymized) feedback and common queries
- **Pinecone/Weaviate** — swap ChromaDB for a hosted vector DB to support deployment at scale

---

## Design Decisions & Tradeoffs

**Why rule-based safety instead of LLM-based?**
Speed and reliability. LLM classification adds 1-2 seconds of latency and can fail if the API is down. For crisis detection, determinism matters more than sophistication.

**Why Claude for the agent LLM?**
Claude's instruction-following is excellent for the constrained role (navigator, not advisor), and its tone is naturally warm without being sycophantic. The system prompt is tight enough that GPT-4o works equally well.

**Why ChromaDB instead of Pinecone?**
Zero infrastructure for a portfolio project. The tradeoff is that the index rebuilds on cold start in cloud deployments. For production, Pinecone or Weaviate would be the upgrade.

**Why MMR retrieval instead of similarity search?**
Maximum Marginal Relevance reduces duplicate results when multiple resources are semantically similar (e.g., two food banks with identical descriptions). The user gets 5 diverse, relevant results instead of 5 variations of the same thing.

---

## License

MIT — free to use, fork, and deploy.

---

*Built to demonstrate RAG pipelines, LangChain agents, responsible AI design, and full-stack AI deployment. Questions? Open an issue.*
