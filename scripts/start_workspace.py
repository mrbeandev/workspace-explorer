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
    # Create data and logs directory
    data_dir = os.path.join(BASE_DIR, "data")
    user_data_dir = os.path.join(data_dir, "user-data")
    settings_dir = os.path.join(user_data_dir, "User")
    os.makedirs(settings_dir, exist_ok=True)
    
    # Create settings.json to disable git and other features
    settings_path = os.path.join(settings_dir, "settings.json")
    settings_content = {
        "git.enabled": False,
        "github.enabled": False,
        "git.autorefresh": False,
        "git.autofetch": False,
        "workbench.startupEditor": "none",
        "telemetry.enableTelemetry": False,
        "workbench.enableExperiments": False,
        "update.mode": "none"
    }
    import json
    with open(settings_path, "w") as f:
        json.dump(settings_content, f, indent=4)

    log_dir = os.path.join(BASE_DIR, "logs")
    os.makedirs(log_dir, exist_ok=True)
    cs_log_path = os.path.join(log_dir, "code-server.log")
    cf_log_path = os.path.join(log_dir, "cloudflared.log")

    print("🖥️  Starting code-server...")
    cs_log_file = open(cs_log_path, "w")
    code_server_proc = subprocess.Popen(
        [
            cs_bin,
            "--bind-addr", f"127.0.0.1:{args.port}",
            "--auth", "password",
            "--disable-telemetry",
            "--user-data-dir", user_data_dir,
            workspace
        ],
        env=env,
        stdout=cs_log_file,
        stderr=subprocess.STDOUT
    )

    def wait_for_port(port, timeout=15):
        import socket
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=1):
                    return True
            except (socket.timeout, ConnectionRefusedError):
                if code_server_proc.poll() is not None:
                    return False
                time.sleep(0.5)
        return False

    print(f"⏳ Waiting for code-server to bind to port {args.port}...")
    if not wait_for_port(args.port):
        print("❌ Error: code-server failed to start or bind to port in time.")
        print(f"📄 Check logs at: {cs_log_path}")
        code_server_proc.terminate()
        sys.exit(1)
    
    # Start cloudflared tunnel
    cf_bin = get_binary_path("cloudflared")
    print("🌐 Starting Cloudflare tunnel...")
    
    cf_log_file = open(cf_log_path, "w")
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
        cs_log_file.close()
        cf_log_file.close()
        print("👋 Session terminated.")
        sys.exit(0)

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    # Read tunnel output to find URL
    try:
        for line in iter(tunnel_proc.stdout.readline, ""):
            cf_log_file.write(line)
            cf_log_file.flush()
            
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
        print("⏳ Note: Please wait 15-30 seconds for the URL to become active.")
        print(f"📄 Logs:     {log_dir}")
        print("   Press Ctrl+C to terminate the session.\n")
        
        # Keep logging in background
        try:
            while True:
                line = tunnel_proc.stdout.readline()
                if not line:
                    break
                cf_log_file.write(line)
                cf_log_file.flush()
        except KeyboardInterrupt:
            cleanup()
    else:
        print("❌ Failed to establish tunnel.")
        print(f"📄 Check logs at: {cf_log_path}")
        cleanup()

if __name__ == "__main__":
    main()
