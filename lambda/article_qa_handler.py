import google.generativeai as genai
from firebase_admin import firestore


class ArticleQAHandler:
    def __init__(
        self,
        model_name: str,
        db: firestore.Client,
        user_id: str,
        introduction: str,
        articles: list,
    ):
        self.model = genai.GenerativeModel(model_name)
        self.db = db
        self.user_id = user_id
        self.introduction = introduction
        self.articles = articles

        self.save_conversation_history(
            {"user": "最新の技術トピックを教えてください。", "ai": self.introduction}
        )

    def get_recent_articles(self, limit: int = 5):
        articles_ref = self.db.collection("articles").document(self.user_id)
        articles_doc = articles_ref.get()
        if articles_doc.exists:
            return articles_doc.to_dict().get("articles", [])[:limit]
        return []

    def get_conversation_history(self, limit: int = 5):
        history_ref = self.db.collection("conversation").document(self.user_id)
        history_doc = history_ref.get()
        if history_doc.exists:
            history = history_doc.to_dict().get("history", [])
            return history[-limit:]
        return []

    def save_conversation_history(self, new_entry: dict):
        history_ref = self.db.collection("conversation").document(self.user_id)
        history_doc = history_ref.get()
        history = []
        if history_doc.exists:
            history = history_doc.to_dict().get("history", [])

        # 履歴を更新して保存
        history.append(new_entry)
        if len(history) > 10:  # 5往復 = ユーザー質問5 + 回答5
            history = history[-10:]

        history_ref.set({"history": history}, merge=True)

    def generate_response(self, question: str):
        # 会話履歴を取得
        conversation_items = self.get_conversation_history(limit=5)

        # プロンプトに含める記事データを準備
        articles_section = "articles:\n"
        for article in self.articles:
            articles_section += (
                f"title: {article['title']}\nbody: {article['body'][:2000]}\n"
            )

        # プロンプトを構築
        conversation_history = []
        print(conversation_items)
        for item in conversation_items:
            conversation_history.append(f"user: {item['user']}")
            conversation_history.append(f"ai: {item['ai']}")
        conversation_history = "\n".join(conversation_history)
        prompt_lines = [
            "これまでの会話履歴と今回の質問、そして回答生成の参考になる記事を提供します。"
            "今回の質問に対して簡潔かつ具体的に応答してください。",
            "URLやコードを含まず、そのまま自然に発話できる応答を生成してください。",
            "",
            "conversation_history:",
            conversation_history,
            f"question: {question}",
            "",
            articles_section,
        ]

        prompt = "\n".join(prompt_lines)

        response = self.model.generate_content(prompt)
        answer = response.text.strip()

        self.save_conversation_history({"user": question, "ai": answer})

        return answer

    def cleanup_old_history(self):
        history_ref = self.db.collection("conversation").document(self.user_id)
        history_doc = history_ref.get()
        if history_doc.exists:
            history = history_doc.to_dict().get("history", [])
            if len(history) > 10:  # 5往復 = ユーザー質問5 + 回答5
                history = history[-10:]
                history_ref.set({"history": history}, merge=True)
