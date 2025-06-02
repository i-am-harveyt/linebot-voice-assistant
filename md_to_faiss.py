import os
import glob
import pickle
import faiss
import openai
from tqdm import tqdm
from sklearn.preprocessing import normalize

# 初始化 OpenAI API
openai.api_key = os.getenv("OPENAI_API_KEY")

# 設定參數
MARKDOWN_DIR = "./disease_intro_md/"
INDEX_OUTPUT_PATH = "disease_index.faiss"
METADATA_OUTPUT_PATH = "disease_metadata.pkl"
CHUNK_SIZE = 300  # 字數（可調整）
EMBEDDING_MODEL = "text-embedding-ada-002"

# 切 chunk 函數
def chunk_text(text: str, size: int = CHUNK_SIZE) -> list[str]:
    return [text[i:i+size] for i in range(0, len(text), size)]

# 取得 embedding（OpenAI）
def get_embedding(text: str) -> list[float]:
    response = openai.embeddings.create(
        input=text,
        model=EMBEDDING_MODEL
    )
    return response.data[0].embedding

# 主程序
def process_markdown_dir():
    md_files = glob.glob(os.path.join(MARKDOWN_DIR, "*.md"))
    embeddings = []
    metadata = []

    for file_path in tqdm(md_files, desc="Processing files"):
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read().strip()

        if len(content) < 50:
            continue  # 忽略內容太短的檔案

        filename = os.path.basename(file_path)
        chunks = chunk_text(content)

        for i, chunk in enumerate(chunks):
            try:
                emb = get_embedding(chunk)
                embeddings.append(emb)
                metadata.append({
                    "filename": filename,
                    "chunk_id": i,
                    "content": chunk
                })
            except Exception as e:
                print(f"⚠️ Error embedding chunk {i} in {filename}: {e}")

    # 建立 FAISS index
    if not embeddings:
        print("❌ 沒有有效的內容可以建立索引")
        return

    dim = len(embeddings[0])
    index = faiss.IndexFlatL2(dim)
    index.add(normalize_embeddings(embeddings))

    faiss.write_index(index, INDEX_OUTPUT_PATH)
    with open(METADATA_OUTPUT_PATH, "wb") as f:
        pickle.dump(metadata, f)

    print(f"完成：共儲存 {len(embeddings)} 筆 embedding")

# Embedding normalization（重要！可提升準確率）
def normalize_embeddings(vectors: list[list[float]]):
    import numpy as np
    return normalize(np.array(vectors), axis=1)

if __name__ == "__main__":
    process_markdown_dir()
