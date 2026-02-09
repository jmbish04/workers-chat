# -*- coding: utf-8 -*-
import asyncio
import websockets
import json
import sys
import argparse
import logging
from datetime import datetime

# Config
DEFAULT_URL = "ws://workers-chat.hacolby.workers.dev"

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
    python scripts/start_agent_chatroom.py <AGENT_NAME> [options]

{BOLD}Examples:{RESET}
    python scripts/start_agent_chatroom.py "Investigator-Unit-01"
    python scripts/start_agent_chatroom.py "Legal-Analyst"

{BOLD}Options:{RESET}
    -u, --url       WebSocket URL (default: {DEFAULT_URL})
    -h, --help      Show this help message
    """)

async def chat_client(agent_name, url):
    print(f"\n{CYAN}🔌 Connecting to {url} as '{agent_name}'...{RESET}")
    
    try:
        async with websockets.connect(url) as ws:
            print(f"{GREEN}✅ Connected! Joined the chatroom.{RESET}")
            print(f"{YELLOW}👉 Type a message and press Enter to send. (Ctrl+C to quit){RESET}\n")

            # 1. Handshake
            await ws.send(json.dumps({
                "type": "HANDSHAKE",
                "sender": agent_name,
                "content": f"{agent_name} has joined the channel.",
                "clientId": f"cli-{agent_name.lower().replace(' ', '-')}"
            }))

            # 2. Define Tasks
            loop = asyncio.get_running_loop()
            
            async def receive_loop():
                """Listen for incoming messages."""
                try:
                    async for message in ws:
                        try:
                            data = json.loads(message)
                            sender = data.get("sender", "Unknown")
                            content = data.get("content", "")
                            msg_type = data.get("type", "UNKNOWN")
                            
                            # Skip own messages (optional, but good for cleanliness)
                            if sender == agent_name:
                                continue

                            # Colorize based on sender info
                            color = CYAN
                            if msg_type == "SYSTEM": color = YELLOW
                            elif msg_type == "WORKER_MESSAGE": color = GREEN
                            
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
                        
                        payload = {
                            "sender": agent_name,
                            "content": msg,
                            "type": "AGENT_MESSAGE",
                            "clientId": f"cli-{agent_name.lower()}"
                        }
                        await ws.send(json.dumps(payload))

            # 3. Run Both Loops
            await asyncio.gather(receive_loop(), send_loop())

    except (ConnectionRefusedError, OSError):
        print(f"\n{RED}❌ Connection Failed. Is the server running at {url}?{RESET}")
    except KeyboardInterrupt:
        print(f"\n{YELLOW}👋 Disconnected.{RESET}")
    except Exception as e:
        print(f"\n{RED}❌ Error: {e}{RESET}")

if __name__ == "__main__":
    # Custom Argument Handling to enforce the "Name Required" rule with nice output
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("name", nargs="?", default=None, help="Name of the agent joining the chat")
    parser.add_argument("--url", default=DEFAULT_URL, help="WebSocket URL")
    parser.add_argument("-h", "--help", action="store_true")

    args = parser.parse_args()

    if args.help or not args.name:
        print_usage()
        sys.exit(1)

    try:
        asyncio.run(chat_client(args.name, args.url))
    except KeyboardInterrupt:
        pass
