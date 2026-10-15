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
    review=sub.add_parser("review")
    review.add_argument("--mode",choices=["test","shadow","paper","unknown"],default="test")
    review.add_argument("--capture-dir",help="Explicit local capture of permitted returned evidence; no upload")
    args=parser.parse_args(argv)
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
