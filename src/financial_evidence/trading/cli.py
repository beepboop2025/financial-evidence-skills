"""Visible, editable product configurations and a bounded first trading-input review."""
import argparse
import asyncio
import json
import os
from pathlib import Path
from .client import ProductClient, product_catalog
from .journal import save_receipt


def main(argv=None):
    parser=argparse.ArgumentParser(description="Configure and inspect financial-agent data inputs")
    parser.add_argument("--platform-url",default=os.environ.get("SEICHE_AGENT_PLATFORM_URL"))
    sub=parser.add_subparsers(dest="command",required=True)
    sub.add_parser("catalog")
    sub.add_parser("mcp-config")
    doctor=sub.add_parser("doctor",help="Check anonymous MCP connections and source-monitor status; no order authority")
    from .readiness import PROBES
    doctor.add_argument("--product",action="append",choices=list(PROBES),help="Repeat to select products; defaults to all four research connections")
    doctor.add_argument("--timeout",type=float,default=30,help="Per-connection deadline in seconds (maximum 120)")
    latency=sub.add_parser("latency",help="Bounded anonymous synthetic MCP latency sample; no SLA claim")
    latency.add_argument("--product",action="append",choices=list(PROBES))
    latency.add_argument("--samples",type=int,default=3)
    latency.add_argument("--timeout",type=float,default=30)
    context=sub.add_parser("context",help="Read compact source-status metadata; not a market price feed")
    context.add_argument("--events",action="store_true",help="Read bounded SSE events; reconnect returns latest state")
    context.add_argument("--limit",type=int,default=1)
    context.add_argument("--timeout",type=float,default=30)
    sub.add_parser("source-access",help="Inspect source-specific permissions and missing commercial approvals")
    sub.add_parser("feed-pilot",help="Run synthetic feed recovery and permission fixtures; no external feed")
    review=sub.add_parser("review")
    review.add_argument("--mode",choices=["test","shadow","paper","unknown"],default="test")
    review.add_argument("--capture-dir",help="Explicit local capture of permitted returned evidence; no upload")
    args=parser.parse_args(argv)
    if args.command in {"source-access", "feed-pilot"}:
        try:
            if args.command == "source-access":
                from .source_contract import qualify_sources
                result=qualify_sources()
            else:
                from .feed_pilot import run_replay_pilot
                result=run_replay_pilot()
        except (ValueError, OSError) as exc:
            print(json.dumps({"status":"unavailable","reason":type(exc).__name__,
                              "execution_authority":"none"}))
            return 2
        print(json.dumps(result,indent=2,allow_nan=False))
        return 2 if args.command == "feed-pilot" and result.get("status") != "passed" else 0
    if args.command == "latency":
        from .latency import measure_latency
        try:
            result=asyncio.run(measure_latency(platform_url=args.platform_url,products=args.product,
                                              samples=args.samples,timeout=args.timeout))
        except ValueError as exc:
            parser.error(str(exc))
        print(json.dumps(result,indent=2,allow_nan=False))
        return 0 if result["status"] == "passed" else 2
    if args.command == "context":
        from .context import ContextClient
        if not 1 <= args.limit <= 20:
            parser.error("limit must be between 1 and 20")
        async def read_context():
            async with ContextClient(platform_url=args.platform_url,timeout=args.timeout) as reader:
                if not args.events:
                    return await reader.snapshot()
                events=[]
                states=0
                stream=reader.events()
                try:
                    async for event in stream:
                        if event["event"] == "keepalive":
                            continue
                        events.append(event)
                        states += 1
                        if states >= args.limit:
                            break
                finally:
                    await stream.aclose()
                return {"schema":"financial-evidence.context-events.v1", "events":events,
                        "status":"passed" if states == args.limit else "partial",
                        "execution_authority":"none", "replay_complete":False}
        try:
            result=asyncio.run(asyncio.wait_for(read_context(),timeout=args.timeout))
        except Exception as exc:
            print(json.dumps({"status":"unavailable","reason":type(exc).__name__,
                              "execution_authority":"none"}))
            return 2
        print(json.dumps(result,indent=2,allow_nan=False))
        return 2 if result.get("status") == "partial" else 0
    if args.command=="doctor":
        from .readiness import check_readiness, exit_code
        try:
            result=asyncio.run(check_readiness(platform_url=args.platform_url,products=args.product,timeout=args.timeout))
        except ValueError as exc:
            parser.error(str(exc))
        print(json.dumps(result,indent=2,allow_nan=False))
        return exit_code(result)
    client=ProductClient(platform_url=args.platform_url,mode=getattr(args,"mode","unknown"),
                         credential=os.environ.get("SEICHE_NETWORK_TOKEN"))
    if args.command=="catalog":
        print(json.dumps(product_catalog(client.platform_url),indent=2));return 0
    if args.command=="mcp-config":
        if args.platform_url or os.environ.get("SEICHE_NETWORK_TOKEN"):
            servers={row["id"]:{"command":"financial-evidence-product-mcp","args":["--product",row["id"],"--platform-url",client.platform_url]} for row in product_catalog()}
        else:
            servers={row["id"]:{"type":"http","url":client.endpoints[row["id"]]} for row in product_catalog()}
        print(json.dumps({"mcpServers":servers},indent=2));return 0
    result=asyncio.run(client.funding_china_review())
    if args.capture_dir:
        for item in result["inputs"]:
            if "payload" in item:
                item["local_receipt"]=save_receipt(Path(args.capture_dir),item)
    print(json.dumps(result,indent=2,allow_nan=False))
    return 1 if any(i.get("status")=="unavailable" for i in result["inputs"]) else 0


if __name__=="__main__":
    raise SystemExit(main())
