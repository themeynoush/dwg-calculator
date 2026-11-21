"""Pipeline definition: wires the nodes into a LangGraph state graph.

scan → convert → parse → extract_geometry → export_gltf → build_catalog
"""
from langgraph.graph import END, START, StateGraph

from src.nodes.build_catalog import build_catalog
from src.nodes.convert import convert
from src.nodes.export_gltf import export_gltf
from src.nodes.extract_geometry import extract_geometry
from src.nodes.parse import parse
from src.nodes.scan import scan
from src.state import PipelineState

NODES = [scan, convert, parse, extract_geometry, export_gltf, build_catalog]


def build_graph():
    graph = StateGraph(PipelineState)
    for node in NODES:
        graph.add_node(node.__name__, node)
    graph.add_edge(START, NODES[0].__name__)
    for current, nxt in zip(NODES, NODES[1:], strict=False):
        graph.add_edge(current.__name__, nxt.__name__)
    graph.add_edge(NODES[-1].__name__, END)
    return graph.compile()
