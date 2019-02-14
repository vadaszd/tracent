from abc import ABC, abstractmethod
from typing import Dict, Type, TypeVar, Tuple, Callable

from svgwrite import Drawing
from svgwrite.base import BaseElement
from svgwrite.container import Symbol, Group

from .trace_diagram import (
    DiagramVisitor, TraceDiagram, LifeLine, Head, Foot,
    Spine, Vertex, Destruction, Activation, Edge,
    Point)


class Positioner(ABC):
    """ Abstract base class for positioning trace diagram shapes

        Concrete derived classes wrap `svgwrite.base.BaseElement`s (more
        precisely, instances of derived classes of Baselement) representing the
        shapes and provide functionality to fill in their coordinates.
    """
    _drawing: Drawing

    def __init__(self, drawing: Drawing,):
        self._drawing = drawing


class DotLikePositioner(Positioner):
    """ Abstract base class for positioning dot-like shapes.

        The position of a dot-like shape is determined by a single Point. The
        rendering procedure for these elements rely on stretching the shape to
        fit into a given viewport, affecting all sub-elements proportionally.

        The positioner calls a shape builder to create and add the elements of
        the shape to a `Symbol` instance. The shape is built only once using
        some arbitrary dimensions and added to the <symbols/> section of the
        SVG document. The occurrences of the shape are rendered with the help
        of `Use` instances, stretching the shapes as their textual content
        requires.
    """
    def __init__(self, drawing: Drawing,
                 shape_builder: Callable[[Symbol], None],
                 width: int, height: int
                 ):
        """ Initialize a DotLikePositioner.

        :param drawing: The `svgwrite.Drawing` being worked on
        :param shape_builder: A callback function taking an
            `svgwrite.container.Symbol`. It has to add() the elements drawing
            the shape to the Symbol object.
        :param width: Width of the shape (for opening a viewbox)
        :param height: Height of the shape (for opening a viewbox)
        """
        super().__init__(drawing)
        self._symbol = self._drawing.symbol()
        self._drawing.defs.add(self._symbol)
        shape_builder(self._symbol)
        self._symbol.viewbox(0, 0, width, height)
        self._width = width
        self._height = height

    @abstractmethod
    def at(self, point: Point) -> BaseElement:
        """ Place a `svgwrite.base.BaseElement` representing the shape at the
        given position.
        """


class AlignTopMiddle(DotLikePositioner):
    def at(self, point: Point) -> BaseElement:
        """ Place the symbol aligning its top middle at the given point
        """
        return self._drawing.use(self._symbol,
                                 x=point.x - self._width/2,
                                 y=point.y,
                                 width=self._width,
                                 height=self._height
                                 )


class AlignBottomMiddle(DotLikePositioner):
    def at(self, point: Point) -> BaseElement:

        """ Place the symbol aligning its bottom middle at the given point
        """
        return self._drawing.use(self._symbol,
                                 x=point.x - self._width/2,
                                 y=point.y - self._height,
                                 width=self._width,
                                 height=self._height
                                 )


class AlignCenterMiddle(DotLikePositioner):
    def at(self, point: Point) -> BaseElement:
        """ Place the symbol aligning its center middle at the given point
        """
        return self._drawing.use(self._symbol,
                                 x=point.x - self._width/2,
                                 y=point.y - self._height/2,
                                 width=self._width,
                                 height=self._height
                                 )


class AlignCenterLeft(DotLikePositioner):
    def at(self, point: Point) -> BaseElement:
        """ Place the symbol aligning its center left at the given point
        """
        return self._drawing.use(self._symbol,
                                 x=point.x,
                                 y=point.y - self._height/2,
                                 width=self._width,
                                 height=self._height
                                 )


class AlignCenterRight(DotLikePositioner):
    def at(self, point: Point) -> BaseElement:
        """ Place the symbol aligning its center right at the given point
        """
        return self._drawing.use(self._symbol,
                                 x=point.x - self._width,
                                 y=point.y - self._height/2,
                                 width=self._width,
                                 height=self._height
                                 )


