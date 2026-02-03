#!/usr/bin/env python3
"""
Workspace Explorer - CLI Script
Starts code-server with a Cloudflare tunnel for secure remote access.
Outputs connection details directly to terminal.
"""

import os
import sys
import subprocess
import secrets
import signal
import time
import re
import argparse

# Configuration
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
BIN_DIR = os.path.join(BASE_DIR, "bin")

CODE_SERVER_VERSION = "4.96.2"
CODE_SERVER_URL = f"https://github.com/coder/code-server/releases/download/v{CODE_SERVER_VERSION}/code-server-{CODE_SERVER_VERSION}-linux-amd64.tar.gz"
CLOUDFLARED_URL = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"

# Ensure bin directory exists
os.makedirs(BIN_DIR, exist_ok=True)

def get_binary_path(name):
    if name == "code-server":
        return os.path.join(BIN_DIR, f"code-server-{CODE_SERVER_VERSION}-linux-amd64", "bin", "code-server")
    return os.path.join(BIN_DIR, name)

def download_binaries():
    """Download code-server and cloudflared if not present."""
    cf_path = get_binary_path("cloudflared")
    if not os.path.exists(cf_path):
        print("📥 Downloading cloudflared...")
        subprocess.run(["curl", "-L", CLOUDFLARED_URL, "-o", cf_path], check=True)
        subprocess.run(["chmod", "+x", cf_path], check=True)
        print("✅ cloudflared installed.")
    
    cs_bin = get_binary_path("code-server")
    if not os.path.exists(cs_bin):
        cs_tar = os.path.join(BIN_DIR, "code-server.tar.gz")
        print("📥 Downloading code-server...")
        subprocess.run(["curl", "-L", CODE_SERVER_URL, "-o", cs_tar], check=True)
        print("📦 Extracting code-server...")
        subprocess.run(["tar", "-xzf", cs_tar, "-C", BIN_DIR], check=True)
        os.remove(cs_tar)
        print("✅ code-server installed.")

def main():
    parser = argparse.ArgumentParser(
        description="Start a secure remote workspace session.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s /path/to/workspace
  %(prog)s /path/to/workspace --port 9000
  %(prog)s .  # Current directory
        """
    )
    parser.add_argument("workspace", help="Path to the workspace directory to serve")
    parser.add_argument("--port", type=int, default=8080, help="Local port for code-server (default: 8080)")
    args = parser.parse_args()

    workspace = os.path.abspath(args.workspace)
    if not os.path.isdir(workspace):
        print(f"❌ Error: '{workspace}' is not a valid directory.")
        sys.exit(1)

    # Download binaries if needed
    download_binaries()

    # Generate password
    password = secrets.token_urlsafe(12)
    
    print("\n" + "="*60)
    print("🚀 STARTING WORKSPACE SESSION")
    print("="*60)
    print(f"📁 Workspace: {workspace}")
    print(f"🔑 Password:  {password}")
    print("="*60 + "\n")

    # Start code-server
    cs_bin = get_binary_path("code-server")
    env = os.environ.copy()
    env["PASSWORD"] = password
    
    print("🖥️  Starting code-server...")
    code_server_proc = subprocess.Popen(
        [
            cs_bin,
            "--bind-addr", f"127.0.0.1:{args.port}",
            "--auth", "password",
            "--disable-telemetry",
            workspace
        ],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    # Give code-server time to start
    time.sleep(2)
    
    # Start cloudflared tunnel
    cf_bin = get_binary_path("cloudflared")
    print("🌐 Starting Cloudflare tunnel...")
    
    tunnel_proc = subprocess.Popen(
        [cf_bin, "tunnel", "--url", f"http://127.0.0.1:{args.port}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    # Capture tunnel URL
    url_pattern = re.compile(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com')
    tunnel_url = None

    def cleanup(sig=None, frame=None):
        print("\n\n🛑 Shutting down...")
        tunnel_proc.terminate()
        code_server_proc.terminate()
        try:
            tunnel_proc.wait(timeout=3)
            code_server_proc.wait(timeout=3)
        except:
            tunnel_proc.kill()
            code_server_proc.kill()
        print("👋 Session terminated.")
        sys.exit(0)

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    # Read tunnel output to find URL
    try:
        for line in iter(tunnel_proc.stdout.readline, ""):
            if tunnel_proc.poll() is not None:
                print("❌ Tunnel process exited unexpectedly.")
                cleanup()
                break
            
            match = url_pattern.search(line)
            if match:
                tunnel_url = match.group(0)
                break
    except Exception as e:
        print(f"❌ Error reading tunnel output: {e}")
        cleanup()

    if tunnel_url:
        print("\n" + "="*60)
        print("✅ WORKSPACE READY!")
        print("="*60)
        print(f"🌐 URL:      {tunnel_url}")
        print(f"🔑 Password: {password}")
        print("="*60)
        print("\n💡 Share the URL and password with your owner.")
        print("   Press Ctrl+C to terminate the session.\n")
        
        # Keep running and forward any tunnel output
        try:
            while True:
                line = tunnel_proc.stdout.readline()
                if not line:
                    break
                # Optionally print tunnel logs (commented out to reduce noise)
                # print(f"[tunnel] {line.strip()}")
        except KeyboardInterrupt:
            cleanup()
    else:
        print("❌ Failed to establish tunnel.")
        cleanup()

if __name__ == "__main__":
    main()
