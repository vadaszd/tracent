
""" Capture the structure of a diagram visualizing an event-based trace.

    A trace diagram is visually similar to a UML sequence diagram.
    This module defines the classes representing the elements of a trace
    diagram.
    It also defines an interface for visiting the structure and the
    interface visitors are expected to implement.
"""
import inspect

from abc import ABC, abstractmethod
from math import sqrt
from typing import Dict, List, NamedTuple, Type

try:
    from tracent import TagDict
except ImportError:
    import sys
    sys.path.append('..')

from tracent import TagDict
from tracent.oob import tracent_pb2 as pb


class Point(NamedTuple):
    """ A point in the SVG coordinate-system

        The origin is the upper left corner of the _drawing
        The X axis runs horizontally, Y points downwards.
        Both axis are considered to be scaled in mm.
    """
    x: float
    y: float

    def __add__(self, other: 'Point') -> 'Point':
        return Point(self.x + other.x, self.y + other.y)

    def __mul__(self, other: float) -> 'Point':
        return Point(self.x * other, self.y * other)

    def __abs__(self) -> float:
        return sqrt(self.x * self.x + self.y * self.y)


class DiagramElement:
    """ Base class for all elements of the diagram, with support for Visitors.

        Each diagram-element has a *reference point*, which is
        (programming-wise) the only externally visible reference to the position
        of the element.
        The position of the elements are set by the layout generator visitor.
    """
    position: Point  # reference point

    def accept(self, visitor: 'DiagramVisitor'):
        """ Visit the diagram elememt and its constituents

            This method defines the interface for accepting a visitor and it
            also provides a default implementation making the visitor visit
            the element. This is suitable for atomic diagram elements.

            Compound diagram elements must override this method and make sure
            that their constituent elements accept the visitor *before*
            it visits the compound element.
        """
        visitor.visit(self)


class DiagramVisitor(ABC):

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        try:
            targets = cls.__visitor_targets__
        except AttributeError:
            targets = cls.__visitor_targets__ = dict()
        for name, member in cls.__dict__.items():
            if not name.startswith('visit') or not inspect.isfunction(member):
                continue
            signature = inspect.signature(member)
            if len(signature.parameters) != 2:
                raise TypeError("{} should have exactly 2 parameter"
                                .format(member.__name__))
            parameters = iter(signature.parameters.values())
            next(parameters)
            de = next(parameters)
            annotation = de.annotation
            if not isinstance(annotation, type):
                raise TypeError("Visit*() parameter must be annotated with "
                                "a type, got {}".format(repr(annotation)))
            targets[annotation] = member

    @abstractmethod
    def visit_trace_diagram(self, de: 'TraceDiagram'): pass

    @abstractmethod
    def visit_life_line(self, de: 'LifeLine'): pass

    @abstractmethod
    def visit_head(self, de: 'Head'): pass

    @abstractmethod
    def visit_foot(self, de: 'Foot'): pass

    @abstractmethod
    def visit_spine(self, de: 'Spine'): pass

    @abstractmethod
    def visit_vertex(self, de: 'Vertex'): pass

    @abstractmethod
    def visit_destruction(self, de: 'Destruction'): pass

    @abstractmethod
    def visit_activation(self, de: 'Activation'): pass

    @abstractmethod
    def visit_edge(self, de: 'Edge'): pass

    def visit(self, de: DiagramElement):
        for cls in type(de).mro():
            method = self.__visitor_targets__.get(cls, None)
            if method is not None:
                return method(self, de)
        raise TypeError("No visit*() method for {}".format(repr(de)))


#  https://www.uml-diagrams.org/sequence-diagrams.html
class TraceDiagram(DiagramElement):
    """ A UML sequence diagram like representation of a trace

        A collection of
            - life-lines representing EUs and events happening on them
            - edges representing ordering constraints between events

        The reference point of the diagram is the position of its first
        (leftmost) life line
    """
    # Timestamp of the earliest start event
    # An event is a start event if it has no incoming edge
    # If there are multiple such events in a trace (which should not happen)
    # then we take the event with the smallest timestamp (unadjusted for clock
    # skew)
    start_time: float

    # The scale to convert time differences to geometrical distances (by
    # multiplying the time difference with the scale).
    time_scale: float

    life_lines: List['LifeLine']
    edges: List['Edge']

    def __init__(self, start_time: float, time_scale: float):
        self.start_time = start_time
        self.time_scale = time_scale
        self.life_lines = list()
        self.edges = list()

    def accept(self, visitor: DiagramVisitor):
        visitor.visit(self)
        for life_line in self.life_lines:
            life_line.accept(visitor)
        for edge in self.edges:
            edge.accept(visitor)


