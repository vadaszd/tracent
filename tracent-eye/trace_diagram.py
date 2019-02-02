
""" Capture the structure of a diagram visualizing an event-based trace.

    A trace diagram is visually similar to a UML sequence diagram.
"""
from abc import ABC, abstractmethod
from typing import Dict, List


class DiagramElement(ABC):
    def accept(self, visitor: 'Visitor'):
        visitor.visit(self)


class Visitor(ABC):

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
        pass  # TODO: dispatch to the type-specific visit_* methods


#  https://www.uml-diagrams.org/sequence-diagrams.html
class TraceDiagram(DiagramElement):
    """ A UML sequence diagram like representation of a trace

        A collection of
            - life-lines representing EUs and events happening on them
            - edges representing ordering constraints between events
    """
    life_lines: List['LifeLine']
    edges: List['Edge']

    def accept(self, visitor: Visitor):
        for life_line in self.life_lines:
            life_line.accept(visitor)
        for edge in self.edges:
            edge.accept(visitor)
        visitor.visit(self)


class LifeLine(DiagramElement):
    """ A UML life-line like representation of an EU in a trace diagram
    """
    # Constituent DiagramElements
    head: 'Head'
    spine: 'Spine'
    foot: 'Foot'
    vertices: List['Vertex']  # sorted by time_offset
    activations: List['Activation']

    # Other attributes
    start_time: float
    clock_skew: float

    def accept(self, visitor: Visitor):
        self.head.accept(visitor)
        self.spine.accept(visitor)
        self.foot.accept(visitor)
        for vertex in self.vertices:
            vertex.accept(visitor)
        for activation in self.activations:
            activation.accept(visitor)
        visitor.visit(self)


class Head(DiagramElement):
    """ The shape at the top of the life-line containing its description.
    """
    eu_tags: Dict[str, TagType]


class Foot(DiagramElement):
    """ An optional repetition of the Head at the bottom end of the spine.

        If there is a Destruction shape on the life-line, the foot must be
        placed below it.
    """


class Spine(DiagramElement):
    """ The thin vertical line of the life-line """


class Vertex(DiagramElement):
    """ A dot-like shape representing an event on the EU"""
    time_offset: float
    tags: Dict[str, TagType]


class Destruction(DiagramElement):
    """ A shape representing an event of type FINISH_EU

        The spine ceases at this shape. May be followed by a Foot.
    """


class Activation(DiagramElement):
    """ A widened  section of the Spine representing a non-idle EU state

        Must be bounded by vertices.
        The graphical representation may suggest a top-down directionality.
        Represents an ordering constraint between two events on the same EU.
    """
    fro: Vertex
    to: Vertex
    status: pb.Event.Status


class Edge(DiagramElement):
    """ A directed line connecting two vertices placed on different life-lines

        Represents an ordering constraint between two events on different EUs.
    """
    fro: Vertex
    to: Vertex
