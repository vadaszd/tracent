from typing import Dict

from .trace_diagram import (
    DiagramVisitor, Point, TraceDiagram, LifeLine, Head, Foot,
    Spine, Vertex, Destruction, _BaseEdge, Activation, Edge
)


class LayoutGenerator(DiagramVisitor):

    life_line_displacement = Point(150, 0)  # displacement between life lines
    origin_displacement = Point(0, 30)
    directed_scale: Point
    last_vertex_by_life_line: Dict[LifeLine, Vertex]

    def __init__(self):
        self.num_life_lines: float = 0.0
        self.last_vertex_by_life_line = dict()

    def visit_trace_diagram(self, de: TraceDiagram):
        de.position = Point(100, 100)
        self.directed_scale = Point(0, de.time_scale)

    def visit_life_line(self, de: LifeLine):
        de.position = (de.trace_diagram.position + self.origin_displacement +
                       self.life_line_displacement * self.num_life_lines)
        de.time_axes_origin = self.origin_displacement + de.position
        self.num_life_lines += 1.0

    def visit_head(self, de: Head):
        de.position = de.life_line.position

    def visit_vertex(self, de: Vertex):
        de.position = (de.life_line.time_axes_origin +
                       self.directed_scale * de.time_offset)
        try:
            last_vertex = self.last_vertex_by_life_line[de.life_line]
        except KeyError:
            self.last_vertex_by_life_line[de.life_line] = de
        else:
            if de.time_offset > last_vertex.time_offset:
                self.last_vertex_by_life_line[de.life_line] = de

    def visit_destruction(self, de: Destruction):
        return self.visit_vertex(de)

    def visit_activation(self, de: Activation):
        self._visit_base_edge(de)

    def visit_foot(self, de: Foot):
        try:
            last_vertex = self.last_vertex_by_life_line[de.life_line]
        except KeyError:
            last_vertex_position = de.life_line.time_axes_origin
        else:
            last_vertex_position = last_vertex.position
        de.position = last_vertex_position + self.origin_displacement

    def visit_spine(self, de: Spine):
        de.position = de.life_line.head.position
        de.end_position = de.life_line.foot.position

    def visit_edge(self, de: Edge):
        self._visit_base_edge(de)

    # Common implementation for Activation and Edge, never called
    # directly from any accept() method
    @staticmethod
    def _visit_base_edge(de: _BaseEdge):
        de.position = de.fro.position
        de.end_position = de.to.position

