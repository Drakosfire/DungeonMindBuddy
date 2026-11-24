"""Observe the pinned SDK's final-answer item without changing its transport."""
from generationengine import GenerationEngineError, TextCompleted, TextFailed, TextResult

from .build_reply_projection import BuildReplyProjection


class BuildAnswerObserver:
    def __init__(self, emit):
        self.emit = emit
        self.projection = BuildReplyProjection()
        self.item = None
        self.finished = False

    def __call__(self, event):
        if self.finished:
            return
        if event.type == "response.output_item.added":
            item = event.item
            if item.type == "message" and item.role == "assistant" and item.phase == "final_answer":
                if self.item is not None:
                    self.finished = True
                else:
                    self.item = (item.id, event.output_index)
        elif event.type == "response.output_item.done" and (event.item.id, event.output_index) == self.item:
            self.finished = True
        elif event.type == "response.output_text.delta" and (event.item_id, event.output_index) == self.item:
            text = self.projection.feed(event.delta)
            if text:
                self.emit(text)


class ObservedSdkStream:
    """Keep GenerationEngine in charge of SDK iteration, cleanup and the final."""

    def __init__(self, stream, observe):
        self.stream = stream
        self.observe = observe

    @property
    def response(self):
        return self.stream.response

    async def __aenter__(self):
        self.events = await self.stream.__aenter__()
        return self

    async def __aexit__(self, *exc):
        return await self.stream.__aexit__(*exc)

    async def __aiter__(self):
        async for event in self.events:
            if self.observe is not None:
                try:
                    self.observe(event)
                except Exception:
                    self.observe = None  # Observation cannot fail the saved turn.
            yield event


async def generate_build_reply(client, request):
    from contextlib import aclosing

    async with aclosing(client.stream_text(request)) as events:
        async for event in events:
            if isinstance(event, TextFailed):
                raise GenerationEngineError(event.failure, event.observation)
            if isinstance(event, TextCompleted):
                return TextResult(text=event.final_text, observation=event.observation)
    raise ValueError("The Build reply stream did not produce a final answer")
