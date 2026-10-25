"""Start the SmartBrew AI prototype on http://127.0.0.1:5000.

Usage:
    python run.py            # start (creates and seeds the database on first run)
    python run.py --reset    # delete the database first, then start with fresh demo data
"""

import os
import sys

from smartbrew import create_app


def main(argv):
    """Create the app (optionally after resetting the database) and run the dev server.

    Inputs:  argv – command-line arguments; ``--reset`` deletes instance/smartbrew.sqlite,
             ``--port N`` changes the port (default 5000).
    Returns: None (blocks while the server runs).
    """
    if "--reset" in argv:
        db_path = os.path.join(os.path.dirname(__file__), "instance", "smartbrew.sqlite")
        if os.path.exists(db_path):
            os.remove(db_path)
            print("Database reset.")
    port = int(argv[argv.index("--port") + 1]) if "--port" in argv else 5000
    app = create_app()
    print(f"SmartBrew AI running on http://127.0.0.1:{port}")
    app.run(host="127.0.0.1", port=port, debug=False)


if __name__ == "__main__":
    main(sys.argv[1:])
