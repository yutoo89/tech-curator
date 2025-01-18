import json
import google.generativeai as genai


RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "is_technical_term": {"type": "BOOLEAN"},
        "original_text": {"type": "STRING"},
        "transformed_text": {"type": "STRING"},
        "reading": {"type": "STRING"},
    },
    "required": ["original_text", "transformed_text", "reading"],
}


class GeminiTextCorrector:
    def __init__(self, model_name: str):
        self.model = genai.GenerativeModel(model_name)

    def create_prompt(self, input_text: str, region_code: str) -> str:
        lines = [
            "以下の指示に従い、提供された文字列を分析してください。",
            "- 音声認識で得られたtextとregion_codeが提供されます",
            "- 下記の各項目を出力します",
            "  - is_technical_term: textが技術用語か否か",
            "  - transformed_text: textを技術用語として正しい表記に変換したもの",
            "  - reading: transformed_textの正しい読み(phonetic)を、その地域の言語で生成したもの",
            "- textが多義語の場合は、スペース区切りで意味を明確にする単語を追加したものをtransformed_textとします",
            "  - 例: 「オーロラ」=>「Aurora AWS」",
            "- textの音から本来意図した技術用語を推測できる場合は、その技術用語をtransformed_textとします",
            "  - 例: 「先生へ愛」=>「生成AI」",
            "  - 技術用語を意図して入力したと推測できる場合は、is_technical_termをtrueとする",
            "例1:",
            "- input: {text: '先生へ愛', region_code: 'JP'}",
            "- output: {is_technical_term: true, transformed_text: '生成AI', reading: 'せいせいえーあい'}",
            "例2:",
            "- input: {text: '図書館', region_code: 'JP'}",
            "- output: {is_technical_term: false, transformed_text: '図書館', reading: 'としょかん'}\n",
            f"提供する情報:",
            f"- text: {input_text}",
            f"- region_code: {region_code}",
        ]
        return "\n".join(lines)

    def run(self, input_text: str, region_code: str) -> str:
        prompt = self.create_prompt(input_text, region_code)
        response = self.model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                response_schema=RESPONSE_SCHEMA,
            ),
        )
        parsed_result = json.loads(response.text)
        return {
            "is_technical_term": parsed_result.get("is_technical_term", False),
            "original_text": input_text,
            "transformed_text": parsed_result.get("transformed_text", ""),
            "reading": parsed_result.get("reading", ""),
        }
