#!/usr/bin/env python
"""
SAGE API Server Launcher
========================
Simple script to launch the SAGE API server for remote access.

Usage:
    python run_server.py              # Default: 0.0.0.0:8000
    python run_server.py --port 5000  # Custom port
    python run_server.py --host 127.0.0.1 --port 8080  # Custom host and port

Remote Access:
    After starting, access the API from other machines using:
    http://<your-ip-address>:<port>/docs
"""
import argparse
import socket
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent))


def get_local_ip():
    """Get local IP address for network access"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"


def main():
    parser = argparse.ArgumentParser(
        description="SAGE API Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python run_server.py                    # Start on all interfaces, port 8000
    python run_server.py --port 5000        # Use custom port
    python run_server.py --host 127.0.0.1   # Localhost only
        """
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind (default: 0.0.0.0 for all interfaces)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind (default: 8000)"
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development"
    )

    args = parser.parse_args()

    # Get local IP for display
    local_ip = get_local_ip()

    print()
    print("=" * 60)
    print("  SAGE API Server - Remote Access")
    print("=" * 60)
    print()
    print(f"  Local URL:     http://localhost:{args.port}")
    print(f"  Network URL:   http://{local_ip}:{args.port}")
    print(f"  API Docs:      http://localhost:{args.port}/docs")
    print()
    print("  Endpoints:")
    print(f"    GET  /status          - System status")
    print(f"    POST /age/upload      - Upload and age photo")
    print(f"    POST /age/photo       - Age photo from base64")
    print(f"    POST /chat            - Chat with elderly self")
    print(f"    GET  /chat/history/   - Get chat history")
    print()
    print("=" * 60)
    print("  Press Ctrl+C to stop the server")
    print("=" * 60)
    print()

    # Import and run
    try:
        import uvicorn
        from src.api import app

        uvicorn.run(
            "src.api:app" if args.reload else app,
            host=args.host,
            port=args.port,
            reload=args.reload
        )
    except ImportError as e:
        print(f"Error: Missing dependency - {e}")
        print("Please run: pip install -r requirements.txt")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n  Server stopped.")


if __name__ == "__main__":
    main()