class LineLikePositioner(Positioner):
    """ A class for positioning line-like shapes.

        The position of a line-like shape is determined by a start and an
        end Point.

        In contrast to dot-like shapes, line-like elements elements should not
        be rendered by stretching a pre-sized shape, as that would distort
        arrow-heads. Therefore, instead of the procedure in `DotLikePositioner`,
        every such element must be drawn individually.

        The default implementation that comes with this positioner draws an
        `svgwrite.shapes.Line` from start to end for each occurrence of the
        shape. The details of the graphical appearance are determined by XXX
    """
    def from_to(self, start: Point, end: Point) -> BaseElement:
        return self._drawing.line(start=start, end=end)


class SymbolSet(ABC):
    """ Abstract class defining the appearance of trace diagram symbols
    """
    _head: DotLikePositioner
    _foot: DotLikePositioner
    _vertex: DotLikePositioner
    _destruction: DotLikePositioner
    _activation: LineLikePositioner
    _spine: LineLikePositioner
    _edge: LineLikePositioner

    _head_attributes: Dict[str, str]
    _foot_attributes: Dict[str, str]
    _vertex_attributes: Dict[str, str]
    _destruction_attributes: Dict[str, str]
    _activation_attributes: Dict[str, str]
    _spine_attributes: Dict[str, str]
    _edge_attributes: Dict[str, str]

    def __init__(self, drawing: Drawing):
        self._drawing = drawing
        self._activation = LineLikePositioner(self._drawing)
        self._spine = LineLikePositioner(self._drawing)
        self._edge = LineLikePositioner(self._drawing)

    @property
    def head(self) -> DotLikePositioner:
        """ The symbol used for heads"""
        return self._head

    @property
    def foot(self) -> DotLikePositioner:
        """ The symbol used for feet"""
        return self._foot

    @property
    def vertex(self) -> DotLikePositioner:
        """ The symbol used for vertices"""
        return self._vertex

    @property
    def destruction(self) -> DotLikePositioner:
        """ The symbol used for destructions"""
        return self._destruction

    @property
    def activation(self) -> LineLikePositioner:
        """ The symbol used for activations"""
        return self._activation

    @property
    def spine(self) -> LineLikePositioner:
        """ The symbol used for spines"""
        return self._spine

    @property
    def edge(self) -> LineLikePositioner:
        """ The symbol used for edges"""
        return self._edge

    def head_group(self):
        return self._drawing.g(**self._head_attributes)

    def foot_group(self):
        return self._drawing.g(**self._foot_attributes)

    def vertex_group(self):
        return self._drawing.g(**self._vertex_attributes)

    def destruction_group(self):
        return self._drawing.g(**self._destruction_attributes)

    def activation_group(self):
        return self._drawing.g(**self._activation_attributes)

    def spine_group(self):
        return self._drawing.g(**self._spine_attributes)

    def edge_group(self):
        return self._drawing.g(**self._edge_attributes)

    @abstractmethod
    def _build_head_shape(self, symbol: Symbol): pass

    @abstractmethod
    def _build_foot_shape(self, symbol: Symbol): pass

    @abstractmethod
    def _build_vertex_shape(self, symbol: Symbol): pass

    @abstractmethod
    def _build_destruction_shape(self, symbol: Symbol): pass


# noinspection PyAbstractClass
class VerticalSymbols(SymbolSet):

    head_size: Tuple[int, int] = (100, 20)
    foot_size: Tuple[int, int] = (100, 20)
    vertex_radius: int = 5

    def __init__(self, drawing: Drawing):
        super().__init__(drawing)
        self._head = AlignBottomMiddle(self._drawing,
                                       self._build_head_shape,
                                       *self.head_size
                                       )
        self._foot = AlignTopMiddle(self._drawing,
                                    self._build_foot_shape,
                                    *self.foot_size
                                    )
        self._vertex = AlignCenterMiddle(self._drawing,
                                         self._build_vertex_shape,
                                         self.vertex_radius * 2,
                                         self.vertex_radius * 2
                                         )
        self._destruction = AlignCenterMiddle(self._drawing,
                                              self._build_destruction_shape,
                                              self.vertex_radius,
                                              self.vertex_radius
                                              )


