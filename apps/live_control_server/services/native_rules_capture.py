"""Mandatory per-request native SDK message capture; no telemetry/raw-body log.

The pinned post_api_request hook supplies the uncapped assistant_message object.
Never read the sanitized response dict or the rendered final_response instead.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Callable

MAX_REPLY_BYTES=262144
MAX_TOOL_ARGUMENT_BYTES=65536


@dataclass(frozen=True)
class NativeToolReply:
    call_id: str
    name: str
    arguments_json: str
    arguments_sha256: str


@dataclass(frozen=True)
class NativeProviderReply:
    authorization_id: str
    api_request_id: str
    provider: str
    model: str
    api_mode: str
    request_sha256: str
    finish_reason: str | None
    status: str
    text: str | None
    text_sha256: str | None
    text_utf8_bytes: int
    tool_calls: tuple[NativeToolReply,...]


def _get(value,key,default=None):
    return value.get(key,default) if isinstance(value,dict) else getattr(value,key,default)


def _identity(value,limit=256):
    if not isinstance(value,str) or not value.strip() or value!=value.strip() or len(value.encode('utf-8'))>limit:
        raise ValueError('Invalid native capture identity')
    return value


def _strict_object(raw):
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result:raise ValueError('Duplicate tool argument key')
            result[key]=value
        return result
    value=json.loads(raw,object_pairs_hook=unique,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('Nonfinite tool argument')))
    if not isinstance(value,dict):raise ValueError('Tool arguments must be an object')
    return value


class NativeReplyCapture:
    """One current call/reply. An unacknowledged or missing capture vetoes use.

    Registration/binding must succeed before native SDK entry. This collector is
    a hook owner only; transport/APP wiring and claim checks remain separate.
    """
    def __init__(self,on_reply: Callable[[NativeProviderReply],bool]):
        self.on_reply=on_reply
        self.pending=None
        self.last=None
        self.failure=None
        self._hooks=None
        self._seen=set()
        self._bindings=0
        self._closed=False

    def register(self,plugin_manager) -> bool:
        hooks=getattr(plugin_manager,'_hooks',None)
        if self._closed or self._hooks is not None or not isinstance(hooks,dict):
            self.failure='capture_hook_unavailable';return False
        callbacks=hooks.setdefault('post_api_request',[])
        if not isinstance(callbacks,list):
            self.failure='capture_hook_unavailable';return False
        callbacks.append(self.on_post_api_request);self._hooks=hooks
        return True

    def bind(self,view,*,authorization_id: str,api_request_id: str) -> bool:
        try:
            if self._closed or self.failure is not None or self._hooks is None or self.pending is not None or self._bindings>=64:
                raise ValueError('Native capture is not ready')
            provider=_identity(view.provider);model=_identity(view.model);mode=_identity(view.api_mode)
            if mode not in {'chat_completions','codex_responses'}:raise ValueError('Unknown native transport')
            digest=view.payload_sha256
            if not isinstance(digest,str) or len(digest)!=64 or any(c not in '0123456789abcdef' for c in digest):
                raise ValueError('Invalid native request digest')
            self._bindings+=1
            self.pending=(_identity(authorization_id),_identity(api_request_id),provider,model,mode,digest)
            self.last=None  # Retire the prior body; only metadata IDs survive.
            return True
        except (ValueError,TypeError,AttributeError):
            self.failure='capture_binding_failed';return False

    def on_post_api_request(self,**payload) -> bool:
        try:
            if self.failure is not None or self.pending is None:raise ValueError('No pending native capture')
            authorization,request,provider,model,mode,digest=self.pending
            if payload.get('api_request_id')!=request:raise ValueError('Foreign SDK reply')
            if payload.get('model',model)!=model or payload.get('api_mode',mode)!=mode:
                raise ValueError('SDK reply identity changed')
            message=payload.get('assistant_message')
            if message is None or _get(message,'role','assistant')!='assistant':raise ValueError('Missing SDK assistant message')
            text=_get(message,'content')
            if text is not None and not isinstance(text,str):raise ValueError('Native reply text is not text')
            text_bytes=b'' if text is None else text.encode('utf-8')
            if len(text_bytes)>MAX_REPLY_BYTES:raise ValueError('Native reply exceeds output limit')
            calls=_get(message,'tool_calls')
            if calls is None:calls=[]
            if not isinstance(calls,(list,tuple)) or len(calls)>32:raise ValueError('Native tool replies exceed bound')
            size=len(text_bytes);tools=[];ids=set()
            for call in calls:
                identity=_identity(_get(call,'id'),128)
                if identity in ids or identity in self._seen or _get(call,'type')!='function':raise ValueError('Ambiguous native tool identity')
                ids.add(identity);function=_get(call,'function');name=_identity(_get(function,'name'),128)
                raw=_get(function,'arguments')
                if not isinstance(raw,str):raise ValueError('Missing actual tool arguments')
                encoded=raw.encode('utf-8');size+=len(encoded)
                if len(encoded)>MAX_TOOL_ARGUMENT_BYTES or size>MAX_REPLY_BYTES:raise ValueError('Native arguments exceed output bound')
                arguments=_strict_object(raw)
                canonical=json.dumps(arguments,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')
                tools.append(NativeToolReply(identity,name,raw,sha256(canonical).hexdigest()))
            finish=payload.get('finish_reason')
            if finish is not None and (not isinstance(finish,str) or len(finish)>128):raise ValueError('Invalid SDK finish reason')
            status='tool_calls' if finish=='tool_calls' and tools else 'answered' if finish=='stop' and not tools and text and text.strip() else 'failed'
            reply=NativeProviderReply(authorization,request,provider,model,mode,digest,finish,status,text,
                sha256(text_bytes).hexdigest() if text is not None else None,len(text_bytes),tuple(tools))
            try:
                acknowledged=self.on_reply(reply) is True
            except Exception:
                # The SDK swallows hook exceptions. Retain an explicit veto when
                # a parent persistence callback raises, without logging content.
                acknowledged=False
            if not acknowledged:raise ValueError('Native reply was not durably acknowledged')
            self.last=reply;self.pending=None;self._seen.update(ids)
            if status=='failed':self.failure='provider_output_incomplete'
            return True
        except (ValueError,TypeError,AttributeError,RecursionError):
            self.failure='native_reply_capture_failed';self.pending=None;self.last=None
            return False

    def close(self):
        if self._hooks is not None:
            callbacks=self._hooks.get('post_api_request',[])
            if isinstance(callbacks,list):
                callbacks[:]=[callback for callback in callbacks if callback!=self.on_post_api_request]
        self._hooks=None;self.pending=None;self.last=None;self._seen.clear()
        self._closed=True;self.failure=self.failure or 'capture_closed';self.on_reply=None
