import unittest

from tracent_eye.layout_generator import LayoutGenerator
from tracent_eye.svg_renderer import SVGRenderer, SimpleVerticalSymbols, mock_user_agent_font
from tracent_eye.trace_diagram import (
    TraceDiagram, LifeLine, Vertex, Destruction, Activation, Edge
    )


class TracentEyeTestCase(unittest.TestCase):

    def setUp(self):
        self.trace_diagram = TraceDiagram(0.0, 500.0)

    def test_simple_diagram(self):
        ll1 = LifeLine(self.trace_diagram, {})
        ll2 = LifeLine(self.trace_diagram, {})
        v1 = Vertex(ll1, 0.0, {})
        v2 = Vertex(ll1, 0.2, {})
        v3 = Vertex(ll2, 0.21, {})
        v4 = Destruction(ll2, 0.29, {})
        v5 = Vertex(ll1, 0.3, {})
        v6 = Destruction(ll1, 0.35, {})
        Activation(v1, v2)
        Edge(v2, v3)
        Activation(v3, v4)
        Edge(v4, v5)
        Activation(v5, v6)
        self.trace_diagram.accept(LayoutGenerator())
        renderer = SVGRenderer("simple_trace_diagram.svg",
                               SimpleVerticalSymbols)
        self.trace_diagram.accept(renderer)

        def f(x, y, lines):
            bb_xy, bb_wh, dy = mock_user_agent_font.get_bounding_box(x, y, lines)
            renderer._drawing.add(
                renderer._drawing.rect(insert=bb_xy, size=bb_wh,
                                       stroke="black", stroke_width=2,
                                       fill="none"))
            t = renderer._drawing.text("", insert=(x, y), **{'text-anchor': 'middle'})
            for line in lines:
                t.add(renderer._drawing.tspan(line, x=[x], dy=[dy]))
            renderer._drawing.add(t)

        f(300, 20, ["The aspect ratio that uses",])
        f(400, 60, ["X the color profile description database for a color profile description entry whose name des",
                    " data show the ratio of the requested height of the font to the actual"])
        f(300, 150, ["pecified, the font is ", "scaled so that its ", "em square has a side length ",
                     "of that particular length", "scaled so that its ", "em square has a side length ",
                     "of that particular length", "scaled so that its ", "em square has a side length ",
                     "of that particular length", "scaled so that its ", "em square has a side length ",
                     " data show the ratio of the requested ", "height of the font to the actual"])

        renderer._drawing.save(True)


if __name__ == '__main__':
    unittest.main()
