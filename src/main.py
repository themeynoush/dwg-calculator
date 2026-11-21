"""Entrypoint: process uploads/ then serve the viewer on http://localhost:PORT."""
import argparse
import logging

import uvicorn

from src.pipeline import run_pipeline
from src.server import OUTPUT_DIR, UPLOADS_DIR, create_app


def main() -> None:
    parser = argparse.ArgumentParser(description="DWG 3D viewer")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--force", action="store_true", help="reprocess every DWG file")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    logging.getLogger("ezdxf").setLevel(logging.ERROR)  # LibreDWG output quirks are auto-fixed
    run_pipeline(str(UPLOADS_DIR), str(OUTPUT_DIR), force=args.force)
    logging.info("Open http://localhost:%d in your browser", args.port)
    uvicorn.run(create_app(), host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
