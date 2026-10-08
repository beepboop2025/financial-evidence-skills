"""One isolated bounded research call. No broker imports, credentials or orders."""

import argparse
import sys

from ..agents import EvidenceAgentClient
from ..core import FIXED_ROUTE_OPENER, fetch_source
from ..service import EvidenceService
from .contracts import MAX_BUNDLE_BYTES, Workflow, decode, encode


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--traffic-class", choices=["unverified", "internal", "synthetic"], default="unverified")
    args = parser.parse_args()
    try:
        workflow = Workflow.parse(decode(sys.stdin.buffer.read(8193), limit=8192))
        value = workflow.value
        def opener(request, **kwargs):
            request.add_header("User-Agent", "Financial-Evidence-Runtime/1.0.0")
            request.add_header("X-Liquilens-Traffic-Class", args.traffic_class)
            return FIXED_ROUTE_OPENER(request, **kwargs)

        def fetcher(source, **kwargs):
            return fetch_source(source, opener=opener, **kwargs)

        service = EvidenceService(fetcher=fetcher)
        try:
            client = EvidenceAgentClient(service)
            # Workflow validation makes this a fixed method, never dynamic code.
            if value["operation"] == "query":
                result = client.query(**value["parameters"])
            else:
                result = client.review(**value["parameters"])
        finally:
            service.close()
        raw = encode(result)
        if len(raw) > MAX_BUNDLE_BYTES - 16384:
            raise ValueError("result allowance exceeded")
        sys.stdout.buffer.write(raw + b"\n")
    except Exception:
        # Source errors may contain private environment details: emit a fixed code.
        sys.stderr.write("research_worker_failed\n")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
