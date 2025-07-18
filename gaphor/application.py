"""The Application object. One application should be available.

An application can host multiple sessions. From a user point of view a
session is represented as a window in which a diagram can be edited.
"""

from __future__ import annotations

import importlib.metadata
import logging
from collections.abc import Iterator
from pathlib import Path
from typing import TypeVar, cast
from uuid import uuid1

from gaphor.abc import ActionProvider, Service
from gaphor.action import action
from gaphor.core import event_handler
from gaphor.core.eventmanager import EventManager
from gaphor.entrypoint import initialize
from gaphor.event import (
    ActiveSessionChanged,
    ApplicationShutdown,
    ModelSaved,
    ServiceInitializedEvent,
    ServiceShutdownEvent,
    SessionCreated,
    SessionShutdown,
    SessionShutdownRequested,
)
from gaphor.services.componentregistry import ComponentRegistry

T = TypeVar("T")


logger = logging.getLogger(__name__)


def distribution():
    """The distribution metadata for Gaphor."""
    return importlib.metadata.distribution("gaphor")


class NotInitializedError(Exception):
    pass


class Application(Service, ActionProvider):
    """The Gaphor application is started from the gaphor.ui module.

    This application instance is used to maintain application wide references
    to services and sessions (opened models). It behaves like a singleton in many ways.

    The Application is responsible for loading services and plugins. Services
    are registered in the "component_registry" service.
    """

    def __init__(self, gtk_app=None):
        self._gtk_app = gtk_app
        self._active_session: Session | None = None
        self._sessions: set[Session] = set()

        self._services_by_name = initialize("gaphor.appservices", application=self)

        self.event_manager: EventManager = cast(
            EventManager, self._services_by_name["event_manager"]
        )

    def get_service(self, name):
        if not self._services_by_name:
            raise NotInitializedError("Session is no longer alive")

        return self._services_by_name[name]

    @property
    def active_window(self):
        return self._gtk_app.get_active_window() if self._gtk_app else None

    @property
    def gtk_app(self):
        return self._gtk_app

    @property
    def sessions(self):
        return self._sessions

    @property
    def active_session(self):
        return self._active_session

    def new_session(self, *, filename=None, template=None, services=None, force=False):
        """Initialize an application session."""

        filename = Path(filename) if filename else None
        if filename is None is template:
            return self._spawn_session(session=Session(services=services))

        if filename and not force:
            for session in self._sessions:
                if session.filename == filename:
                    session.foreground()
                    return

        return self._spawn_session(
            session=Session(services=services),
            filename=filename,
            template=template,
            force=force,
        )

    def recover_session(self, *, session_id, filename=None, template=None) -> Session:
        """Recover a (crashed) session."""

        return self._spawn_session(
            session=Session(session_id=session_id), filename=filename, template=template
        )

    def _spawn_session(
        self, session: Session, filename=None, template=None, force=False
    ) -> Session:
        @event_handler(ActiveSessionChanged)
        def on_active_session_changed(_event):
            logger.debug("Set active session to %s", session)
            self._active_session = session

        @event_handler(SessionShutdown)
        def on_session_shutdown(event: SessionShutdown):
            self.shutdown_session(session)
            if not self._sessions and (
                event.quitting or not (self._gtk_app and self._gtk_app.get_windows())
            ):
                self.shutdown()

        event_manager = session.get_service("event_manager")
        event_manager.subscribe(on_active_session_changed)
        event_manager.subscribe(on_session_shutdown)

        self._sessions.add(session)

        session_created = SessionCreated(
            self, session, filename, template, force, interactive=bool(self._gtk_app)
        )
        event_manager.handle(session_created)
        self.event_manager.handle(session_created)
        session.foreground()

        return session

    def shutdown_session(self, session: Session):
        assert session
        session.shutdown()
        self._sessions.discard(session)
        if session is self._active_session:
            self._active_session = None

    def shutdown(self):
        """Forcibly shut down all sessions. No questions asked.

        This is mainly for testing purposes.
        """
        while self._sessions:
            self.shutdown_session(self._sessions.pop())

        self.event_manager.handle(ApplicationShutdown(self))

        for c in self._services_by_name.values():
            if c is not self:
                c.shutdown()
        self._services_by_name.clear()

    @action(name="app.quit", shortcut="<Primary>q")
    def quit(self):
        """The user's application Quit command."""
        for session in list(self._sessions):
            self._active_session = session
            event_manager = session.get_service("event_manager")
            event_manager.handle(SessionShutdownRequested(quitting=True))

        if not self._sessions:
            self.shutdown()

    def all(self, base: type[T]) -> Iterator[tuple[str, T]]:
        return (
            (n, c) for n, c in self._services_by_name.items() if isinstance(c, base)
        )


class Session(Service):
    """A user context is a set of services (including UI services) that define
    a window with loaded model."""

    def __init__(self, session_id: str | None = None, *, services=None):
        """Initialize the application."""
        self.session_id = session_id or str(uuid1())
        services_by_name: dict[str, Service] = initialize("gaphor.services", services)
        self._filename = None

        self.event_manager: EventManager = cast(
            EventManager, services_by_name["event_manager"]
        )
        self.component_registry: ComponentRegistry = cast(
            ComponentRegistry, services_by_name["component_registry"]
        )

        for name, srv in services_by_name.items():
            logger.debug("Initializing service %s", name)
            self.component_registry.register(name, srv)
            self.event_manager.handle(ServiceInitializedEvent(name, srv))

        self.event_manager.subscribe(self.on_filename_changed)

    def get_service(self, name):
        if not self.component_registry:
            raise NotInitializedError("Session is no longer alive")

        return self.component_registry.get_service(name)

    @property
    def filename(self):
        return self._filename

    def foreground(self):
        self.event_manager.handle(ActiveSessionChanged(self))

    def shutdown(self):
        if self.component_registry:
            for name, srv in reversed(list(self.component_registry.all(Service))):  # type: ignore[type-abstract]
                self.shutdown_service(name, srv)

    def shutdown_service(self, name, srv):
        logger.debug("Shutting down service %s", name)

        self.event_manager.handle(ServiceShutdownEvent(name, srv))
        self.component_registry.unregister(srv)
        srv.shutdown()

    @event_handler(SessionCreated, ModelSaved)
    def on_filename_changed(self, event):
        self._filename = event.filename
