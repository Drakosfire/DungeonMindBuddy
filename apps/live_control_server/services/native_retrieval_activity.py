"""Observations of issued native reads; the acquisition owner retains authority."""


def observe_native_retrieval(adapter, operation, target, *, completed=False, unavailable=False):
    capture = getattr(adapter, 'context_capture', None)
    if capture is None:
        return
    capture.observe({
        'kind': 'context_decision',
        'action': 'retained' if unavailable else 'retrieved' if completed else 'expanded',
        'item_ids': [target],
        'reason_code': 'unavailable' if unavailable else 'question_relevance',
        'policy_version': f'native_{operation}_progress_v1',
    })
