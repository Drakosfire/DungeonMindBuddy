"""Closed user-reviewed intent for creating a connected Build page."""
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator


class _Closed(BaseModel):
    model_config = ConfigDict(extra='forbid')


class ConnectedPageOrigin(_Closed):
    document_id: UUID
    revision: int = Field(ge=1, strict=True)
    content_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    editor_json: str = Field(min_length=2, max_length=2_000_000)
    editor_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    selection_from: int = Field(ge=0, strict=True)
    selection_to: int = Field(ge=1, strict=True)
    selected_text: str = Field(min_length=1, max_length=4000)


class ConnectedPageObject(_Closed):
    node_id: str | None = Field(default=None, min_length=1, max_length=500)
    label: str = Field(min_length=1, max_length=200, pattern=r'^[^\n\r]+$')
    kind: Literal['npc', 'location']


class ConnectedPageIntent(_Closed):
    operation_id: UUID
    world_id: str = Field(pattern=r'^[a-z0-9][a-z0-9_-]{0,62}$')
    title: str = Field(min_length=1, max_length=200, pattern=r'^[^\n\r]+$')
    origin: ConnectedPageOrigin
    place: ConnectedPageObject
    person: ConnectedPageObject | None = None
    relationships: list[Literal['owns', 'operates']] = Field(default_factory=list, max_length=2)
    mode: Literal['scaffold', 'build_out']
    instructions: str = Field(default='', max_length=8000)

    @model_validator(mode='after')
    def coherent(self):
        if self.place.kind != 'location' or (self.person and self.person.kind != 'npc'):
            raise ValueError('Choose a location and, optionally, a person')
        if bool(self.relationships) != bool(self.person) or len(set(self.relationships)) != len(self.relationships):
            raise ValueError('Choose a person and distinct relationships, or leave both absent')
        if self.person and self.person.node_id and self.person.node_id == self.place.node_id:
            raise ValueError('The person and location must be distinct objects')
        if self.title != self.title.strip() or any(o.label != o.label.strip() for o in [self.place, *([self.person] if self.person else [])]):
            raise ValueError('Names must be nonempty without surrounding whitespace')
        return self
