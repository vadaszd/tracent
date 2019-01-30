
""" Capture the structure of a diagram visualizing an event-based trace.

    A trace diagram is visually similar to a UML sequence diagram.
"""

from typing import Dict, List


#  https://www.uml-diagrams.org/sequence-diagrams.html
class TraceDiagram:
    """ A UML sequence diagram like representation of a trace

        A collection of
            - life-lines representing EUs and events happening on them
            - edges representing ordering constraints between events
    """
    life_lines: List['Lifeline']
    edges: List['Edge']


class Lifeline:
    """ A UML life-line like representation of an EU in a trace diagram
    """
    head: 'Head'
    spine: 'Spine'
    foot: 'Foot'
    vertices: List['Vertex']  #  sorted by time_offset
    activations: List['Activation']
    start_time: float
    clock_skew: float

    class Head:
        """ The shape at the top of the life-line containing its description.
        """
        eu_tags: Dict[str, TagType]

    class Foot:
        """ An optional repetition of the Head at the bottom end of the spine.

            If there is a Destruction shape on the life-line, the foot must be
            placed below it.
        """

    class Spine:
        """ The thin vertical line of the life-line """

    class Vertex:
        """ A dot-like shape representing an event on the EU"""
        time_offset: float
        tags: Dict[str, TagType]

    class Destruction:
        """ A shape representing an event of type FINISH_EU

            The spine ceases at this shape. May be followed by a Foot.
        """

    class Activation:
        """ A widened  section of the Spine representing a non-idle EU state

            Must be bounded by vertices.
            The graphical representation may suggest a top-down directionality.
            Represents an ordering constraint between two events on the same EU.
        """
        fro: 'Lifeline.Vertex'
        to: 'Lifeline.Vertex'
        status: pb.Event.Status


class Edge:
    """ A directed line connecting two vertices placed on different life-lines

        Represents an ordering constraint between two events on different EUs.
    """
    fro: Lifeline.Vertex
    to: Lifeline.Vertex
