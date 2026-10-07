import argparse

from ai.agent import DEFAULT_SERVER_URL, MinecraftAI
from bridge.ai_bridge_server import run_bridge


def print_plan(ai):
    print("\n" + "="*60 + "\nOBJECTIVE PLAN\n" + "="*60)
    for i, o in enumerate(ai.objectives, 1):
        print(f"{i:02d}. {o.text}")
        print(f"    id:       {o.id}")
        print(f"    action:   {o.action}")
        print(f"    depends:  {', '.join(o.prerequisites) or '-'}")
        if o.params: print(f"    params:   {o.params}")


def main():
    p=argparse.ArgumentParser(description="CarrotCraft autonomous Minecraft AI")
    p.add_argument("--goal", default="get full netherite")
    p.add_argument("--server-version", default="1.21.1")
    p.add_argument("--client-version", default="1.8.8")
    p.add_argument("--server-url", default=DEFAULT_SERVER_URL,
                   help="WebSocket address of the Eaglercraft server the client joins")
    p.add_argument("--bridge-host", default="127.0.0.1")
    p.add_argument("--bridge-port", type=int, default=8765)
    p.add_argument("--tick", type=float, default=0.4,
                   help="Seconds between AI action batches")
    p.add_argument("--serve", action="store_true",
                   help="Run the headless bridge and control the client")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--research-objectives", action="store_true")
    p.add_argument("--objective-limit", type=int, default=None)
    p.add_argument("--video-limit", type=int, default=3)
    p.add_argument("--study-videos", action="store_true")
    p.add_argument("--research", action="store_true")
    p.add_argument("--diamond-research", action="store_true")
    p.add_argument("--optimize", action="store_true")
    p.add_argument("--combine", action="store_true")
    a=p.parse_args()
    a.video_limit=max(1,a.video_limit)
    a.bridge_port=max(1,min(65535,a.bridge_port))
    a.tick=max(0.05,a.tick)

    ai=MinecraftAI(a.server_version,a.client_version,a.server_url)
    print("="*60)
    print("CARROTCRAFT AUTONOMOUS MINECRAFT AI")
    print("="*60)
    print("Goal:",a.goal)
    print("Server version:",a.server_version)
    print("Client version:",a.client_version)
    print("Server address:",ai.server_url)
    ai.prepare(a.goal)
    print_plan(ai)

    if a.research_objectives:
        ai.research_all_objectives(a.video_limit, a.study_videos, a.objective_limit)
    elif a.research or a.diamond_research:
        strategies=ai.research_diamonds(20) if a.diamond_research else ai.extract_strategies_for_videos(ai.research(a.goal))
        print("Videos/strategies found:",len(strategies))
        if a.study_videos: ai.study_videos(ai.knowledge.data.get("videos",[]),a.video_limit)

    if a.optimize: print(ai.optimize(a.goal))
    if a.combine: print(ai.combine_strategies())
    if a.dry_run:
        print("\nDry run complete."); return

    print("\nHEADLESS CLIENT")
    print("Python planner + YouTube research + knowledge base are ready.")
    print("  Python AI -> Objective Planner -> Research -> Strategy ->")
    print(f"  Action Executor -> ws://{a.bridge_host}:{a.bridge_port} -> Headless Eaglercraft -> {ai.server_url}")
    o=ai.select_next_objective()
    if o:
        print("\nNext objective:",o.text)
        print("High-level client action:",ai.objective_action())

    if a.serve:
        run_bridge(ai,a.bridge_host,a.bridge_port,a.tick)
    else:
        print("\nThe client is not being controlled yet. Start the bridge with:")
        print(f'  python main.py --goal "{a.goal}" --serve')


if __name__=="__main__":
    main()