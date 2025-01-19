from __future__ import annotations
from datetime import datetime, timezone
from firebase_admin import firestore


class DocumentNotFoundError(Exception):
    def __init__(self, message: str):
        super().__init__(message)


class News:
    MONTHLY_LIMIT = 100
    COLLECTION_NAME = "news"

    def __init__(
        self,
        user_id: str,
        keyword: str,
        language_code: str,
        introduction: str,
        articles: list,
        monthly_usage: int,
        remaining_usage: int,
        last_reset_date: str,
        doc_ref: firestore.DocumentReference,
    ):
        self.user_id = user_id
        self.keyword = keyword
        self.language_code = language_code
        self.introduction = introduction
        self.articles = articles
        self.monthly_usage = monthly_usage
        self.remaining_usage = remaining_usage
        self.last_reset_date = last_reset_date
        self.doc_ref = doc_ref

    @staticmethod
    def create(
        db: firestore.Client, user_id: str, keyword: str, language_code: str
    ) -> News:
        now = datetime.now(timezone.utc).isoformat()
        doc_ref = db.collection(News.COLLECTION_NAME).document(user_id)
        doc = doc_ref.get()

        introduction = None
        articles = []
        monthly_usage = 0
        remaining_usage = News.MONTHLY_LIMIT
        last_reset_date = now
        if doc.exists:
            doc_data = doc.to_dict()
            monthly_usage = doc_data.get("monthly_usage", 0)
            remaining_usage = doc_data.get("remaining_usage", News.MONTHLY_LIMIT)

        doc_ref.set(
            {
                "keyword": keyword,
                "language_code": language_code,
                "introduction": introduction,
                "articles": articles,
                "monthly_usage": monthly_usage,
                "remaining_usage": remaining_usage,
                "last_reset_date": last_reset_date,
            },
            merge=True,
        )

        return News(
            user_id=user_id,
            keyword=keyword,
            language_code=language_code,
            introduction=introduction,
            articles=articles,
            monthly_usage=monthly_usage,
            remaining_usage=remaining_usage,
            last_reset_date=last_reset_date,
            doc_ref=doc_ref,
        )

    @staticmethod
    def get(db: firestore.Client, user_id: str) -> News:
        doc_ref = db.collection(News.COLLECTION_NAME).document(user_id)
        doc = doc_ref.get()

        if not doc.exists:
            raise DocumentNotFoundError(
                f"Document with user_id '{user_id}' not found in collection '{News.COLLECTION_NAME}'."
            )

        doc_data = doc.to_dict()

        keyword = doc_data.get("keyword")
        language_code = doc_data.get("language_code")
        introduction = doc_data.get("introduction", "")
        articles = doc_data.get("articles", [])
        monthly_usage = doc_data.get("monthly_usage", 0)
        remaining_usage = doc_data.get("remaining_usage", News.MONTHLY_LIMIT)
        last_reset_date = doc_data.get("last_reset_date", "")

        return News(
            user_id=user_id,
            keyword=keyword,
            language_code=language_code,
            introduction=introduction,
            articles=articles,
            monthly_usage=monthly_usage,
            remaining_usage=remaining_usage,
            last_reset_date=last_reset_date,
            doc_ref=doc_ref,
        )
