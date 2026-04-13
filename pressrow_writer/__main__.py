"""CLI entry point for Press Row Writer's Room.

Subcommands:
    serve   — start the local web server (default)
    batch   — pre-generate obsession candidates for Swipe mode
"""
import sys
import threading
import time
import webbrowser

from pressrow_writer import config_io, server


def _open_browser_after_delay(url: str, delay: float = 0.6):
    """Open the browser shortly after the server starts listening."""
    def _open():
        time.sleep(delay)
        try:
            webbrowser.open(url)
        except Exception:
            pass
    threading.Thread(target=_open, daemon=True).start()


def cmd_serve():
    config_io.ensure_dirs()
    _open_browser_after_delay(f"http://{server.HOST}:{server.PORT}")
    server.serve()


def cmd_batch():
    from pressrow_writer import batch_obsessions
    batch_obsessions.main(sys.argv[2:])


def main():
    argv = sys.argv[1:]
    cmd = argv[0] if argv else "serve"

    if cmd == "serve":
        cmd_serve()
    elif cmd == "batch":
        cmd_batch()
    elif cmd in ("-h", "--help", "help"):
        print(__doc__)
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