class LifeLine(DiagramElement):
    """ A UML life-line like representation of an EU in a trace diagram

        The trace diagram consists of multiple life lines.
    """
    # Constituent DiagramElements
    head: 'Head'
    spine: 'Spine'
    foot: 'Foot'
    vertices: List['Vertex']  # sorted by time_offset
    activations: List['Activation']
    time_axes_origin: Point

    def __init__(self, trace_diagram: TraceDiagram, tags: TagDict):
        self.trace_diagram = trace_diagram
        trace_diagram.life_lines.append(self)
        self.head = Head(self, tags)
        self.foot = Foot(self)
        self.spine = Spine(self)
        self.vertices = list()
        self.activations = list()

    def accept(self, visitor: DiagramVisitor):
        # The order of visiting the elements is significant and is optimized
        # for the layout generator
        # (may be exploited by other stateful visitors as well)
        visitor.visit(self)
        self.head.accept(visitor)

        for vertex in self.vertices:
            vertex.accept(visitor)

        for activation in self.activations:
            activation.accept(visitor)

        self.foot.accept(visitor)
        self.spine.accept(visitor)


class Head(DiagramElement):
    """ The shape at the top of the life-line containing its description.

        The coordinates of the reference point of the head are "bottom middle"
            - vertically: the vertical coordinate of its lowest point.
            - horizontally: the mean of the horizontal coordinates of its
                    leftmost and rightmost points.
    """
    eu_tags: TagDict

    def __init__(self, life_line: LifeLine, tags: TagDict):
        self.life_line = life_line
        self.tags = tags


class Foot(DiagramElement):
    """ An optional repetition of the Head at the bottom end of the spine.

        If there is a Destruction shape on the life-line, the foot must be
        placed below it.
    """
    def __init__(self, life_line: LifeLine):
        self.life_line = life_line


class _LineLikeElement(DiagramElement):
    end_position: Point


class Spine(_LineLikeElement):
    """ The thin vertical line of the life-line
    """
    def __init__(self, life_line: LifeLine):
        self.life_line = life_line


class Vertex(DiagramElement):
    """ A dot-like shape representing an event on the EU.
    """
    time_offset: float
    tags: TagDict

    def __init__(self, life_line: LifeLine, time_stamp: float,
                 tags: TagDict,
                 ):
        """
        :param life_line: The life-line associated with the EU of the event
        :param time_stamp: Must be already corrected for clock skew
        :param tags: The tags associated with the event
        """
        self.life_line = life_line
        life_line.vertices.append(self)
        self.time_offset = time_stamp - life_line.trace_diagram.start_time


class Destruction(Vertex):
    """ A shape representing an event of type FINISH_EU

        The spine ceases at this shape. May be followed by a Foot.
    """


class _BaseEdge(_LineLikeElement):
    fro: Vertex
    to: Vertex

    def __init__(self, fro: Vertex, to: Vertex):
        self.fro = fro
        self.to = to


class Activation(_BaseEdge):
    """ A widened  section of the Spine representing a non-idle EU state

        Must be bounded by vertices.
        The graphical representation may suggest a top-down directionality.
        Represents an ordering constraint between two events on the same EU.
    """
    life_line: LifeLine
    status: pb.Event.Status

    def __init__(self, fro: Vertex, to: Vertex):
        super(Activation, self).__init__(fro, to)
        self.life_line = to.life_line
        assert self.life_line is fro.life_line
        self.life_line.activations.append(self)


class Edge(_BaseEdge):
    """ A directed line connecting two vertices placed on different life-lines

        Represents an ordering constraint between two events on different EUs.
    """
    trace_diagram: TraceDiagram

    def __init__(self, fro: Vertex, to: Vertex):
        super(Edge, self).__init__(fro, to)
        self.trace_diagram = to.life_line.trace_diagram
        assert self.trace_diagram is fro.life_line.trace_diagram
        self.trace_diagram.edges.append(self)


