# Publisher brand assets

`icon.svg` is copied from the repository's existing Financial Evidence Inspector
artwork at `docs/integrations/fdc3/evidence-inspector/icon.svg`. The PNGs are direct
Chrome renders of that same SVG at 32, 64 and 128 pixels.
`microsoft-store-logo-300.png` renders the unchanged SVG at 300×300 pixels for
the Microsoft Marketplace store listing; its source mark and colors are identical. The 220×140 card banner
uses the same mark, colors and plain product copy. No third-party logo is used.

The banner is listing artwork, not a screenshot and not evidence of a native
integration. Capture an actual native add-on screenshot separately. Google asks
for 32/128-pixel icons and a 220×140 card banner; its current accepted screenshot
sizes are 1280×800, 640×400 or 2560×1600.
[Google's graphic requirements](https://developers.google.com/workspace/marketplace/create-listing).

Microsoft asset requirements depend on the manifest and publishing surface.
Use the correct store icon sizes requested by the active Partner Center form;
do not substitute a unified Microsoft 365 manifest's icon set for an add-in-only
manifest without checking its requirements.


`native-excel-windows-20261028.png` is an unaltered 2932×1404 screenshot from the
28 October 2026 Windows Excel operator test. It shows public research in a blank
validation workbook, after two insertions of the first capture and a later
manual refresh. Its SHA-256 is
`76af0b5a385a32ff2efbe1901bf0da815292461665a5f50c86d9dde4350332f9`.
The [native receipt](../../excel/native-acceptance-windows-20261028.json) states
its scope. This is real host evidence, not an illustration or public Marketplace
installation. Check the current submission form's accepted dimensions before use.
