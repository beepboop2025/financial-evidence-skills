# Native Linux office acceptance

The `Native office acceptance` workflow starts digest-pinned, disposable official
ONLYOFFICE Docs, Collabora CODE and Nextcloud containers on separate GitHub-hosted
Linux runners. It does not connect to existing user services or product APIs.

The fixture contains all six real export sheets with synthetic funding rows,
unknown institution coverage, zero, negative and withheld values, Unicode, literal
`_x0041_`, and formula-looking source text. Every expected cell is compared after
native conversion. ONLYOFFICE must also emit `onDocumentReady` for both ODS and
XLSX. The supported ONLYOFFICE route is XLSX: a real browser cell edit must also
save through the native callback, and every saved cell is checked. ONLYOFFICE 10
has an upstream ODS-to-XLSX style serializer defect; the exact failed export is
retained as an unsupported route and never reported as a passing ODS export.
Nextcloud must retain uploaded bytes exactly, then serve each document to
Collabora through WOPI and receive the native spreadsheet status in the browser.
Screenshots, converted files, image identities and a JSON receipt are retained.

The job fails on conversion errors, changed cells, missing native editor readiness,
or a changed Nextcloud Office app version. A converter result alone does not pass
the editor or Nextcloud checks. A passing receipt applies to these exact versions
and fixtures, not all customer installations, all editing features or independent
adoption. Host networking and loopback HTTP are for the disposable runner only;
these are not production deployment instructions.

Official implementation references:

- [ONLYOFFICE opening files](https://api.onlyoffice.com/docs/docs-api/get-started/how-it-works/opening-file)
- [ONLYOFFICE conversion requests](https://api.onlyoffice.com/docs/docs-api/additional-api/conversion-api/request)
- [ONLYOFFICE container configuration](https://github.com/ONLYOFFICE/Docker-DocumentServer/blob/master/README.md)
- [Collabora SDK and conversion API](https://sdk.collaboraonline.com/CO-SDK-manual.pdf)
- [Nextcloud Office configuration](https://github.com/nextcloud/richdocuments/blob/main/docs/install.md)
- [Nextcloud container configuration](https://github.com/nextcloud/docker)
