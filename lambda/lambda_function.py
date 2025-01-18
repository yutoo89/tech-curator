# -*- coding: utf-8 -*-

import os
import json
import logging

from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.dispatch_components import AbstractExceptionHandler
import ask_sdk_core.utils as ask_utils
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_model import Response
import firebase_admin
from firebase_admin import credentials, firestore
import google.generativeai as genai

from topic import Topic
from access import Access
from trend import Trend, DocumentNotFoundError

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# GenAI initialization
genai.configure(api_key=os.environ["GENAI_API_KEY"])

# Firestore initialization
if not firebase_admin._apps:
    SERVICE_ACCOUNT_KEY = os.environ["SERVICE_ACCOUNT_KEY"]
    cred = credentials.Certificate(json.loads(SERVICE_ACCOUNT_KEY))
    firebase_admin.initialize_app(cred)
db = firestore.client()


def trend_summary(db: firestore.Client, user_id: str, locale: str, handler_input: HandlerInput) -> str:
    try:
        trend = Trend.get(db, user_id)
        sample_question = (
            "If you want to know more details about this news, try saying something like 'Question, about XYZ.'"
            if locale != "ja-JP"
            else "このニュースの詳細を知りたい場合は「質問、まるまる」のように言ってみてください。"
        )
        speaks = [
            trend.title,
            trend.body,
            sample_question
        ]

        session_attributes = handler_input.attributes_manager.session_attributes
        session_attributes["trend_body"] = trend.body

        return ("." if locale != "ja-JP" else "。").join(speaks)
    except DocumentNotFoundError:
        return (
            'Tell us the tech topic you want to follow. For example, say "Follow Generative AI."'
            if locale != "ja-JP"
            else "フォローしたい技術トピックを教えてください。たとえば、「生成AIをフォロー」と言ってみてください。"
        )


def topic_summary(db: firestore.Client, user_id: str, locale: str) -> str:
    try:
        topic = Topic.get(db, user_id)

        example_topic = get_example_topic(topic.topic, locale)
        if locale == "ja-JP":
            speaks = [
                f"現在フォロー中のトピックは「{topic.topic}」です。",
                f"違う技術トピックをフォローしたい場合は、たとえば、「{example_topic}をフォロー」のように言ってください。",
            ]
        else:
            speaks = [
                f"The topic you are currently following is '{topic.topic}'.",
                f"If you want to follow a different tech topic, say something like 'Follow {example_topic}.'",
            ]

        return " ".join(speaks)
    except DocumentNotFoundError:
        return (
            "You are not following any topics currently. Please tell me the tech topic you would like to follow. For example, say 'Follow Generative AI.'"
            if locale != "ja-JP"
            else "現在フォロー中のトピックはありません。フォローしたい技術トピックを教えてください。たとえば、「生成AIをフォロー」と言ってみてください。"
        )


class LaunchRequestHandler(AbstractRequestHandler):
    """スキル起動"""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool

        return ask_utils.is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        user_id = handler_input.request_envelope.session.user.user_id
        locale = handler_input.request_envelope.request.locale

        Access.create_or_update(db, user_id)
        speak_output = trend_summary(db, user_id, locale, handler_input)

        return (
            handler_input.response_builder.speak(speak_output)
            .ask(speak_output)
            .response
        )


class GetTrendIntentHandler(AbstractRequestHandler):
    """ニュース再生"""

    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("GetTrendIntent")(handler_input)

    def handle(self, handler_input):
        user_id = handler_input.request_envelope.session.user.user_id
        locale = handler_input.request_envelope.request.locale

        trend = Trend.get(db, user_id)
        if trend.remaining_usage == 0:
            speak_output = append_usage_message("", trend.remaining_usage, locale)
            return handler_input.response_builder.speak(speak_output).response

        Access.create_or_update(db, user_id)
        speak_output = trend_summary(db, user_id, locale, handler_input)

        speak_output = append_usage_message(speak_output, trend.remaining_usage, locale)
        return (
            handler_input.response_builder.speak(speak_output)
            .ask(speak_output)
            .response
        )


