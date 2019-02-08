from abc import ABC, abstractmethod
from itertools import chain
from typing import List

from svgwrite import Drawing
from svgwrite.container import Symbol, Use

from .trace_diagram import (
    DiagramVisitor, TraceDiagram, LifeLine, Head, Foot,
    Spine, Vertex, Destruction, Activation, Edge
)


class AbstractSVGRenderer(DiagramVisitor, ABC):

    @abstractmethod
    @property
    def head_symbol(self) -> Symbol:
        """ The symbol used for heads
        """
    @abstractmethod
    @property
    def foot_symbol(self) -> Symbol:
        """ The symbol used for feet
        """
    @abstractmethod
    @property
    def vertex_symbol(self) -> Symbol:
        """ The symbol used for vertices
        """
    @abstractmethod
    @property
    def destruction_symbol(self) -> Symbol:
        """ The symbol used for destructions
        """
    @abstractmethod
    @property
    def activation_symbol(self) -> Symbol:
        """ The symbol used for activations
        """
    @abstractmethod
    @property
    def spine_symbol(self) -> Symbol:
        """ The symbol used for spines
        """
    @abstractmethod
    @property
    def edge_symbol(self) -> Symbol:
        """ The symbol used for edges
        """

    def __init__(self, filename: str):
        self._drawing = Drawing(filename=filename, debug=True)
        self._heads: List[Use] = list()
        self._feet: List[Use] = list()
        self._spines: List[Use] = list()
        self._vertices: List[Use] = list()
        self._activations: List[Use] = list()
        self._edges: List[Use] = list()

    def visit_trace_diagram(self, de: 'TraceDiagram'):
        # This is the last visit_*() method call
        for use in chain(self._spines, self._heads, self._feet,
                         self._activations, self._edges, self._vertices):
            self._drawing.add(use)

    def visit_life_line(self, de: 'LifeLine'):
        # TODO: group things on  a life line
        pass

    def visit_head(self, de: 'Head'):
        self._heads.append(self._drawing.use(self.head_symbol))

    def visit_vertex(self, de: 'Vertex'):
        self._vertices.append(self._drawing.use(self.vertex_symbol))

    def visit_destruction(self, de: 'Destruction'):
        self._vertices.append(self._drawing.use(self.destruction_symbol))

    def visit_activation(self, de: 'Activation'):
        self._activations.append(self._drawing.use(self.activation_symbol))

    def visit_foot(self, de: 'Foot'):
        self._feet.append(self._drawing.use(self.foot_symbol))

    def visit_spine(self, de: 'Spine'):
        self._spines.append(self._drawing.use(self.spine_symbol))

    def visit_edge(self, de: 'Edge'):
        self._heads.append(self._drawing.use(self.edge_symbol))

    @property
    def drawing(self) -> Drawing: return self._drawing
