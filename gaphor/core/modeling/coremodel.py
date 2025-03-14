# This file is generated by coder.py. DO NOT EDIT!
# ruff: noqa: F401, E402, F811
# fmt: off

from __future__ import annotations

from gaphor.core.modeling.properties import (
    association,
    attribute as _attribute,
    derived,
    derivedunion,
    enumeration as _enumeration,
    redefine,
    relation_many,
    relation_one,
)


# 1: override Base
from gaphor.core.modeling.base import Base

# 7: override Diagram
from gaphor.core.modeling.diagram import Diagram

# 10: override Presentation
from gaphor.core.modeling.presentation import Presentation

# 16: override StyleSheet
from gaphor.core.modeling.stylesheet import StyleSheet

class PendingChange(Base):
    applied: _attribute[int] = _attribute("applied", int, default=0)
    element_id: _attribute[str] = _attribute("element_id", str)
    op = _enumeration("op", ("add", "remove", "update"), "add")


class ElementChange(PendingChange):
    diagram_id: _attribute[str] = _attribute("diagram_id", str)
    element_name: _attribute[str] = _attribute("element_name", str)
    modeling_language: _attribute[str] = _attribute("modeling_language", str)


class ValueChange(PendingChange):
    property_name: _attribute[str] = _attribute("property_name", str)
    property_type: _attribute[str] = _attribute("property_type", str)
    property_value: _attribute[str] = _attribute("property_value", str)


class RefChange(PendingChange):
    property_name: _attribute[str] = _attribute("property_name", str)
    property_ref: _attribute[str] = _attribute("property_ref", str)



Base.presentation = association("presentation", Presentation, composite=True, opposite="subject")
Diagram.ownedPresentation = association("ownedPresentation", Presentation, composite=True, opposite="diagram")
Presentation.parent = association("parent", Presentation, upper=1, opposite="children")
Presentation.children = association("children", Presentation, composite=True, opposite="parent")
Presentation.diagram = association("diagram", Diagram, upper=1, opposite="ownedPresentation")
Presentation.subject = association("subject", Base, upper=1, opposite="presentation")
