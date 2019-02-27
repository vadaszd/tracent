from abc import ABC, abstractmethod, ABCMeta
from typing import Dict, Type, TypeVar, Tuple, Callable, List

from svgwrite import Drawing
from svgwrite.base import BaseElement
from svgwrite.container import Symbol, Group

from tracent import TagDict
from .trace_diagram import (
    DiagramVisitor, TraceDiagram, LifeLine, Head, Foot,
    Spine, Vertex, Destruction, Activation, Edge,
    Point, DiagramElement)


class MockFont(object):

    def __init__(self, row_distance: float, glyph_width: float,
                 horizontal_margin: float, vertical_margin: float,
                 vertical_offset: float
                 ):
        """ Initialize a MockUserAgent instance

        :param row_distance: the distance among lines (the assumed EM)
        :param glyph_width:
        :param horizontal_margin:
        :param vertical_margin:
        :param vertical_offset:
        """
        self.row_distance, self.glyph_width, self.horizontal_margin = \
            row_distance,       glyph_width,      horizontal_margin,
        self.vertical_margin, self.vertical_offset = \
            vertical_margin,       vertical_offset

    def get_bounding_box(self, lines: List[str]
                         ) -> Tuple[Point, Tuple[int, int], int]:
        """ Get the bounding box for a list of lines rendered.

        The top middle of the box is going to be aligned on the (x, y)
        coordinates.

        :param lines: iterable of strings to be rendered

        :return: A 3-tuple;
                  -  the first element is a Point with the offset to the
                    top-center of the text(suitable for inserting
                    centered text),
                  - the second contains its width and height of the bounding
                    box as 2-tuple
                  - the third is the vertical distance dy to be used with
                    <tspan> elements
        """
        num_lines = len(lines)
        num_glyphs = max(len(line) for line in lines) if lines else 0
        width = (num_glyphs * self.glyph_width + self.horizontal_margin
                 ) * self.row_distance
        height = (num_lines + self.vertical_margin) * self.row_distance
        text_offset = Point(0.5 * width,
                            self.vertical_offset * self.row_distance
                            )
        return (text_offset,
                (int(width), int(height)),
                int(self.row_distance)
                )

    # def get_defult_shape_size(self):
    #     return Point(0, 0), \
    #            (int(self.row_distance), int(self.row_distance)), \
    #            mock_font.row_distance


mock_font = MockFont(
    row_distance=25.0, glyph_width=0.26, horizontal_margin=0.5,
    vertical_margin=0.4, vertical_offset=-0.1
)


class Shape(ABC):
    """ Abstract base class for creating and positioning trace diagram shapes

        Concrete derived classes wrap `svgwrite.base.BaseElement`s (more
        precisely, instances of derived classes of Baselement) representing the
        shapes and provide functionality to fill in their coordinates.
    """
    _drawing: Drawing
    _g: Group

    def __init__(self, drawing: Drawing, g: Group):
        """ Initialize a DotLikePositioner.

        :param drawing: The `svgwrite.Drawing` being worked on
        """
        self._drawing = drawing
        self._g = g


class PrebuiltShape(Shape):
    def __init__(self, drawing: Drawing, g: Group):
        """ Initialize a DotLikePositioner.

        :param drawing: The `svgwrite.Drawing` being worked on
        """
        super().__init__(drawing, g)
        self._drawing.defs.add(self._pre_build())

    @abstractmethod
    def _pre_build(self) -> BaseElement: pass


class DotLikeShape(PrebuiltShape):
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

    def __call__(self, de: DiagramElement) -> BaseElement:
        """ Place a `svgwrite.base.BaseElement` representing the shape at the
        given position.
        """
        lines = self._get_text_lines(de)
        text_offset, bb_size, row_distance = mock_font.get_bounding_box(lines)
        bb_insert = self._align_bb(de.position, bb_size)
        be = self._build_shape(lines, bb_insert, bb_size,
                               text_offset, row_distance
                               )
        self._g.add(be)
        return be

    @staticmethod
    def _get_text_lines(de: DiagramElement) -> List[str]:
        """

        :rtype:  List[str]
        """
        return list()

    @staticmethod
    @abstractmethod
    def _align_bb(position: Point, size: Tuple[int, int]) -> Point:
        pass

    @abstractmethod
    def _build_shape(self, lines: List[str],
                     bb_insert: Point, bb_size: Tuple[int, int],
                     text_offset: Point, row_distance: int
                     ) -> BaseElement:
        pass


