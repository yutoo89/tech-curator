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
        self, topic: str, supplementary_topic: list[str], digests: dict[int, TrendDigest]
    ):
        if not digests:
            raise InvalidDigestsError(
                "The 'digests' dictionary is empty. At least one trend_digest item is required."
            )

        self.topic = topic
        self.supplementary_topic = supplementary_topic
        self.digests = digests

    @staticmethod
    def get(db: firestore.Client, user_id: str) -> Trend:
        doc = db.collection(Trend.COLLECTION_NAME).document(user_id).get()
        if not doc.exists:
            raise DocumentNotFoundError(
                f"Document with user_id '{user_id}' not found in collection '{Trend.COLLECTION_NAME}'."
            )

        digests = doc.get("digests")
        if not isinstance(digests, list):
            raise InvalidDigestsError(
                "The 'digests' field must be a list of trend_digest items."
            )
        if not digests:
            raise InvalidDigestsError(
                "The 'digests' field is empty or not found in the document."
            )

        digests_dict = {
            i + 1: TrendDigest(index=i + 1, title=d["title"], body=d["body"])
            for i, d in enumerate(digests)
        }

        return Trend(
            topic=doc.get("topic"),
            supplementary_topic=doc.get("supplementary_topic"),
            digests=digests_dict,
        )


    def digest_indices(self) -> list[int]:
        return list(self.digests.keys())
