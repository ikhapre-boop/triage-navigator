import json
import os
from pathlib import Path
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain.schema import Document

load_dotenv()

CHROMA_DIR = Path(__file__).parent.parent / "chroma_db"
SEED_FILE = Path(__file__).parent / "seed_resources.json"


def load_seed_resources() -> list[Document]:
    with open(SEED_FILE, "r") as f:
        resources = json.load(f)

    docs = []
    for r in resources:
        content = (
            f"Name: {r['name']}\n"
            f"Type: {r['type']}\n"
            f"Description: {r['description']}\n"
            f"Services: {', '.join(r.get('services', []))}\n"
            f"Coverage: {r.get('coverage', 'National or varies')}\n"
            f"Phone: {r.get('phone', 'See website')}\n"
            f"Website: {r.get('website', '')}\n"
            f"Hours: {r.get('hours', 'Varies')}\n"
            f"Eligibility: {r.get('eligibility', 'Open to all')}"
        )
        docs.append(Document(
            page_content=content,
            metadata={
                "name": r["name"],
                "type": r["type"],
                "phone": r.get("phone", ""),
                "website": r.get("website", ""),
                "source": "seed",
                "id": r.get("id", r["name"].lower().replace(" ", "_")),
            }
        ))
    print(f"  Loaded {len(docs)} seed resources")
    return docs


def build_vector_store(docs: list[Document], reset: bool = False) -> Chroma:
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

    if reset and CHROMA_DIR.exists():
        import shutil
        shutil.rmtree(CHROMA_DIR)
        print("  Cleared existing vector store")

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)

    vectorstore = Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        persist_directory=str(CHROMA_DIR),
        collection_name="civic_resources",
    )
    print(f"  Stored {len(docs)} documents in vector store")
    return vectorstore


if __name__ == "__main__":
    print("=== Building Triage Navigator Vector Store ===\n")
    print("Loading seed resources...")
    docs = load_seed_resources()
    print(f"\nEmbedding {len(docs)} documents... (takes ~30 seconds)")
    build_vector_store(docs, reset=True)
    print("\n✅ Done! Run: streamlit run ui/app.py")