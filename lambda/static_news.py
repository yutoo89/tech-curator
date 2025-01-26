from datetime import datetime
import uuid


class StaticNews:
    COLLECTION = "static_news"

    def __init__(
        self,
        body: str,
        sample_question: str,
        language_code: str,
        published: datetime = None,
        id: str = None,
    ):
        self.id = id if id else str(uuid.uuid4())
        self.body = body
        self.sample_question = sample_question
        self.language_code = language_code
        self.published = published if published else datetime.now()

    @staticmethod
    def from_dict(source):
        return StaticNews(
            id=source.get("id"),
            body=source.get("body", ""),
            sample_question=source.get("sample_question", ""),
            language_code=source.get("language_code", ""),
            published=source.get("published", datetime.now()),
        )

    def to_dict(self):
        return {
            "id": self.id,
            "body": self.body,
            "sample_question": self.sample_question,
            "language_code": self.language_code,
            "published": self.published,
        }

    def save(self, ref):
        doc_ref = ref.document(self.id)
        doc_ref.set(self.to_dict())

    def update(self, ref, updates):
        doc_ref = ref.document(self.id)
        doc_ref.update(updates)

    @staticmethod
    def get(ref, id):
        doc = ref.document(id).get()
        if doc.exists:
            data = doc.to_dict()
            return StaticNews.from_dict(data)
        else:
            return None

    @staticmethod
    def collection(db):
        return db.collection(StaticNews.COLLECTION)

    @staticmethod
    def exists(ref, id):
        doc_ref = ref.document(id)
        return doc_ref.get().exists
