from openai import AsyncOpenAI
from app.core.config import settings
from typing import List

class QuestionVectorizer:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.OPENROUTER_API_KEY,
            base_url=settings.OPENROUTER_BASE_URL
        )
        self.model = settings.EMBEDDING_MODEL

    async def get_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for the given text using OpenRouter/OpenAI API.
        """
        if not settings.OPENROUTER_API_KEY:
            raise ValueError("OPENROUTER_API_KEY is not set")
            
        response = await self.client.embeddings.create(
            input=text,
            model=self.model
        )
        return response.data[0].embedding

vectorizer = QuestionVectorizer()
