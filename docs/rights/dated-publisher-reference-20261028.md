# Dated original-publisher acquisition with a withheld reference

A verified capture may retain a metric date and unit while withholding its reference value. The explicit `allow_restricted_reference` acquisition mode uses that date as a request target and reacquires every value from the existing seven original-publisher endpoints. It is not evidence of historical publication availability.

The default remains the full nine-value reference crosscheck. Restricted mode rejects missing or duplicate metrics, unavailable states, non-null restricted values, incorrect units, and target dates after the capture. It still compares every available reference value at the existing precision and retains exact publisher-date, unit, response-hash, and operation-completeness checks. It never falls back to reference values when a publisher request fails.

Packets containing omitted comparisons use `original-publisher-dated-reference.v1`, enumerate each comparison as performed or not performed, and force `ready=false` with `data_readiness=attention_required`. The archive also requires the built review to be ready before its probe can be ready. A restricted reference cannot promote a packet even if its supplied readiness flag is incorrect. Original captures and historical packets are preserved.

Validation: 55 focused publisher, archive, private-reference, public-download, and API-kit tests passed in the existing packet container dependencies with candidate source mounted read-only and networking disabled. This is candidate-source validation, not an installed-image or production acceptance receipt.
