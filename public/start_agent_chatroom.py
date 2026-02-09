# -*- coding: utf-8 -*-
import asyncio
import json
import sys
import argparse
from datetime import datetime
from urllib.parse import urlparse
from urllib.request import Request, urlopen

import websockets

# Config
DEFAULT_BASE_URL = "https://workers-chat.hacolby.workers.dev"

# ANSI Colors
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"
BOLD = "\033[1m"

def print_usage():
    print(f"""
{BOLD}{RED}❌ Error: Agent Name Required{RESET}

{BOLD}Usage:{RESET}
    python start_agent_chatroom.py <AGENT_NAME> [options]

{BOLD}Examples:{RESET}
    python start_agent_chatroom.py "Investigator-Unit-01"
    python start_agent_chatroom.py "Legal-Analyst" --room incident-bridge

{BOLD}Options:{RESET}
    --room          Room name to join (defaults to a new private room)
    -u, --url       Base URL (default: {DEFAULT_BASE_URL})
    -h, --help      Show this help message
    """)

def normalize_base_urls(raw_url):
    base = (raw_url or DEFAULT_BASE_URL).strip()
    if "://" not in base:
        base = "https://" + base
    parsed = urlparse(base)
    scheme = parsed.scheme
    netloc = parsed.netloc or parsed.path
    if scheme in ("ws", "wss"):
        ws_scheme = scheme
        http_scheme = "https" if scheme == "wss" else "http"
    else:
        http_scheme = scheme
        ws_scheme = "wss" if scheme == "https" else "ws"
    return f"{http_scheme}://{netloc}", f"{ws_scheme}://{netloc}"

def create_private_room(http_origin):
    request = Request(f"{http_origin}/api/room", method="POST")
    with urlopen(request) as response:
        return response.read().decode().strip()

async def chat_client(agent_name, room_name, http_origin, ws_origin):
    ws_url = f"{ws_origin}/api/room/{room_name}/websocket"
    print(f"\n{CYAN}🔌 Connecting to {ws_url} as '{agent_name}'...{RESET}")
    print(f"{YELLOW}🔗 Share this room: {http_origin}/#{room_name}{RESET}\n")
    
    try:
        async with websockets.connect(ws_url) as ws:
            print(f"{GREEN}✅ Connected! Joined the chatroom.{RESET}")
            print(f"{YELLOW}👉 Type a message and press Enter to send. (Ctrl+C to quit){RESET}\n")

            # 1. Handshake
            await ws.send(json.dumps({
                "type": "join",
                "name": agent_name
            }))

            # 2. Define Tasks
            loop = asyncio.get_running_loop()
            
            async def receive_loop():
                """Listen for incoming messages."""
                try:
                    async for message in ws:
                        try:
                            data = json.loads(message)
                            if data.get("error"):
                                print(f"\n{RED}❌ Error: {data['error']}{RESET}")
                                continue
                            if data.get("ready"):
                                continue

                            msg_type = data.get("type")
                            sender = data.get("name") or data.get("sender") or "Unknown"
                            content = data.get("message") or data.get("content") or ""
                            if not msg_type and not content:
                                continue

                            # Skip own messages (optional, but good for cleanliness)
                            if sender == agent_name:
                                continue

                            # Colorize based on sender info
                            color = CYAN
                            if msg_type == "join":
                                content = f"{sender} joined"
                                sender = "System"
                                color = YELLOW
                            elif msg_type == "quit":
                                content = f"{sender} left"
                                sender = "System"
                                color = YELLOW
                            elif msg_type == "SYSTEM":
                                color = YELLOW
                            
                            timestamp = datetime.now().strftime("%H:%M:%S")
                            print(f"\r{color}[{timestamp}] {BOLD}{sender}:{RESET} {content}")
                            
                            # Re-print prompt
                            print(f"{BOLD}{agent_name}>{RESET} ", end="", flush=True)
                            
                        except json.JSONDecodeError:
                            pass
                except websockets.exceptions.ConnectionClosed:
                    print(f"\n{RED}❌ Connection closed by server.{RESET}")
                    sys.exit(0)

            async def send_loop():
                """Read stdin and send messages."""
                while True:
                    # Non-blocking input reading is tricky in asyncio without extra deps (like aioconsole)
                    # We use run_in_executor to block only this task, not the loop.
                    print(f"{BOLD}{agent_name}>{RESET} ", end="", flush=True)
                    msg = await loop.run_in_executor(None, sys.stdin.readline)
                    if not msg: # EOF
                        break
                    
                    msg = msg.strip()
                    if msg:
                        # Move cursor up one line to overwrite the input line (aesthetic, optional)
                        # sys.stdout.write("\033[F\033[K") 
                        
                        payload = {"type": "message", "message": msg}
                        await ws.send(json.dumps(payload))

            # 3. Run Both Loops
            await asyncio.gather(receive_loop(), send_loop())

    except (ConnectionRefusedError, OSError):
        print(f"\n{RED}❌ Connection Failed. Is the server running at {ws_url}?{RESET}")
    except KeyboardInterrupt:
        print(f"\n{YELLOW}👋 Disconnected.{RESET}")
    except Exception as e:
        print(f"\n{RED}❌ Error: {e}{RESET}")

if __name__ == "__main__":
    # Custom Argument Handling to enforce the "Name Required" rule with nice output
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("name", nargs="?", default=None, help="Name of the agent joining the chat")
    parser.add_argument("--room", default=None, help="Room name to join")
    parser.add_argument("--url", default=DEFAULT_BASE_URL, help="Base URL")
    parser.add_argument("-h", "--help", action="store_true")

    args = parser.parse_args()

    if args.help or not args.name:
        print_usage()
        sys.exit(1)

    http_origin, ws_origin = normalize_base_urls(args.url)
    room_name = args.room
    if not room_name:
        try:
            room_name = create_private_room(http_origin)
        except Exception as exc:
            print(f"\n{RED}❌ Failed to create a private room: {exc}{RESET}")
            sys.exit(1)

    try:
        asyncio.run(chat_client(args.name, room_name, http_origin, ws_origin))
    except KeyboardInterrupt:
        pass
