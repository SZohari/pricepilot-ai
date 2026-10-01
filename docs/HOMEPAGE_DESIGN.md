# Welcome page and retail workspace — September 2026

The entrance is a welcome page: **A better price. A clearer next step.** It
introduces the process without manufacturing a recommendation. The working
example is one fictional German online watch shop, Kiez & Co.

## Design and behavior

Warm charcoal, cream, copper and olive connect the full-width welcome and the
working desk. Self-hosted Newsreader headlines pair with Manrope controls/body.
The welcome story follows **Bring the data → See the decision → Learn what works**.
Three distinct images and an answer panel follow native scrolling: preparing product data, comparing offers, then reviewing orders. Keyboard chapter
buttons, mobile inline answers, a motion toggle and device reduced motion remain.
Hero image travel is bounded to 30 px; there is no scroll interception.

The main homepage action opens the five-step pricing setup; CSV intake remains available. Three cards link to actual demo SKUs
for cost pressure, market comparison and slow stock. Photographer/bicycle stories
no longer occupy the homepage.

The interior prioritizes a next action, with amber cost issues, violet tests,
blue checks and muted hold/investigation states. Costs and evidence remain nearby.
Server recalculation preserves controls and open details; stale responses are
ignored. Tablet/mobile layouts stack the controls, and import tables scroll.

## Images and provenance

The watch images and three new journey scenes were made with the **built-in image generation tool**,
visually inspected and copied into the project. These are fictional editorial
illustrations, not actual clients or photographs of the demo product models.

| Active image | Original | Served WebP family |
| --- | --- | --- |
| Welcome shop | `design/homepage/design-store.png` | `design-store-{640,960,1536}.webp` |
| Packing orders | `design/homepage/watch-packing.png` | `watch-packing-{640,960,1536}.webp` |
| Generic watches | `design/homepage/watch-details.png` | `watch-details-{640,960,1536}.webp` |
| Stage 1: prepare data | `design/homepage/journey-stock.png` | `journey-stock-{640,960,1536}.webp` |
| Stage 2: compare offers | `design/homepage/journey-compare.png` | `journey-compare-{640,960,1536}.webp` |
| Stage 3: review orders | `design/homepage/journey-review.png` | `journey-review-{640,960,1536}.webp` |

Served files are under `src/web/static/assets/images`. Previous portrait-studio
and cycle-workshop assets remain in the repository but are not displayed here.
Exact new prompts: [journey-prompts.json](../design/homepage/journey-prompts.json). Earlier prompts: [retail-prompts.json](../design/homepage/retail-prompts.json) and
[original prompts](../design/homepage/prompts.json).

WebP conversion changes only size/encoding. New packing/detail 1536 px images
are about 70/99 KB. Responsive sizes, intrinsic dimensions, eager hero loading
and lazy below-fold loading bound transfer cost. The Sharp-based
`scripts/optimize_homepage_images.cjs` reproduces all eight retained image families (24 files). The three new 1536 px images are about 148/108/89 KB. The active story photo changes with its chapter; on narrow screens each chapter has its own inline image.

Fonts: official [Manrope](https://github.com/google/fonts/tree/main/ofl/manrope)
and [Newsreader](https://github.com/google/fonts/tree/main/ofl/newsreader).
Six Latin/Latin Extended WOFF2 files and both OFL licenses ship locally. Originals
remain in `design/homepage/fonts`; URLs are recorded in
`scripts/vendor_homepage_webfonts.py`. No runtime CDN or generation service is used.
The public archive includes served assets/licenses, not original artwork.

## Verification boundary

Automated checks cover disclosure, routes, keyboard/scroll behavior, motion
preferences, cleanup, asset integrity, escaped imported text and stale responses.
See [Retail decision system](RETAIL_DECISION_SYSTEM.md) for the accounting and
HTTP workflow checks.

Generated images were visually inspected. The rendered new interface has **not**
had a browser visual pass because the saved local-browser access restriction
remains. Static and interaction tests do not replace that check. This update
is local and packaged; it has not been published to Render.
