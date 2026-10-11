# Newsroom reuse kit

Two retained historical editions, published 11 October 2026. No market data is
fetched or refreshed when this package is built. The edition times identify the
research publication; underlying observations and source-release dates differ.

Each edition contains unchanged chart/data assets, source links, an HTML image
embed, a preview and a caption. The online reuse page links the existing edition
assets rather than duplicating their binaries. The ZIP includes those binaries
for convenience, plus the existing source notices and an integrity manifest.

Read the live [reuse terms](https://beepboop2025.github.io/financial-evidence-skills/media/rights.html),
[correction log](https://beepboop2025.github.io/financial-evidence-skills/media/corrections.html) and
[funding source attribution](https://beepboop2025.github.io/financial-evidence-skills/funding/sources.md) before using an asset.
The copies inside this archive are snapshots; website-relative navigation in
archived HTML may not work offline. The manifest carries original public URLs.

Open preview.html for an edition, or copy embed.html into a CMS HTML block. Its
image and verification links use the public Media Desk. Test the CMS output.
For offline or blocked-image use, take the included PNG and retain CAPTION.txt.
An image embed does not dynamically refresh the dates, source notes or caption.
Downloaded and republished copies cannot automatically receive corrections.

The bank brief records that the original issuer PDF hash was not independently
verified; no issuer PDF is included. No broad bank coverage, live funding quote,
data-feed licence, newsroom adoption, endorsement or service level is asserted.

checksums.json covers every other file inside the archive. The public manifest
also identifies the ZIP. A hash proves file identity, not source accuracy or
legal permission. Build locally with python3 -B scripts/build_newsroom_reuse_kit.py.

Contact: mrinal@liquilens.in
