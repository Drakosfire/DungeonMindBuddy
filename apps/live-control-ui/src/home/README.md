# Buddy Home

`BuddyHome` uses existing hosted authentication, selected-World state and app
navigation. Sample references reveal only local fictional content and never
create, read or mutate a private World. The two public Home fragment destinations
are explicitly admitted in `App.tsx`; other guest-route restrictions remain.

## Artwork

`mill-at-dusk.webp` is original artwork generated with the built-in image generation
tool for this Home page, then resized to 1440 × 480 and encoded as WebP (quality
88). It is a campaign preview, not a depiction of operator/private campaign data.

Generation prompt:

> Create a wide cinematic painted illustration asset for a tabletop fantasy campaign notebook website. Landscape 3:1 composition. An old timber and stone watermill with a gently turning wooden wheel beside a quiet river, autumn woodland, dusk violet sky and warm amber light in two windows. A small stone stair disappears beneath the mill hinting at a sealed door. Painterly storybook realism, sophisticated restrained detail, warm ochre foliage, muted slate blue shadows, soft atmospheric depth. Inviting mysterious mood, no characters, no text, no lettering, no borders, no parchment frame, no UI. Composition should remain beautiful cropped to a horizontal banner. Original fictional setting.

The parchment texture and compass vocabulary reuse the existing Buddy aesthetic.
The illustrated navigation comparison strip in the design concept is not product
UI. The actual return links live in the Home masthead and footer.

## Browser witness

After building, start the task-owned Vite preview on port 5187 and run
`node src/home/verifyHome.browser.mjs <external-output-directory>` from the
frontend directory. The witness uses installed Chrome (override `CHROME_PATH` if
needed), synthetic signed-out responses and no live account/provider. It saves
responsive screenshots and interaction results. This supplements, rather than
replaces, exact-SHA repository qualification and actual hosted sign-in acceptance.
