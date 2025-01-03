# -*- coding: utf-8 -*-

# This sample demonstrates handling intents from an Alexa skill using the Alexa Skills Kit SDK for Python.
# Please visit https://alexa.design/cookbook for additional examples on implementing slots, dialog management,
# session persistence, api calls, and more.
# This sample is built using the handler classes approach in skill builder.
import logging

from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.dispatch_components import AbstractExceptionHandler
import ask_sdk_core.utils as ask_utils
from ask_sdk_core.handler_input import HandlerInput

from ask_sdk_model import Response
import os
from datetime import datetime, timezone
import json
import firebase_admin
from firebase_admin import credentials, firestore


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Initialize Firestore
SERVICE_ACCOUNT_KEY = os.environ["SERVICE_ACCOUNT_KEY"]
cred = credentials.Certificate(json.loads(SERVICE_ACCOUNT_KEY))
firebase_admin.initialize_app(cred)
db = firestore.client()


class LaunchRequestHandler(AbstractRequestHandler):
    """Handler for Skill Launch."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool

        return ask_utils.is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        locale = handler_input.request_envelope.request.locale
        speak_output = 'Tell us the topics you want to follow. For example, say "Follow Generative AI."'
        if locale == "ja-JP":
            speak_output = "フォローしたいトピックを教えてください。たとえば、「生成AIをフォロー」と言ってみてください。"

        return (
            handler_input.response_builder.speak(speak_output)
            .ask(speak_output)
            .response
        )


class TopicCreater:
    def __init__(self, db: firestore.Client, user_id: str, topic: str):
        self.db = db
        self.user_id = user_id
        self.topic = topic

    def run(self) -> None:
        topic_doc_ref = db.collection("topics").document(self.user_id)
        topic_doc_ref.set({"raw_topic": self.topic}, merge=True)


class AccessUpdater:
    def __init__(self, db: firestore.Client, user_id: str):
        self.db = db
        self.user_id = user_id

    def run(self) -> None:
        now = datetime.now(timezone.utc).isoformat()
        doc_ref = self.db.collection("accesses").document(self.user_id)
        doc = doc_ref.get()

        if doc.exists:
            access_data = doc.to_dict()
            current_last_accessed = access_data.get("last_accessed")

            doc_ref.set(
                {"last_accessed": now, "previous_accessed": current_last_accessed},
                merge=True,
            )
        else:
            doc_ref.set({"last_accessed": now, "previous_accessed": None})


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

        self.set_topic(user_id, topic)

        locale = handler_input.request_envelope.request.locale
        speak_output = f"{topic} has been followed. Please wait a moment and try reopening Trend Curator."
        if locale == "ja-JP":
            speak_output = f"{topic}をフォローしました。しばらく時間をおいて、もう一度トレンドキュレーターを開いてみてください。"

        return (
            handler_input.response_builder.speak(speak_output)
            # .ask("add a reprompt if you want to keep the session open for the user to respond")
            .response
        )

    def set_topic(self, user_id, topic):
        TopicCreater(db, user_id, topic).run()
        AccessUpdater(db, user_id).run()


class HelpIntentHandler(AbstractRequestHandler):
    """Handler for Help Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "You can say hello to me! How can I help?"

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
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(CancelOrStopIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())
sb.add_request_handler(
    IntentReflectorHandler()
)  # make sure IntentReflectorHandler is last so it doesn't override your custom intent handlers

sb.add_exception_handler(CatchAllExceptionHandler())

handler = sb.lambda_handler()
