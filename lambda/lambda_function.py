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


def trend_summary(
    db: firestore.Client, user_id: str, locale: str, session_attributes
) -> str:
    try:
        trend = Trend.get(db, user_id)

        session_attributes["valid_indexes"] = trend.digest_indices()

        period_str = "." if locale != "ja-JP" else "。"
        summary = (
            f"Topics related to {trend.topic}."
            if locale != "ja-JP"
            else f"{trend.topic}に関する話題です。"
        )
        for digest in trend.digests.values():
            summary += f"{digest.index}: {digest.title}{period_str}"
        summary += (
            "If you would like to hear more details, please state the number, such as '1 for details.'"
            if locale != "ja-JP"
            else "詳しい内容を聞きたいときは「ニュース『1』を詳しく」のように番号をお伝えください。"
        )

        return summary
    except DocumentNotFoundError:
        return (
            'Tell us the topics you want to follow. For example, say "Follow Generative AI."'
            if locale != "ja-JP"
            else "フォローしたいトピックを教えてください。たとえば、「生成AIをフォロー」と言ってみてください。"
        )


class LaunchRequestHandler(AbstractRequestHandler):
    """Handler for Skill Launch."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool

        return ask_utils.is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        session_attributes = handler_input.attributes_manager.session_attributes
        user_id = handler_input.request_envelope.session.user.user_id
        locale = handler_input.request_envelope.request.locale

        Access.create_or_update(db, user_id)
        speak_output = trend_summary(db, user_id, locale, session_attributes)

        return (
            handler_input.response_builder.speak(speak_output)
            .ask(speak_output)
            .response
        )


class GetTrendSummaryHandler(AbstractRequestHandler):
    """Handler for providing trend summary based on user request."""

    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("GetTrendSummaryIntent")(handler_input)

    def handle(self, handler_input):
        session_attributes = handler_input.attributes_manager.session_attributes
        user_id = handler_input.request_envelope.session.user.user_id
        locale = handler_input.request_envelope.request.locale

        Access.create_or_update(db, user_id)
        speak_output = trend_summary(db, user_id, locale, session_attributes)

        return (
            handler_input.response_builder.speak(speak_output)
            .ask(speak_output)
            .response
        )


class SetTopicIntentHandler(AbstractRequestHandler):
    """Handler for Set Topic Intent."""

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
            f"{topic} has been followed. Please wait a moment and try reopening Trend Curator."
            if locale != "ja-JP"
            else f"{topic}をフォローしました。しばらく時間をおいて、もう一度トレンドキュレーターを開いてみてください。"
        )

        return (
            handler_input.response_builder.speak(speak_output)
            # .ask("add a reprompt if you want to keep the session open for the user to respond")
            .response
        )

    def set_topic(self, user_id, topic, locale):
        Topic.create(db, user_id, topic, locale)
        Access.create_or_update(db, user_id)


class GetTrendDetailHandler(AbstractRequestHandler):
    """Handler for requesting details about specific news."""

    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("GetTrendDetailIntent")(handler_input)

    def handle(self, handler_input):
        user_id = handler_input.request_envelope.session.user.user_id
        slots = handler_input.request_envelope.request.intent.slots
        trend_digest_index = (
            int(slots["TrendDigestIndex"].value)
            if "TrendDigestIndex" in slots
            else None
        )

        locale = handler_input.request_envelope.request.locale
        session_attributes = handler_input.attributes_manager.session_attributes
        valid_indexes = session_attributes.get("valid_indexes", [])

        if trend_digest_index is not None and trend_digest_index in valid_indexes:
            trend = Trend.get(db, user_id)
            news_body = trend.digests[trend_digest_index].body
            valid_indexes.remove(trend_digest_index)
            session_attributes["valid_indexes"] = valid_indexes

            if valid_indexes:
                speak_output = news_body + (
                    " Would you like to hear more details about another topic? Please state the number, such as '1 for details.'"
                    if locale != "ja-JP"
                    else "他に詳しく聞きたい話題はありますか？「'1'を詳しく」のように番号をお伝えください。"
                )
            else:
                speak_output = news_body + (
                    "That's all for today's news, please wait for the next update."
                    if locale != "ja-JP"
                    else "本日の話題は以上です。次の更新をお待ちください。"
                )
                return (
                    handler_input.response_builder.speak(speak_output)
                    .set_should_end_session(True)
                    .response
                )
        else:
            valid_indexes_str = ", ".join([f"'{i}'" for i in valid_indexes])
            speak_output = (
                f"The specified index does not exist. Please choose an index from {valid_indexes_str}."
                if locale != "ja-JP"
                else f"指定された番号が存在しません。{valid_indexes_str}の番号から選んでください。"
            )

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


# The SkillBuilder object acts as the entry point for your skill, routing all request and response
# payloads to the handlers above. Make sure any new handlers or interceptors you've
# defined are included below. The order matters - they're processed top to bottom.

sb = SkillBuilder()

sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(SetTopicIntentHandler())
sb.add_request_handler(GetTrendSummaryHandler())
sb.add_request_handler(GetTrendDetailHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(CancelOrStopIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())
sb.add_request_handler(IntentReflectorHandler())
sb.add_exception_handler(CatchAllExceptionHandler())

handler = sb.lambda_handler()
