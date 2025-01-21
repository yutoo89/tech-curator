import google.generativeai as genai
from firebase_admin import firestore


class ArticleQAHandler:
    def __init__(
        self,
        model_name: str,
        db: firestore.Client,
        user_id: str,
        articles: list,
        language_code: str,
    ):
        self.model = genai.GenerativeModel(model_name)
        self.db = db
        self.user_id = user_id
        self.articles = articles
        self.language_code = language_code
        self.history_ref = self.db.collection("conversation").document(
            self.user_id
        )

    def get_conversation_history(self, limit: int = 5):
        history_doc = self.history_ref.get()
        if history_doc.exists:
            history = history_doc.to_dict().get("history", [])
            return history[-limit:]
        return []

    def save_conversation_history(self, new_entry: dict):
        history_doc = self.history_ref.get()
        history = []
        if history_doc.exists:
            history = history_doc.to_dict().get("history", [])

        history.append(new_entry)
        if len(history) > 10:
            history = history[-10:]

        self.history_ref.set({"history": history}, merge=True)

    def delete_conversation_history(self):
        self.history_ref.delete()

    def generate_response(self, question: str):
        if not question.endswith("?"):
            question += "?"
        conversation_items = self.get_conversation_history(limit=5)

        articles_section = ""
        for article in self.articles:
            articles_section += (
                f"title: {article['title']}\nurl: {article['url']}\nbody: {article['body'][:2000]}\n"
            )

        conversation_history_list = []
        for item in conversation_items:
            conversation_history_list.append(f"user: {item['user']}")
            conversation_history_list.append(f"ai: {item['ai']}")
        conversation_history_text = "\n".join(conversation_history_list)

        prompt_lines = [
            "あなたはエンジニアと会話するAIです。",
            "下記の質問に対する短い回答を生成してください。",
            f"question: {question}",
            "",
            "これまでの会話履歴と参考記事を提供します。",
            "回答は以下の条件に従って生成してください。",
            "- 過去に提供した情報と重複や類似がないこと",
            "- 抽象的な内容は避け、ツール名や機能名の固有名詞など具体的な情報を含めること",
            "- URLやコード、括弧書きの補足など、自然に発話できない表現は避けること",
            f"- 言語コード'{self.language_code}'で生成すること",
            "- 回答は50文字程度で生成すること",
        ]

        prompt_lines.extend(
            [
                "",
                "*************************** conversation_history ***************************\n",
                conversation_history_text,
                "",
                "*************************** articles ***************************************\n",
                articles_section,
            ]
        )
        prompt = "\n".join(prompt_lines)

        response = self.model.generate_content(prompt)
        answer = response.text.strip()

        self.save_conversation_history({"user": question, "ai": answer})

        return answer

    def cleanup_old_history(self):
        history_doc = self.history_ref.get()
        if history_doc.exists:
            history = history_doc.to_dict().get("history", [])
            if len(history) > 10:  # 5往復 = ユーザー質問5 + 回答5
                history = history[-10:]
                self.history_ref.set({"history": history}, merge=True)
