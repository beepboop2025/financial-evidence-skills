# n8n Creator review demonstration

This records one continuous Chromium viewport of an isolated, real n8n 2.42.6
instance. The package is installed from npm through Settings → Community Nodes
as `n8n-nodes-financial-evidence@0.1.0`. A new workflow and node are created in
the UI, then money markets, bank risk and market liquidity are executed with
limit 1 and offset 0. The research node requires no API credential.

A prepared AI Agent workflow uses the same installed node as an AI tool and a
real local Qwen3 1.7B model through Ollama. It must actually invoke the tool;
an answer that merely mentions the tool cannot pass. The model digest is
checked against the reviewed official registry manifest. No paid model API,
mock responder, recorded response, node source modification or fake UI is used.

The self-hosted owner uses a reserved example email and random disposable
password. It exists only in the ephemeral runner. It is not an n8n Creator or
Cloud account. Setup and local model prewarming occur before recording. The
research interface and source clocks are shown without entering credentials
on camera. There is no voiceover, which the review instructions make optional.

Run `node --test integrations/n8n-node/scripts/review_demo.test.mjs` to check
the fail-closed proof and private-artifact boundaries. The `n8n uncut review
demo` workflow installs the pinned Linux runtime, browser and Ollama, then
runs the actual recording. It needs no repository secrets or write permission.

Only a passed recording of at most 300 seconds is copied into `review/`.
The original continuous WebM and whole-file MP4 conversion retain the same
duration. There are no cuts, speed changes, overlays or replacement audio.
The receipt records archive/model/video hashes, run identity, real native
execution IDs, preserved research pages and the operator-controlled request
window. These are internal demonstration calls, never customer adoption.

`private/` contains the disposable runtime profile, cookies/database, service
logs and failed recording and is never uploaded. Services stop on success or
failure. A failed run uploads only the sanitized stage/error receipt. Review
the successful original video visually before submitting it to the existing
Creator Portal application; the workflow does not upload to the portal or
claim verification approval.
