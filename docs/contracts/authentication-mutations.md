# Authentication and mutation API contract

## Intentional security contract changes

- `SC4S_MANAGER_MANUAL_LOGIN_TOKEN` is a login credential only. It is accepted only in the JSON body of `POST /api/login`; it is no longer accepted in query parameters, bearer headers, custom manual-token headers, or cookies.
- Successful manual login creates a random, process-local, revocable session. The browser receives only the random session identifier in `sc4s_manual_session` with `HttpOnly`, `Secure`, and `SameSite=Strict`. `POST /api/logout` revokes that session.
- Forwarded usernames are audit identities only when `X-SC4S-Manager-Proxy` has authenticated the trusted proxy. Manual sessions are recorded as `admin`; loopback API-token calls as `local-api`.
- `POST /api/env` and `POST /api/config/file` now use the validated apply transaction. Their legacy default is safe staging (`apply: false`). `POST /api/env/secret` returns HTTP 410; secrets must use a typed credential workflow such as destination configuration.
- Public mutations are serialized by a process-wide transaction lock. Clients may send integer `expected_revision`; a stale value returns `code: revision_conflict` without running the mutation. Successful coordinated mutations return and increment `revision`. The revision is process-local and resets at process restart.
- A performed apply is successful only if validation, the narrow control action, and explicit post-check health all succeed. Otherwise the prior snapshot is restored and the response includes `rolled_back: true`, `rollback_validation`, and `rollback_runtime` (reload/restart + post-check after filesystem restore when runtime was mutated). When a control action already ran against the failed config, Manager also reloads/restarts SC4S with the restored files and reports `rollback_runtime` evidence.
- State-writing library and template export/staging POSTs also use `coordinated_mutation()` so they honor `expected_revision` and return an updated `revision`.

These changes do not broaden runtime control: callers still cannot choose a shell command, Docker endpoint, container, compose file, or arbitrary filesystem path.
