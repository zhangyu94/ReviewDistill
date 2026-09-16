# ReviewDistill documentation site

Docusaurus site for user-facing guides. Source pages live in [`docs/`](./docs/). The sidebar is **Guide** (new-user path to `reviewdistill ui`) then **Reference** (80% of clicks). Prose is second person: command or screenshot first, then one sentence of why. Do not keep old documentation URLs working; update in-repo links instead.

```bash
pnpm --dir website install
pnpm --dir website start
```

Production build: `pnpm --dir website build`. Push to `main` deploys `website/build` to GitHub Pages.

Rebuild screenshots and CLI GIFs:

```bash
pnpm --dir website capture
```

That script sets a fake `HOME`. It must not touch the real `~/.reviewdistill`. Details: [`captures/README.md`](./captures/README.md). `website build` does not run capture. Playwright and VHS are optional for building and deploying the site.

Media in Markdown/MDX must go through `useBaseUrl('/img/...')` (or `/video/...`). A `pathname:///` URL skips `baseUrl` (`/ReviewDistill/`) and 404s on GitHub Pages.

Do not screenshot Settings with an API key.

Contributor specs stay in [`docs/spec/`](../docs/spec/) (roadmap, schema, comment identity), not on this site.