class SimpleVerticalSymbols(VerticalSymbols):

    def __init__(self, drawing: Drawing):
        super().__init__(drawing)
        self._head_attributes = dict(fill='yellow', stroke='red',
                                     stroke_width=1)
        self._foot_attributes = dict(fill='yellow', stroke='red',
                                     stroke_width=1)
        self._vertex_attributes = dict(fill='black', stroke='black',
                                       stroke_width=0)
        self._destruction_attributes = dict(stroke='black', stroke_width=1)
        self._activation_attributes = dict(stroke='green', stroke_width=8)
        self._spine_attributes = dict(stroke='black', stroke_width=2)
        self._edge_attributes = dict(stroke='red', stroke_width=10)

    def _build_head_shape(self, symbol: Symbol):
        symbol.add(self._drawing.rect(insert=(0, 0),
                                      size=self.head_size,
                                      )
                   )

    def _build_foot_shape(self, symbol: Symbol):
        symbol.add(self._drawing.rect(insert=(0, 0),
                                      size=self.foot_size,
                                      )
                   )

    def _build_vertex_shape(self, symbol: Symbol):
        symbol.add(self._drawing.circle(center=(self.vertex_radius,
                                                self.vertex_radius),
                                        r=self.vertex_radius,
                                        )
                   )

    def _build_destruction_shape(self, symbol: Symbol):
        symbol.add(self._drawing.line(start=(0, 0),
                                      end=(self.vertex_radius,
                                           self.vertex_radius),
                                      )
                   )
        symbol.add(self._drawing.line(start=(0, self.vertex_radius),
                                      end=(self.vertex_radius, 0),
                                      )
                   )


class SVGRenderer(DiagramVisitor):
    S = TypeVar('S', bound=SymbolSet)

    def __init__(self, filename: str, symbol_set: Type[S]):
        self._drawing = Drawing(filename=filename, debug=True)
        self._symbols = symbol_set(self._drawing)
        self._heads: Group = self._symbols.head_group()
        self._feet: Group = self._symbols.foot_group()
        self._spines: Group = self._symbols.spine_group()
        self._vertices: Group = self._symbols.vertex_group()
        self._activations: Group = self._symbols.activation_group()
        self._edges: Group = self._symbols.edge_group()

    def visit_trace_diagram(self, de: TraceDiagram):
        # This is the last visit_*() method call
        for group in (self._spines, self._heads, self._feet,
                      self._activations, self._edges, self._vertices):
            self._drawing.add(group)

    def visit_life_line(self, de: LifeLine):
        pass

    def visit_head(self, de: Head):
        self._heads.add(self._symbols.head.at(de.position))

    def visit_vertex(self, de: Vertex):
        self._vertices.add(self._symbols.vertex.at(de.position))

    def visit_destruction(self, de: Destruction):
        self._vertices.add(self._symbols.destruction.at(de.position))

    def visit_activation(self, de: Activation):
        self._activations.add(
            self._symbols.activation.from_to(de.position, de.end_position)
        )

    def visit_foot(self, de: Foot):
        self._feet.add(self._symbols.foot.at(de.position))

    def visit_spine(self, de: Spine):
        self._spines.add(
            self._symbols.spine.from_to(de.position, de.end_position)
        )

    def visit_edge(self, de: Edge):
        self._edges.add(
            self._symbols.edge.from_to(de.position, de.end_position)
        )

    @property
    def drawing(self) -> Drawing: return self._drawing