class GetTopicIntentHandler(AbstractRequestHandler):
    """トピック確認"""

    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("GetTopicIntent")(handler_input)

    def handle(self, handler_input):
        user_id = handler_input.request_envelope.session.user.user_id
        locale = handler_input.request_envelope.request.locale

        trend = Trend.get(db, user_id)
        if trend.remaining_usage == 0:
            speak_output = append_usage_message("", trend.remaining_usage, locale)
            return handler_input.response_builder.speak(speak_output).response

        Access.create_or_update(db, user_id)
        speak_output = topic_summary(db, user_id, locale)

        speak_output = append_usage_message(speak_output, trend.remaining_usage, locale)
        return (
            handler_input.response_builder.speak(speak_output)
            .ask(speak_output)
            .response
        )


class SetTopicIntentHandler(AbstractRequestHandler):
    """トピック登録"""

    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("SetTopicIntent")(handler_input)

    def handle(self, handler_input):
        user_id = handler_input.request_envelope.session.user.user_id
        slots = handler_input.request_envelope.request.intent.slots
        topic = slots["Topic"].value if "Topic" in slots else None
        locale = handler_input.request_envelope.request.locale

        trend = Trend.get(db, user_id)
        if trend.remaining_usage == 0:
            speak_output = append_usage_message("", trend.remaining_usage, locale)
            return handler_input.response_builder.speak(speak_output).response

        topic_instance = self.set_topic(user_id, topic, locale)

        example_topic = get_example_topic(topic_instance.topic, locale)
        if not topic_instance.is_technical_term:
            speak_output = (
                f"It seems that '{topic_instance.topic}' is not a technical term. Please tell us the technical topic you want to follow. For example, try saying 'Follow {example_topic}'."
                if locale != "ja-JP"
                else f"「{topic_instance.topic}」は技術用語ではないようです。フォローしたい技術トピックを教えてください。たとえば、「{example_topic}をフォロー」と言ってみてください。"
            )
        else:
            speak_output = (
                f"You are now following the topic '{topic_instance.topic}'. Please wait a moment and try reopening Tech Curator. "
                f"If you want to follow a different tech topic, please say something like 'Follow {example_topic}'."
                if locale != "ja-JP"
                else f"「{topic_instance.topic}」をフォローしました。しばらく時間をおいて、もう一度テックキュレーターを開いてみてください。"
                f"違う技術トピックをフォローしたい場合は、たとえば、「{example_topic}をフォロー」と言ってみてください。"
            )

        # NOTE: トピックの登録により利用回数が1回減るため調整
        speak_output = append_usage_message(
            speak_output, trend.remaining_usage - 1, locale
        )
        return (
            handler_input.response_builder.speak(speak_output)
            .ask(speak_output)
            .response
        )

    def set_topic(self, user_id, topic, locale) -> Topic:
        topic = Topic.create(db, user_id, topic, locale)
        Access.create_or_update(db, user_id)
        return topic


class QuestionIntentHandler(AbstractRequestHandler):
    """ニュースに関する質問"""

    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("QuestionIntent")(handler_input)

    def handle(self, handler_input):
        session_attributes = handler_input.attributes_manager.session_attributes
        slots = handler_input.request_envelope.request.intent.slots
        query = slots["Query"].value if "Query" in slots else None
        trend_body = session_attributes.get("trend_body", None)
        if trend_body:
            speak_output = f"クエリは「{query}」、現在のトレンド内容は「{trend_body}」です。質問をどうぞ。"
        else:
            speak_output = "トレンド情報が見つかりませんでした。もう一度試してください。"

        return (
            handler_input.response_builder.speak(speak_output)
            .ask(speak_output)
            .response
        )


