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

from topic import Topic
from access import Access
from trend import Trend, DocumentNotFoundError

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Firestore initialization
if not firebase_admin._apps:
    SERVICE_ACCOUNT_KEY = os.environ["SERVICE_ACCOUNT_KEY"]
    cred = credentials.Certificate(json.loads(SERVICE_ACCOUNT_KEY))
    firebase_admin.initialize_app(cred)
db = firestore.client()


def trend_summary(db: firestore.Client, user_id: str, locale: str) -> str:
    try:
        trend = Trend.get(db, user_id)
        speaks = [
            trend.title,
            trend.body,
        ]

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
        if locale == "ja-JP":
            speaks = [
                f"現在フォロー中のトピックは「{topic.topic}」です。",
                "違う技術トピックをフォローしたい場合は、たとえば、「生成AIをフォロー」のように言ってください。",
            ]
        else:
            speaks = [
                f"The topic you are currently following is '{topic.topic}'.",
                "If you want to follow a different tech topic, say something like 'Follow Generative AI.'",
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
        speak_output = trend_summary(db, user_id, locale)

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

        Access.create_or_update(db, user_id)
        speak_output = trend_summary(db, user_id, locale)

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

        Access.create_or_update(db, user_id)
        speak_output = topic_summary(db, user_id, locale)

        return (
            handler_input.response_builder.speak(speak_output)
            .ask(speak_output)
            .response
        )


class SetTopicIntentHandler(AbstractRequestHandler):
    """トピック登録"""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("SetTopicIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        user_id = handler_input.request_envelope.session.user.user_id
        slots = handler_input.request_envelope.request.intent.slots
        topic = slots["Topic"].value if "Topic" in slots else None
        locale = handler_input.request_envelope.request.locale

        self.set_topic(user_id, topic, locale)
        speak_output = (
            f"{topic} has been followed. Please wait a moment and try reopening Tech Curator."
            if locale != "ja-JP"
            else f"{topic}をフォローしました。しばらく時間をおいて、もう一度テックキュレーターを開いてみてください。"
        )

        return (
            handler_input.response_builder.speak(speak_output)
            .set_should_end_session(True)
            .response
        )

    def set_topic(self, user_id, topic, locale):
        Topic.create(db, user_id, topic, locale)
        Access.create_or_update(db, user_id)


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


# The SkillBuilder object acts as the entry point for your skill, routing all request and response
# payloads to the handlers above. Make sure any new handlers or interceptors you've
# defined are included below. The order matters - they're processed top to bottom.

sb = SkillBuilder()

sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(SetTopicIntentHandler())
sb.add_request_handler(GetTopicIntentHandler())
sb.add_request_handler(GetTrendIntentHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(CancelOrStopIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())
sb.add_request_handler(IntentReflectorHandler())
sb.add_exception_handler(CatchAllExceptionHandler())

handler = sb.lambda_handler()
