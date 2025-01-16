from __future__ import annotations
from firebase_admin import firestore


class DocumentNotFoundError(Exception):
    def __init__(self, message: str):
        super().__init__(message)


class Trend:
    COLLECTION_NAME = "trends"
    DEFAULT_REMAINING_USAGE = 100

    def __init__(
        self,
        user_id: str,
        title: str,
        topic: str,
        body: str,
        keywords: list[str],
        queries: list[str],
        monthly_usage: int,
        remaining_usage: int,
    ):
        self.user_id = user_id
        self.title = title
        self.topic = topic
        self.body = body
        self.keywords = keywords
        self.queries = queries
        self.monthly_usage = monthly_usage
        self.remaining_usage = remaining_usage

    @staticmethod
    def get(db: firestore.Client, user_id: str) -> "Trend":
        doc = db.collection(Trend.COLLECTION_NAME).document(user_id).get()
        if not doc.exists:
            raise DocumentNotFoundError(
                f"Document with user_id '{user_id}' not found in collection '{Trend.COLLECTION_NAME}'."
            )

        data = doc.to_dict()
        title = data.get("title", "")
        topic = data.get("topic", "")
        body = data.get("body", "")
        keywords = data.get("keywords", [])
        queries = data.get("queries", [])
        monthly_usage = data.get("monthly_usage", 0)
        remaining_usage = data.get("remaining_usage", Trend.DEFAULT_REMAINING_USAGE)

        if not isinstance(keywords, list):
            raise ValueError("The 'keywords' field must be a list of strings.")
        if not isinstance(queries, list):
            raise ValueError("The 'queries' field must be a list of strings.")

        return Trend(
            user_id=user_id,
            title=title,
            topic=topic,
            body=body,
            keywords=keywords,
            queries=queries,
            monthly_usage=monthly_usage,
            remaining_usage=remaining_usage,
        )
