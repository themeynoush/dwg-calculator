"""Run the graph once over the uploads folder."""
from src.graph import build_graph
from src.state import CatalogEntry, PipelineState


def run_pipeline(uploads_dir: str, output_dir: str, force: bool = False) -> list[CatalogEntry]:
    state = PipelineState(uploads_dir=uploads_dir, output_dir=output_dir, force=force)
    return build_graph().invoke(state)["catalog"]
