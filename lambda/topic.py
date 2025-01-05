from typing import Union
from firebase_admin import firestore


class Topic:
    COLLECTION_NAME = "topics"

    def __init__(self, user_id: str, raw_topic: str, topic: Union[str, None], locale: str):
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

        doc_ref.set({
            "raw_topic": raw_topic,
            "locale": locale
        })
