# ReviewDistill logo design

## Intent

The mark is seen at **16×16** in the Studio header and as a favicon. That size is the design, not a shrink of a larger drawing.

## Concept

A **comment bubble with two text lines** — the proofreading notes ReviewDistill starts from. One silhouette. No second icon (document, fold, funnel) competing at 16px.

The folded-corner “skill file” was dropped: at 16px it reads as a clipped chip, and it optically shifts the top text slot so the two lines look staggered even when their coordinates match.

## Form

- **Symbol only.** Wordmark sits beside it in the header.
- Native `viewBox="0 0 16 16"` with `shape-rendering="crispEdges"`. One viewBox unit = one CSS pixel at the header size. No fractional raster.
- The two interior holes are the **same rectangle** twice: `(3,3) 10×2` and `(3,6) 10×2`. Same `x`, same `width`, same `height`.
- 1px stair-step on the four body corners (not a radius that anti-aliases into a stagger).
- Centered three-step tail.
- Ink `#171717` (Studio `--ch-color-foreground`). Holes are transparent.

## Construction

```
 y  pixels (. = cut / pad, # = ink)
 1  ..############..
 2  .##############.
 3  .##..........##.   ← hole x=3 w=10
 4  .##..........##.
 5  .##############.
 6  .##..........##.   ← identical hole
 7  .##..........##.
 8  .##############.
 9  .##############.
10  ..############..
11  .....######.....
12  ......####......
13  .......##.......
```

## Research applied

| Source | Rule used here |
|--------|----------------|
| [Material Design 3 — designing icons](https://m3.material.io/styles/icons/designing-icons) | On-pixel, simplify, 2D, don’t be overly literal |
| [GitHub Octicons](https://primer.style/octicons/design-guidelines/) | 16px is a first-class size; pixel-align outer edges |
| Favicon practice ([Iconic #8](https://iconic.iconbuddy.com/p/iconic-08-logos-are-just-icons-with-a-job)) | Design 16px first; one silhouette |

## Alternatives considered

- **64 viewBox scaled to 16px:** coordinates can match and still *look* unaligned because the fold and tail anti-alias the two slots differently. That was the previous mark.
- **Comment card with dog-ear:** fold makes the top slot look shifted; at 16px it also reads as a SIM.
- **Stacked bubble + page:** two pictograms. Fails the one-silhouette rule.
- **RD monogram / funnel / taxonomy / sparkle:** generic or the wrong metaphor.

## Files

- Canonical logo: `docs/assets/logo.svg`
- This doc: `docs/assets/logo-design.md`
- Studio copies (keep in sync with canonical):
  - `studio/public/logo.svg` — header mark
  - `studio/public/favicon.svg` — browser tab icon
