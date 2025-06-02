from prompts.medical_advisor import (
    MEDICAL_ADVISOR_SYSTEM_PROMPT,
    format_medical_question,
)

import logging
import os
import pickle

import faiss
import numpy as np
from openai import OpenAI, embeddings
from sklearn.preprocessing import normalize

class AI:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.index = faiss.read_index("disease_index.faiss")
        with open("./disease_metadata.pkl", "rb") as f:
            self.metadata = pickle.load(f)

    def generate_gpt_response(self, paragraph: str, question: str) -> str:
        """Generate response using GPT"""
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": MEDICAL_ADVISOR_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": format_medical_question(paragraph, question),
                    },
                ],
                temperature=0.7,
                max_tokens=500,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logging.error(f"Error generating GPT response: {e}")
            return "抱歉，我現在無法回答這個問題。"

    def query_faiss(self, question: str, top_k: int = 3) -> list[str]:
        response = embeddings.create(
            input=question, model="text-embedding-ada-002"
        )
        query_vector = normalize(np.array([response.data[0].embedding]), axis=1)
        D, I = self.index.search(query_vector, top_k)

        results = []
        for idx in I[0]:
            results.append(self.metadata[idx]["content"])
        return results
