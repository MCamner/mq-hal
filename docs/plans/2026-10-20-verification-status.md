# HAL verification presentation plan

Owner: mq-hal. repo-signal owns doctor output; mq-agent owns checks and receipt validation.

Add an explicit --verification flag to audit and stack-status. Always distinguish structural scores from current changed-file evidence. Default NOT_VERIFIED must not start a provider. Samples remain offline. Use configured repo paths only, never producer-supplied paths. Share one bounded read-only collector; project only validated summary fields and fixed advisory actions. Preserve existing overall/status/feedback fields as existing structural/runtime reports, with separate verification_summary for stack evidence.

Test first: PASS/FAIL/STALE/NOT_VERIFIED, missing/legacy/malformed/timeout responses, no calls without opt-in, and real CLI JSON/text for audit, canonical stack and legacy stack. Run existing smoke checks and release gate. No commit, push or installation in this implementation request.

Rollback: revert additive fields, presentation and flag.
