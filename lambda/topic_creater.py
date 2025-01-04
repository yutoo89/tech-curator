from firebase_admin import firestore


class TopicCreater:
    def __init__(self, db: firestore.Client, user_id: str, topic: str):
        self.db = db
        self.user_id = user_id
        self.topic = topic

    def run(self) -> None:
        topic_doc_ref = self.db.collection("topics").document(self.user_id)
        doc = topic_doc_ref.get()

        if doc.exists:
            topic_doc_ref.delete()

        topic_doc_ref.set({"raw_topic": self.topic})
