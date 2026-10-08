# Financial Evidence 0.1.7 release preparation

This release packages the durable research runtime merged in PR #64. Its public
research MCP keeps the existing three tools and eight fixed topics; the private
runtime adds six separate tools only when an owner starts its stdio server.

Release acceptance uses the existing owner-signed tag and commit policy, exact
main identity, coordinated public Worker version, OCI/Registry publication and
attested GitHub artifacts. Historical 0.1.6 contracts and release receipts are
preserved. The published-consumer verifier now accepts an explicit frozen
contract so old Homebrew/container checks cannot silently test against a newer
contract.

The runtime has no broker credentials or order submission interface. Deploy it
with a dedicated service account, private persistent state, bounded workflow
cadences and retained backup/restore proof. Internal recurrence checks remain
internal activity. Independent adoption requires independent user evidence.

Published discovery pins remain at the last verified release until artifact
readback is complete. The repository's existing package lane publishes GitHub
wheel/sdist assets and OCI images; a PyPI project is not implied by publication.
