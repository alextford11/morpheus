import asyncio
from datetime import datetime, timezone
from enum import Enum
from functools import update_wrapper
from random import random
from typing import Optional, Type  # noqa

import msgpack
from aiohttp.web import Application, HTTPBadRequest, HTTPForbidden, Request  # noqa
from cryptography.fernet import InvalidToken
from pydantic import BaseModel, ValidationError


class ContentType(str, Enum):
    JSON = 'application/json'
    MSGPACK = 'application/msgpack'


class WebModel(BaseModel):
    def _process_values(self, values):
        try:
            return super()._process_values(values)
        except ValidationError as e:
            raise HTTPBadRequest(text=e.display_errors)


class Session(WebModel):
    company: str = ...
    user_id: int = ...
    expires: datetime = ...


class View:
    def __init__(self, request):
        from .worker import Sender  # noqa
        self.request: Request = request
        self.app: Application = request.app
        self.session: Optional[Session] = None
        self.sender: Sender = request.app['sender']

    @classmethod
    def view(cls):
        async def view(request):
            self = cls(request)
            await self.authenticate(request)
            return await self.call(request)

        view.view_class = cls

        # take name and docstring from class
        update_wrapper(view, cls, updated=())

        # and possible attributes set by decorators
        update_wrapper(view, cls.call, assigned=())
        return view

    async def authenticate(self, request):
        pass

    async def call(self, request):
        raise NotImplementedError()

    async def request_data(self, validator: Type[WebModel]=None):
        decoder = self.decode_json
        content_type = self.request.headers.get('Content-Type')
        if content_type == ContentType.MSGPACK:
            decoder = self.decode_msgpack

        try:
            data = await decoder()
        except ValueError as e:
            raise HTTPBadRequest(text=f'invalid request data for {decoder.__name__}: {e}')

        if not isinstance(data, dict):  # TODO is this necessary?
            raise HTTPBadRequest(text='request data should be a dictionary')

        if validator:
            return validator(**data)
        else:
            return data

    async def decode_msgpack(self):
        data = await self.request.read()
        return msgpack.unpackb(data, encoding='utf8')

    async def decode_json(self):
        return await self.request.json()


class ServiceView(View):
    """
    Views used by services. Services are in charge and can be trusted to do "whatever they like".
    """
    async def authenticate(self, request):
        if request.app['settings'].auth_key != request.headers.get('Authorization', ''):
            # avoid the need for constant time compare on auth key
            await asyncio.sleep(random())
            raise HTTPForbidden(text='Invalid "Authorization" header')


class UserView(View):
    """
    Views used by users via ajax, "Authorization" header is Fernet encrypted user data.
    """
    async def authenticate(self, request):
        token = request.headers.get('Authorization', '')
        try:
            raw_data = self.app['fernet'].decrypt(token.encode())
        except InvalidToken:
            await asyncio.sleep(random())
            raise HTTPForbidden(text='Invalid token')

        try:
            data = msgpack.unpackb(raw_data, encoding='utf8')
        except ValueError:
            raise HTTPBadRequest(text='bad auth data')
        self.session = Session(**data)
        if self.session.expires < datetime.utcnow().replace(tzinfo=timezone.utc):
            raise HTTPForbidden(text='token expired')