class HelpIntentHandler(AbstractRequestHandler):
    """Handler for Help Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input):
        speak_output = "You can ask me to follow a topic or request details about a trend. How can I assist?"

        return (
            handler_input.response_builder.speak(speak_output)
            .ask(speak_output)
            .response
        )


class CancelOrStopIntentHandler(AbstractRequestHandler):
    """Single handler for Cancel and Stop Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AMAZON.CancelIntent")(
            handler_input
        ) or ask_utils.is_intent_name("AMAZON.StopIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "Goodbye!"

        return handler_input.response_builder.speak(speak_output).response


class SessionEndedRequestHandler(AbstractRequestHandler):
    """Handler for Session End."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response

        # Any cleanup logic goes here.

        return handler_input.response_builder.response


class IntentReflectorHandler(AbstractRequestHandler):
    """The intent reflector is used for interaction model testing and debugging.
    It will simply repeat the intent the user said. You can create custom handlers
    for your intents by defining them above, then also adding them to the request
    handler chain below.
    """

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_request_type("IntentRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        intent_name = ask_utils.get_intent_name(handler_input)
        speak_output = "You just triggered " + intent_name + "."

        return (
            handler_input.response_builder.speak(speak_output)
            # .ask("add a reprompt if you want to keep the session open for the user to respond")
            .response
        )


class CatchAllExceptionHandler(AbstractExceptionHandler):
    """Generic error handling to capture any syntax or routing errors. If you receive an error
    stating the request handler chain is not found, you have not implemented a handler for
    the intent being invoked or included it in the skill builder below.
    """

    def can_handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> bool
        return True

    def handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> Response
        logger.error(exception, exc_info=True)

        speak_output = "Sorry, I had trouble doing what you asked. Please try again."

        return (
            handler_input.response_builder.speak(speak_output)
            .ask(speak_output)
            .response
        )


class TrendUsageExceededError(Exception):
    """Custom exception for when usage exceeds the limit."""

    pass


def get_remaining_usage(db: firestore.Client, user_id: str) -> int:
    """Fetch the remaining usage for the user."""
    doc = db.collection(Trend.COLLECTION_NAME).document(user_id).get()
    if not doc.exists:
        return Trend.MONTHLY_LIMIT  # Default to the full limit if no document exists

    remaining_usage = doc.get("remaining_usage", Trend.MONTHLY_LIMIT)
    return remaining_usage


def append_usage_message(speak_output: str, remaining_usage: int, locale: str) -> str:
    """Append remaining usage message to the speak output."""
    if remaining_usage == 0:
        return (
            "You have reached the monthly limit for topic changes and questions. Please try again next month."
            if locale != "ja-JP"
            else "今月のフォロートピックの変更、および質問回数の上限に達しました。来月もう一度お試しください。"
        )
    elif remaining_usage <= 10:
        return (
            f"{speak_output} You have {remaining_usage} requests remaining this month for topic changes and questions."
            if locale != "ja-JP"
            else f"{speak_output} 今月のフォロートピックの変更、および質問の残り回数は{remaining_usage}回です。"
        )
    return speak_output


def get_example_topic(topic: str, locale: str) -> str:
    if locale == "ja-JP":
        return "AIエージェント" if topic == "生成AI" else "生成AI"
    else:
        return "AI Agent" if topic == "Generative AI" else "Generative AI"


# The SkillBuilder object acts as the entry point for your skill, routing all request and response
# payloads to the handlers above. Make sure any new handlers or interceptors you've
# defined are included below. The order matters - they're processed top to bottom.

sb = SkillBuilder()

sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(SetTopicIntentHandler())
sb.add_request_handler(GetTopicIntentHandler())
sb.add_request_handler(GetTrendIntentHandler())
sb.add_request_handler(QuestionIntentHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(CancelOrStopIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())
sb.add_request_handler(IntentReflectorHandler())
sb.add_exception_handler(CatchAllExceptionHandler())

handler = sb.lambda_handler()