class WithTags(DotLikeShape, ABC):
    @staticmethod
    def _get_text_lines(de: DiagramElement) -> List[str]:
        return ["{} = {}".format(k, v) for k, v in de.tags.items()]


class SymbolBasedShapeBuilder(DotLikeShape, ABC):
    _symbol: Symbol

    def _pre_build(self) -> BaseElement:
        self._symbol = self._drawing.symbol()
        self._build_symbol()
        return self._symbol

    @abstractmethod
    def _build_symbol(self): pass

    def _build_shape(self, lines: List[str],
                     bb_insert: Point, bb_size: Tuple[int, int],
                     text_offset: Point, row_distance: int
                     ) -> BaseElement:
        width, height = bb_size
        text_insert = bb_insert + text_offset
        g: Group = self._drawing.g()
        g.add(self._drawing.use(self._symbol,
                                x=bb_insert.x, y=bb_insert.y,
                                width=width, height=height
                                )
              )
        text = self._drawing.text("", insert=text_insert,
                                  **{'text-anchor': 'middle'}
                                  )
        for line in lines:
            text.add(self._drawing.tspan(line, x=[text_insert.x],
                                         dy=[row_distance]
                                         )
                     )
        self._drawing.add(text)
        g.add(text)
        return g


class Rectangle(SymbolBasedShapeBuilder, ABC):
    def __init__(self, drawing: Drawing, g: Group, size: Tuple[float, float]):
        self._size = tuple(map(lambda x: int(x * mock_font.row_distance), size))
        super().__init__(drawing, g)

    def _build_symbol(self):
        self._symbol.add(self._drawing.rect(insert=(0, 0), size=self._size,)
                         )
        self._symbol.viewbox(0, 0, *self._size)
        self._symbol.stretch()


class Circle(SymbolBasedShapeBuilder, ABC):
    def __init__(self, drawing: Drawing, g: Group, radius: float):
        self._radius = int(radius * mock_font.row_distance)
        super().__init__(drawing, g)

    def _build_symbol(self):
        diameter = 2 * self._radius
        self._symbol.add(self._drawing.circle(
            center=(self._radius, self._radius), r=self._radius, )
            )
        self._symbol.viewbox(0, 0, diameter, diameter)


class XCross(SymbolBasedShapeBuilder, ABC):
    def __init__(self, drawing: Drawing, g: Group, size: Tuple[float, float]):
        self._size = tuple(map(lambda x: int(x * mock_font.row_distance), size))
        super().__init__(drawing, g)

    def _build_symbol(self):
        width, height = self._size
        self._symbol.add(
            self._drawing.line(start=(0, 0), end=self._size,)
        )
        self._symbol.add(
            self._drawing.line(start=(0, height), end=(width, 0),)
        )
        self._symbol.viewbox(0, 0, width, height)


# Mixin classes (traits) providing various alignment strategies
class AlignTopMiddle(DotLikeShape, ABC):
    @staticmethod
    def _align_bb(position: Point, size: Tuple[int, int]) -> Point:
        """ Place the symbol aligning its top middle at the given point
        """
        width, height = size
        return Point(position.x - width/2, position.y)


class AlignBottomMiddle(DotLikeShape, ABC):
    @staticmethod
    def _align_bb(position: Point, size: Tuple[int, int]) -> Point:

        """ Place the symbol aligning its bottom middle at the given point
        """
        width, height = size
        return Point(position.x - width/2, position.y - height)


class AlignCenterMiddle(DotLikeShape, ABC):
    @staticmethod
    def _align_bb(position: Point, size: Tuple[int, int]) -> Point:
        """ Place the symbol aligning its center middle at the given point
        """
        width, height = size
        return Point (position.x - width/2, position.y - height/2)


class AlignCenterLeft(DotLikeShape, ABC):
    @staticmethod
    def _align_bb(position: Point, size: Tuple[int, int]) -> Point:
        """ Place the symbol aligning its center left at the given point
        """
        width, height = size
        return Point (position.x, position.y - height/2)


