"""kb-ui CLI entry — warm up the model, then run uvicorn and open the browser."""

import sys
import threading
import webbrowser

from knowledge_semantic.ui.app import create_app
from knowledge_semantic.ui.config import HOST, PORT
from knowledge_semantic.ui.services.kb import warmup


def _open_browser_when_ready(url):
    def _open():
        webbrowser.open(url)

    threading.Timer(0.8, _open).start()


def main():
    print("[kb-ui] warming up sentence-transformers model...", file=sys.stderr)
    try:
        warmup()
    except Exception as e:
        print(f"[kb-ui] warmup failed (non-fatal): {e}", file=sys.stderr)

    import uvicorn

    url = f"http://{HOST}:{PORT}"
    print(f"[kb-ui] serving at {url}", file=sys.stderr)
    _open_browser_when_ready(url)

    uvicorn.run(create_app(), host=HOST, port=PORT, log_level="info")


if __name__ == "__main__":
    main()
