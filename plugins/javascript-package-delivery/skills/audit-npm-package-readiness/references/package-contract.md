# npm package audit contract

`npm pack --dry-run --json` is the authority for the selected package payload. A Git-clean tree is not sufficient because npm include and exclude rules can ship untracked or ignored files. Resolve workspace paths against the package root and require a nonempty payload.

The deterministic checker disables lifecycle scripts and network access. Consequently, it does not prove that `prepack`, `prepare`, `prepublishOnly`, `publish`, or related scripts are safe or successful. Declared release lifecycle scripts leave readiness unverified until they are reviewed and run separately in an explicitly authorized isolated environment.

Before publication, also establish:

- package name, version, scope, access, and dist-tag intent;
- README and license inclusion;
- supported Node.js and package-manager versions;
- clean, reviewed source identity for every shipped file;
- provenance and registry authentication policy;
- a fresh install or import smoke test from the exact locally built artifact.

Never print `.npmrc`, tokens, or credential environment variables. Never turn this audit into `npm publish`.

## TypeScript declaration contract

When `package.json` declares `types` or `typings`, the checker requires that exact declaration entry to appear in the npm dry-run payload. It also inventories `.d.ts`, `.d.mts`, and `.d.cts` files and reports whether `typesVersions` is present. These are packaging gates only.

Before calling declarations compatible, compare their exported type, value, namespace, callable, and constructable shapes with the runtime JavaScript API. Exercise the documented consumer import styles in small local TypeScript fixtures and test every supported compiler-version route. Confirm that declaration dependencies needed by consumers are shipped or declared as runtime dependencies. Avoid `/// <reference path>` links across package boundaries.

The deterministic checker does not run `tsc`, install a compiler, infer runtime API parity, or validate every `exports` and `typesVersions` branch. Report those items as manual or separately executed gates rather than guessing from the presence of a declaration file.
