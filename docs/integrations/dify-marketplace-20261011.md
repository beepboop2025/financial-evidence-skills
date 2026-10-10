# Dify Marketplace candidate 0.1.1 — 2026-10-11

The Financial Evidence plugin candidate now uses `dify-plugin==0.10.2`, adds
the required public source repository and contact metadata, declares its sole
outbound domain, and documents setup, connection requirements and a native
workflow. All three bounded native Dify Cloud workflow tests passed. It remains
an **unpublished candidate** until Marketplace review and publication complete.

This replaces the unpublished 0.1.0 candidate for future Dify submissions. It
does not change the fixed Seiche endpoint, supported datasets, bounded inputs
or evidence output contract. Existing 0.1.0 download receipts remain historical
evidence and must not be relabeled as the new package.

## Verified locally

Using Python 3.12.12, five unit tests passed, including partial-page preservation,
invalid-input rejection before network access, HTTP/contract failures, the SDK
JSON message and rejection of private or modified archive files. Actual
`PluginRegistration(DifyPluginEnv())` loaded the manifest and provider with SDK
0.10.2.

Official Dify CLI 0.6.11 built the archive. Its Darwin ARM64 executable was
verified against SHA-256
`9f302d7bcad0d9efb6e1b3b620e7f3f309ea26c206c062f5ae569621ae53f654`.
The source verifier checked all ten packaged files byte-for-byte and rejected
any other entry. Current 0.1.1 candidate SHA-256:
`b94f1c080ddd8e8e592acf41c80c3177660044fd71ee8badb239b6fce72e9f6c`.
Rebuild and record a new hash after any packaged-source change.

The [official Marketplace toolkit](https://github.com/langgenius/dify-marketplace-toolkit)
at revision `57a21d1304b1108df3e6b90a15a4f5dd9f0915f9` returned **zero blocking
failures and zero check-execution failures**, with its online OSV check enabled.
It reported no known vulnerabilities for the two directly pinned requirements;
this does not constitute a full transitive-dependency audit. The prepared PR
body was supplied for the sensitive-capability disclosure check.

Five warning categories are retained for review:

- No minimum Dify version is claimed before native compatibility testing.
- The financial-activity scanner matches the README and tool description's
  denials of transaction/trading capability. The tool only performs an HTTPS GET.
- The domain scanner identifies `api.seiche.info` and also warns that the
  `httpx.get(URL, ...)` call uses a variable. `URL` is a fixed module constant,
  not a user input; redirects are disabled and the domain is declared.
- The dependency category contains informational OSV results.
- The capability scanner flags the HTTP request for manual disclosure review.
  The PR body explains the fixed destination and the transmitted entity filter.

These package checks do not install the plugin in Dify, execute a native
workflow or verify Marketplace duplicate versions. The package receipt schema
v2 explicitly marks native execution and publication as `not_checked`; the
separate native receipt below records the actual workflow results.

## Native acceptance and submission

The plugin registered in Dify Cloud's free SANDBOX workspace through remote
debugging. The private connection stayed outside the repository, packages and
public evidence. A draft **User Input → Get Evidence Page → Output** workflow
routed the complete JSON page directly to output. All three tests used limit 1,
offset 0 and a blank entity; each completed three workflow steps with zero
model tokens, one row, one source, no page diagnostics, complete transport and
`next_offset=1`.

| Dataset | Run ID | Elapsed | First observation |
| --- | --- | --- | --- |
| money_markets | 298f3331-6b4d-4dec-ad79-1299965c52fb | 8.810 s | AONIA 4.6%, dated 2026-10-08; source response PARTIAL retained |
| bank_risk | 33d313d5-4e18-4d56-8047-f5540886edd9 | 1.365 s | AU Small Finance Bank GNPA 2.1%, dated 2026-06-30 |
| market_liquidity | 312ea7e4-b4cc-4acf-8601-5e3afdc9062b | 1.472 s | UST stress percentile null/unavailable, dated 2026-10-08 |

The [sanitized native proof](dify-native-proof-20261011.json) records exact
runtime file hashes and output hashes. The registered source is byte-equivalent
to revision `5fcefc542c51cd3fe3b982142e9fe5801c75fd7c`, with initial archive hash
`8929480aa1553bed501d5c8470f29d44c397f5222263e9fc8f2c0c38cdbba625`.
Only `PRIVACY.md` changed before final packaging; executable files, dependencies,
manifest, tool/provider definitions and icon are byte-identical. The final
privacy notice links the published operator policy and verified Hetzner, Dify
and downstream public-source hosting policies. The exact query route is hosted
on Hetzner; incoming entity/pagination inputs and Dify headers are not forwarded
to the fixed public-source endpoints fetched by that service.

Community Edition was not tested. The draft workflow was not published. Native
success verifies bounded tool execution and preservation of the envelope;
`evidence_status=not_evaluated` and `carrier_verification=not_performed` remain
unchanged. It does not establish source validity, freshness, rights, investment
suitability or customer adoption.

Self-hosting was assessed but not started: this Mac has 16 GiB RAM, active
UTM/QEMU services and approximately 9.6 GiB swap used. Docker/Colima is stopped.
The current official Mac instructions require an 8 GiB Docker VM, and the
default stack contains roughly fifteen services. Cloud debugging avoids that
additional local resource demand.

The [current submission route](https://docs.dify.ai/en/develop-plugin/publishing/marketplace-listing/submit-plugin-to-marketplace)
is a pull request to `langgenius/dify-plugins` containing one package at
`beepboop2025/financial_evidence/financial_evidence-0.1.1.difypkg`. Creator Center
manages published plugins; it is not the initial upload route. Prepare the
current upstream PR template, disclose the entity filter sent to Seiche as
Medium risk and attach validation/native evidence. Marketplace searches for
`Financial Evidence` and `financial_evidence` returned fuzzy matches but no
exact plugin/author match. The current upstream README links publication to the
[Plugin Development Guidelines](https://docs.dify.ai/en/develop-plugin/publishing/standards/contributor-covenant-code-of-conduct);
the template retains an unlinked "Plugin Developer Agreement" label. Those
guidelines were reviewed, including native testing, free distribution, privacy,
support, asset rights and the prohibition on financial transactions. No separate
agreement document was identified in the current official documentation.

## Retained evidence

Local evidence root:
`/Users/mrinal/SSDWorkspace/artifacts/dify-marketplace-compliance-20261011/`.

It contains the package, exact-file receipt, unit-test and registration output,
official-validator output and summary, pinned toolkit checkout, and the
upstream PR body. Native output JSON is retained without copying account UI,
private debug configuration or user identifiers into the public proof.
Marketplace acceptance and traction remain unverified.
