# curl audit contract

The deterministic inspector accepts an exact argument vector rather than a shell command string. Bash, PowerShell, cmd.exe, and other shells have different quoting and expansion rules; the Skill must not guess an argument boundary when it matters.

The inspector models these stable curl behaviors:

- `--request` changes the method token but does not enable the behavior of `--head` or another specialized mode;
- data options select body behavior, and `--data-urlencode` has distinct value and file-reference forms;
- curl may load a default config unless `--disable` or `-q` is the first argument;
- config files use one option per physical line and require `--url` for a URL;
- credential-bearing options and selected headers cross a separate secret-handling boundary.

It deliberately does not execute curl, resolve DNS, open sockets, read an `@file` or form upload, expand environment variables, inspect more than one referenced config, validate TLS, or predict the server response. It also does not parse a raw shell command. Consequently, `reviewable` means only that the normalized evidence has no detected local contradiction.

If the original command includes an actual bearer token, password, cookie, signed URL, client certificate, or private endpoint, keep the option identity but replace its value before creating the JSON input. Stop at a credential finding; do not ask the inspector to make secret handling safe.
