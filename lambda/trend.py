from __future__ import annotations
from firebase_admin import firestore


class DocumentNotFoundError(Exception):
    def __init__(self, message: str):
        super().__init__(message)


class InvalidDigestsError(Exception):
    def __init__(self, message: str):
        super().__init__(message)


class TrendDigest:
    def __init__(self, index: int, title: str, body: str):
        self.index = index
        self.title = title
        self.body = body


class Trend:
    COLLECTION_NAME = "trends"

    def __init__(
        self,
        user_id: str,
        title: str,
        topic: str,
        body: str,
        keywords: list[str],
        queries: list[str] = None,
    ):
        if queries is None:
            queries = []
        self.user_id = user_id
        self.title = title
        self.topic = topic
        self.body = body
        self.keywords = keywords
        self.queries = queries

    @staticmethod
    def get(db: firestore.Client, user_id: str) -> "Trend":
        doc = db.collection(Trend.COLLECTION_NAME).document(user_id).get()
        if not doc.exists:
            raise DocumentNotFoundError(
                f"Document with user_id '{user_id}' not found in collection '{Trend.COLLECTION_NAME}'."
            )

        title = doc.get("title")
        topic = doc.get("topic")
        body = doc.get("body")
        keywords = doc.get("keywords")
        queries = doc.get("queries")

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
        )
