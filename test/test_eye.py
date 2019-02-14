import unittest

from tracent_eye.layout_generator import LayoutGenerator
from tracent_eye.svg_renderer import SVGRenderer, SimpleVerticalSymbols
from tracent_eye.trace_diagram import (
    TraceDiagram, LifeLine, Vertex, Destruction, Activation, Edge
    )


class TracentEyeTestCase(unittest.TestCase):

    def setUp(self):
        self.trace_diagram = TraceDiagram(0.0, 500.0)

    def test_simple_diagram(self):
        ll1 = LifeLine(self.trace_diagram)
        ll2 = LifeLine(self.trace_diagram)
        v1 = Vertex(0.0, {}, ll1)
        v2 = Vertex(0.2, {}, ll1)
        v3 = Vertex(0.21, {}, ll2)
        v4 = Destruction(0.29, {}, ll2)
        v5 = Vertex(0.3, {}, ll1)
        v6 = Destruction(0.35, {}, ll1)
        Activation(v1, v2)
        Edge(v2, v3)
        Activation(v3, v4)
        Edge(v4, v5)
        Activation(v5, v6)
        self.trace_diagram.accept(LayoutGenerator())
        renderer = SVGRenderer("simple_trace_diagram.svg",
                               SimpleVerticalSymbols)
        self.trace_diagram.accept(renderer)
        renderer._drawing.save(True)


if __name__ == '__main__':
    unittest.main()
