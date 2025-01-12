from typing import Union
from firebase_admin import firestore


class DocumentNotFoundError(Exception):
    def __init__(self, message: str):
        super().__init__(message)


class Topic:
    COLLECTION_NAME = "topics"

    def __init__(
        self, user_id: str, raw_topic: str, topic: Union[str, None], locale: str
    ):
        self.user_id = user_id
        self.raw_topic = raw_topic
        self.topic = topic
        self.locale = locale

    @staticmethod
    def create(db: firestore.Client, user_id: str, raw_topic: str, locale: str) -> None:
        doc_ref = db.collection(Topic.COLLECTION_NAME).document(user_id)
        doc = doc_ref.get()

        if doc.exists:
            doc_ref.delete()

        doc_ref.set({"raw_topic": raw_topic, "locale": locale})

    @staticmethod
    def get(db: firestore.Client, user_id: str) -> "Topic":
        doc = db.collection(Topic.COLLECTION_NAME).document(user_id).get()
        if not doc.exists:
            raise DocumentNotFoundError(
                f"Document with user_id '{user_id}' not found in collection '{Topic.COLLECTION_NAME}'."
            )

        raw_topic = doc.get("raw_topic")
        topic = doc.get("topic")
        locale = doc.get("locale")

        return Topic(
            user_id=user_id,
            raw_topic=raw_topic,
            topic=topic,
            locale=locale,
        )
