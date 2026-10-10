# Financial Evidence plugin privacy

This read-only plugin sends the selected dataset, optional entity filter, limit
and offset to `https://api.seiche.info/openbb/api/v1/query`, operated by LIQUILENS
PRIVATE LIMITED. Enter only public entity identifiers. Do not enter private
customer, account or personal data. The plugin needs no API key or model
permission, adds no separate telemetry and writes no local data.

The query API runs on Hetzner infrastructure. Its network and reverse proxy may
process the calling runtime's IP address, request metadata, timestamps and
response status to deliver and secure the service. This is not necessarily the
end user's network address. See the operator's
[Financial Evidence privacy policy](https://beepboop2025.github.io/financial-evidence-skills/privacy/)
and [Hetzner privacy policy](https://www.hetzner.com/legal/privacy-policy/).

The operator's published policy limits ordinary operational logs to 30 days,
with exceptions for legal requirements or active abuse investigations, and
anonymous aggregate counters to 90 UTC dates. Provider-managed logs follow the
provider's lifecycle and policy. Aggregate counts do not identify active people.
These are the service policy commitments; the plugin does not control the
hosting infrastructure's retention settings.

The backend retrieves fixed public source documents and filters the results
locally. It does not forward the incoming entity, limit, offset or Dify request
headers to source providers. Some fixed public-source requests use
[Railway-hosted services](https://railway.com/legal/privacy); these requests do
not carry the user's entity filter or pagination inputs. Source usage rights
remain with the named publishers.

The plugin returns the full research page to Dify. Dify Cloud processes workflow
inputs, results and logs under the [Dify privacy policy](https://dify.ai/legal/privacy-policy).
For self-hosted Dify, your deployment administrator controls workflow history,
logs and retention. This plugin does not send research to an LLM; any additional
workflow nodes have their own data-handling behavior.

Operator and privacy/deletion contact: LIQUILENS PRIVATE LIMITED,
mrinal@liquilens.in.