class AlignCenterRight(DotLikeShape, ABC):
    @staticmethod
    def _align_bb(position: Point, size: Tuple[int, int]) -> Point:
        """ Place the symbol aligning its center right at the given point
        """
        width, height = size
        return Point(position.x - width, position.y - height/2)


class LineLikeShape(Shape):
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

    def __call__(self, start: Point, end: Point) -> BaseElement:
        be = self._drawing.line(start=start, end=end)
        self._g.add(be)
        return be


class ArrowLikeShape(PrebuiltShape):
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

    # The below quantities are in multiples of line width
    # They need to be set as class attributes in derived classes
    _arrow_width: float
    _arrow_height: float
    _arrow_color: str

    def _pre_build(self) -> BaseElement:
        size = self._arrow_width, self._arrow_height
        self._arrow = self._drawing.marker(orient='auto', size=size,
                                           markerUnits='strokeWidth',
                                           insert=(0, 30),
                                           )
        self._arrow.viewbox(0, 0, 60, 60)
        self._arrow.stretch()
        self._build_arrow()
        return self._arrow

    # @abstractmethod
    def _build_arrow(self):
        self._arrow.add(self._drawing.path(d='M0,0 L0,60 L60,30 z',
                                           fill=self._arrow_color)
                        )

    def __call__(self, start: Point, end: Point) -> BaseElement:
        vector = end - start
        length = abs(vector)
        arrow_length = self._g['stroke-width'] * self._arrow_width
        line_end = start + vector * ((length - arrow_length) / length)
        be = self._drawing.line(start=start, end=line_end,
                                marker_end=self._arrow.get_funciri())
        self._g.add(be)
        return be


class ActivationArrow(ArrowLikeShape):
    _arrow_width = 1.0
    _arrow_height = 1.4
    _arrow_color = "darkgreen"


class EdgeArrow(ArrowLikeShape):
    _arrow_width = 3
    _arrow_height = 3
    _arrow_color = "black"


class SymbolSet(ABC):
    """ Abstract class defining the appearance of trace diagram symbols
    """
    _head: DotLikeShape
    _foot: DotLikeShape
    _vertex: DotLikeShape
    _destruction: DotLikeShape
    _activation: ArrowLikeShape
    _spine: LineLikeShape
    _edge: ArrowLikeShape

    _head_attributes: Dict[str, str]
    _foot_attributes: Dict[str, str]
    _vertex_attributes: Dict[str, str]
    _destruction_attributes: Dict[str, str]
    _activation_attributes: Dict[str, str]
    _spine_attributes: Dict[str, str]
    _edge_attributes: Dict[str, str]

    def _make_builder(self, name, bases, group, **kwargs):
        return ABCMeta(name, bases, {})\
            (self._drawing, group(), **kwargs)

    def __init__(self, drawing: Drawing):
        self._drawing = drawing
        self._vertex = self._make_builder(
            "Vertex", (Circle, AlignCenterMiddle), self.vertex_group,
            radius=0.1
        )
        self._destruction = self._make_builder(
            "Destruction", (XCross, AlignCenterMiddle), self.destruction_group,
            size=(0.2, 0.2)
        )
        self._spine = LineLikeShape(self._drawing, self.spine_group())
        self._activation = ActivationArrow(self._drawing, self.activation_group())
        self._edge = EdgeArrow(self._drawing, self.edge_group())

    @property
    def head(self) -> DotLikeShape:
        """ The symbol used for heads"""
        return self._head

    @property
    def foot(self) -> DotLikeShape:
        """ The symbol used for feet"""
        return self._foot

    @property
    def vertex(self) -> DotLikeShape:
        """ The symbol used for vertices"""
        return self._vertex

    @property
    def destruction(self) -> DotLikeShape:
        """ The symbol used for destructions"""
        return self._destruction

    @property
    def activation(self) -> ArrowLikeShape:
        """ The symbol used for activations"""
        return self._activation

    @property
    def spine(self) -> LineLikeShape:
        """ The symbol used for spines"""
        return self._spine

    @property
    def edge(self) -> ArrowLikeShape:
        """ The symbol used for edges"""
        return self._edge

    def head_group(self):
        g = self._drawing.g(**self._head_attributes)
        self._drawing.add(g)
        return g

    def foot_group(self):
        g = self._drawing.g(**self._foot_attributes)
        self._drawing.add(g)
        return g

    def vertex_group(self):
        g = self._drawing.g(**self._vertex_attributes)
        self._drawing.add(g)
        return g

    def destruction_group(self):
        g = self._drawing.g(**self._destruction_attributes)
        self._drawing.add(g)
        return g

    def activation_group(self):
        g = self._drawing.g(**self._activation_attributes)
        self._drawing.add(g)
        return g

    def spine_group(self):
        g = self._drawing.g(**self._spine_attributes)
        self._drawing.add(g)
        return g

    def edge_group(self):
        g = self._drawing.g(**self._edge_attributes)
        self._drawing.add(g)
        return g


# noinspection PyAbstractClass
class VerticalSymbols(SymbolSet):

    head_size: Tuple[int, int] = (100, 20)
    foot_size: Tuple[int, int] = (100, 20)
    vertex_radius: int = 5

    def __init__(self, drawing: Drawing):
        super().__init__(drawing)
        self._head = self._make_builder(
            "Head", (Rectangle, AlignBottomMiddle, WithTags), self.head_group,
            size=(1, 1)
        )
        self._foot = self._make_builder(
            "Foot", (Rectangle, AlignTopMiddle, WithTags), self.foot_group,
            size=(1, 1)
        )


class SimpleVerticalSymbols(VerticalSymbols):

    def __init__(self, drawing: Drawing):
        self._head_attributes = dict(fill='yellow', stroke='brown',
                                     stroke_width=1)
        self._foot_attributes = dict(fill='yellow', stroke='brown',
                                     stroke_width=1)
        self._vertex_attributes = dict(fill='black', stroke='black',
                                       stroke_width=0)
        self._destruction_attributes = dict(stroke='black', stroke_width=1)
        self._activation_attributes = dict(stroke='lightseagreen', stroke_width=8)
        self._spine_attributes = dict(stroke='#b3b3b3', stroke_width=2)
        self._edge_attributes = dict(stroke='darkred', stroke_width=3)
        super().__init__(drawing)


class SVGRenderer(DiagramVisitor):
    S = TypeVar('S', bound=SymbolSet)

    def __init__(self, filename: str, symbol_set: Type[S]):
        self._drawing = Drawing(filename=filename, debug=True)
        self._symbols = symbol_set(self._drawing)

    def visit_trace_diagram(self, de: TraceDiagram):
        # This is the last visit_*() method call
        symbols = self._symbols
        for shape_builder in (
                symbols.spine, symbols.head, symbols.foot,
                symbols.activation, symbols.edge, symbols.vertex,
                symbols.destruction
        ):
            self._drawing.add(shape_builder._g)

    def visit_life_line(self, de: LifeLine):
        pass

    def visit_head(self, head: Head):
        self._symbols.head(head)

    def visit_vertex(self, de: Vertex):
        self._symbols.vertex(de)

    def visit_destruction(self, de: Destruction):
        self._symbols.destruction(de)

    def visit_activation(self, de: Activation):
        self._symbols.activation(de.position, de.end_position)

    def visit_foot(self, de: Foot):
        self._symbols.foot(de)

    def visit_spine(self, de: Spine):
        self._symbols.spine(de.position, de.end_position)

    def visit_edge(self, de: Edge):
        self._symbols.edge(de.position, de.end_position)

    @property
    def drawing(self) -> Drawing: return self._drawing

# https://www.lifewire.com/aspect-ratio-table-common-fonts-3467385
# Arial	0.52
# Avant Garde	0.45
# Bookman	0.40
# Calibri	0.47
# Century Schoolbook	0.48
# Cochin	0.41
# Comic Sans	0.53
# Courier	0.43
# Courier New	0.42
# Garamond	0.38
# Georgia	0.48
# Helvetica	0.52
# Palatino	0.42
# Tahoma	0.55
# Times New Roman	0.45
# Trebuchet	0.52
# Verdana	0.58
