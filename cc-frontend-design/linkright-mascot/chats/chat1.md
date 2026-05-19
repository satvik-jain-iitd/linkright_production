# Linkright CLI Mascot

_Started 2026-05-13 10:18 UTC_

---

## User

I want to create a Similar mascot for Linkright who lives beside the Linkright logo in the CLI tool for Linkright - https://github.com/satvik-jain-iitd/linkright_production

Check the repository and screenshots attached. Ensure this mascot has a life, has some persona, some behaviours according to the vision of linkright. 

Surprise me by bringing the best creative ideas possible using your superpowers like the best designer/motion graphics expert. Also make sure you understand that this mascot will primarily live inside the CLI tool right now and will be going to Web App or Chrome Extension in Future.

## Assistant

_[tool: read_file]_

_[tool: view_image]_

_[tool: view_image]_

_[tool: copy_starter_component]_

_[tool: list_files]_

_[tool: update_todos]_

I have what I need. Vision is clear: career navigation OS, builder-confident voice, climbing-the-arrow metaphor in the logo, and there's already a tiny coral pixel creature in the CLI banner reference. I'll evolve that into a fully-realized mascot with persona, behaviours, and CLI animations — then show how it scales to the web/extension future.

Let me set up the project and start building.

_[tool: list_files]_

_[tool: read_file]_

_[tool: copy_files]_

Good, I have everything. Let me bring in the brand assets and build.

_[tool: write_file]_

_[tool: write_file]_

Now the showcase. I'll structure it as a design canvas with several sections — hero, persona, behaviours, sprite sheet, voice, variations, future forms.

_[tool: write_file]_

_[tool: write_file]_

Now let me build the showcase sections. I'll split into a few files to stay clean.

_[tool: write_file]_

_[tool: write_file]_

_[tool: write_file]_

_[tool: write_file]_

Now the index.html shell.

_[tool: write_file]_

_[tool: show_html]_

_[tool: done]_

_[tool: grep]_

_[tool: grep]_

_[tool: str_replace_edit]_

_[tool: str_replace_edit]_

_[tool: done]_

_[tool: save_screenshot]_

Let me peek at how it renders before forking the verifier.

_[tool: show_html]_

_[tool: save_screenshot]_

_[tool: fork_verifier_agent]_

I've built a comprehensive mascot system for LinkRight. Here's what's there:

**Pip** — a 14×10 coral pixel operator who lives beside the LINKRIGHT banner. He blinks idle, reads JDs with a magnifier, hammers bullets when building resumes, wears a purple aura in AI mode, jumps with a gold star on success, sweats on retry, and carries coffee when a job runs long.

The deliverable is a pan/zoom design canvas with six sections:

1. **Hero** — a live CLI window with the pixel-block LINKRIGHT banner (custom gradient sweep), Pip animated beside it, and a three-point manifesto.
2. **Career journey** — Pip wearing a different tool at each lifecycle stage: Discover → Position → Apply → Interview → Negotiate → Perform → Promote (directly mapped to your vision doc's career navigation pipeline).
3. **Character bible** — Persona card (name, what he believes, what he refuses), Anatomy card (pixel measurements, 4-color palette, scale ladder), and a Voice catalog of dialogue lines grouped by moment.
4. **CLI behaviour atlas** — six mini-terminals showing Pip live in real workflow states, plus a full sprite sheet of 23 expressions and tools.
5. **Direction options** — four expressions of the same source sprite: Coral (canonical), Sage (interview mode), Teal (brand/dashboard), and an ASCII fallback for no-color terminals.
6. **Future forms** — Pip in the dashboard (nav, welcome banner, floating companion) and as a Chrome extension popup parsing a JD on a job page.

The mascot voice strictly follows the LinkRight system: lowercase, terse, specific numbers over adjectives, refuses to invent metrics, no emoji as decoration.

If you want to push further: I can animate the journey strip (Pip walking between stops), add a tweaks panel so you can swap his palette/scale live, or design a tiny ASCII narration script for the CLI to actually use.

## User

Verifier agent check completed

## Assistant

Verifier confirms structure is healthy and clean. The mascot system is ready for you to explore — pan/zoom the canvas, focus any artboard fullscreen, and tell me which direction you want to push further.

## User

Can you please improve the shapness and clarity, use Teal colour since that is the primary one, and improve the contrast so that actions being performed by the Mascot are easily understandable. Like currently I am finding it difficult to understand what the mascot is doing in the different examples.  can you please start with a self-evaluation first of each mascot based on sharpness, contrast and clarity of clarity of the activity that the mascot is doing and if it is clear to the human eye on first glance, what is the mascot actually trying to do? Because terminals are generally dark-colored backgrounds, so you should try to choose something light and something that can be easily seen and can easily be distinguished from the background. If you choose something as dark as you know black, then you might not be able to showcase properly what the mascot is doing. So understand the limitations around that use the teal color as the primary color for the for the mascot and come up with a improved improved version of the existing of the existing artboard or existing index.html file that you have created

## Assistant

## Assistant

_[tool: update_todos]_

_[tool: write_file]_

Good critique — you're right. Let me self-evaluate first, then rebuild around teal as the primary, with high-contrast light-colored accessories that pop on dark terminals.

## Self-evaluation of v1 (what's actually unclear)

| State | What you'd actually see at a glance | Clarity (1–5) | Root cause |
|---|---|---|---|
| `idle` | ✓ A small coral blob with 2 eyes | 4/5 | Fine, but coral isn't the brand primary |
| `happy` (squint) | "Pip's eyes look weird" | 2/5 | 1-pixel eye change is invisible at small size; no mouth to confirm "happy" |
| `look_up/left/right` | Indistinguishable from idle | 1/5 | 1-pixel eye shift is below the legibility threshold |
| `with_magnifier` | "There's a small dark blob beside Pip's face" | 1/5 | Magnifier drawn in **dark navy on dark navy** — disappears into background |
| `with_hammer` | "A vague dark shape above Pip" | 1/5 | Hammer is dark gray `#3B475A` on near-black bg — invisible |
| `with_coffee` | "Is that part of Pip?" | 1/5 | Mug drawn dark, no steam, merges with terminal bg |
| `with_page` | "Cream rectangle floating somewhere" | 2/5 | Page is light but tiny, no clear "document" shape |
| `scout` | "Why does one eye look weird?" | 1/5 | Single-pixel pink detail is illegible |
| `with_rupee` | "Random gold pixels" | 2/5 | `₹` glyph at 4-pixel resolution is just noise |
| `sweat` | "Pip's eyes are flat?" | 2/5 | The drop is on the side, the eye change is the only real signal |
| `ai_aura` | ✓ Purple ring around Pip | 4/5 | Works — light color, large enough |
| `with_star` | ✓ Gold star above Pip | 4/5 | Works — gold pops on dark |

**The pattern:** every state I scored ≤ 2 uses **dark colors on dark backgrounds**. Tools and accessories rendered in shades that match the terminal disappear. Eyes also lack a mouth to anchor expression.

## Fixes going into v2

1. **Palette swap**: coral body → **teal `#0FBEAF`** (the brand primary). Teal has much higher luminance on dark navy than coral; reads instantly.
2. **Accessory color law**: every prop uses one bright, distinct color — **silver** (hammer, magnifier), **cream** (page, coffee), **gold** (star), **purple** (AI aura), **coral** (sparks, sweat, retry — coral is now an alert/CTA color, not body). No more dark-on-dark.
3. **Bigger, more iconic silhouettes** for tools. Hammer = clear T-shape. Magnifier = clear ring + handle. Coffee = clear mug + visible steam.
4. **Mouths added** to expressive states (happy/flat/surprised) so emotion reads without relying on 1-pixel eye shifts.
5. **Sprite display sizes bumped** from pixel=5 to pixel=7+ everywhere — detail now reads on first glance.
6. **Motion lines & sparks** on action states (hammer strikes, jump-up, sweat) so "what's happening" reads at first glance.

Let me build it.

_[tool: str_replace_edit]_

Right — `with_book` got dropped in the rewrite. Let me add it plus push through the rest of the v2 updates: bigger display sizes everywhere, palette refs swapped to teal, and a new critique artboard up top.

_[tool: write_file]_

_[tool: str_replace_edit]_

_[tool: str_replace_edit]_

Now bump display sizes everywhere and add the critique section.

_[tool: str_replace_edit]_

_[tool: str_replace_edit]_

_[tool: str_replace_edit]_

_[tool: str_replace_edit]_

_[tool: str_replace_edit]_

_[tool: str_replace_edit]_

_[tool: grep]_

_[tool: str_replace_edit]_

_[tool: read_file]_

_[tool: str_replace_edit]_

_[tool: str_replace_edit]_

_[tool: str_replace_edit]_

_[tool: str_replace_edit]_

_[tool: done]_

_[tool: fork_verifier_agent]_

v2 is up. The changes you asked for:

- **Body is now teal** (brand primary), eyes pure black — much higher contrast on dark terminal bg than the old coral.
- **Every accessory rewritten** in light colors: silver hammer with coral sparks, cream coffee mug with white steam, silver-ring magnifier, gold star, purple AI aura. No more dark-on-dark.
- **Mouths added** to happy / flat / surprised / confused so emotion reads at any size.
- **`with_book` added** so the Interview stop renders cleanly.
- **Display sizes bumped** everywhere (pixel=5 → 6/7 in cards, journey strip, sprite sheet) so detail is visible at first glance.
- **New "00 · Designer's critique" artboard** at the top of the canvas — shows each v1 sprite next to its v2 fix on dark bg with the diagnosis and the rule that was broken.

Variants reshuffled to match: V1 Teal (canonical), V2 Sage (interview), V3 Coral (alert-only), V4 ASCII fallback.

## User

Verifier agent check completed

## Assistant

Verified. Everything renders clean — teal body dominant, all accessories in their prescribed light colors, no missing sprites, Interview stop fixed. Ready for your review.

## User

I want to ask google gemini on my own end to give me a different direction for this mascot creation. Can you please only give me a structured prompt that i can paste to google gemini to give it the complete context

## Assistant

Here's a self-contained prompt you can paste into Gemini. It carries enough context that Gemini can either critique my direction or propose something genuinely different.

````markdown
# Brief: design a mascot for LinkRight

I need you to propose a **distinct creative direction** for a mascot — different from the one I already have. Push back on my current approach where you think it's wrong, and bring your own point of view.

---

## 1. The product

**LinkRight** is an AI-powered career navigation OS for job seekers (starting with PMs and engineers in India). It's local-first, $0 to run.

The full lifecycle it covers: **Discover → Position → Apply → Interview → Negotiate → Perform → Promote.**

Today the primary surface is a **CLI tool** (`linkright`). The CLI boots with a giant ASCII banner spelling LINKRIGHT in a teal→purple→pink horizontal gradient, with the tagline *"Your local-first career OS · $0 to run · v0.9.2"*.

Phase 2 is a **web dashboard**. Phase 3 is a **Chrome extension** that parses job descriptions in-page.

The logo is a hand-drawn figure climbing a rising arrow toward a gold star, past a gear. The metaphor: human striving, engineered output.

---

## 2. Brand voice & visual system

- **Voice:** builder-confident, evidence-led, quietly witty, anti-AI-slop. Short sentences. Specific numbers. Lowercase. Never uses words like "leveraged," "empowered," "unleash."
- **Type:** Inter only. Weights 400/500/600/700/800.
- **Primary palette:**
  - Teal `#0FBEAF` — trust, brand, primary
  - Coral `#FF5733` — energy, CTAs, alerts (use sparingly)
  - Purple `#8B5CF6` — AI / intelligence surfaces
  - Gold `#E5B80B` — achievement, success
  - Pink `#F05A79` — human / relational (mentorship)
  - Sage `#6B8346` — interview / "quiet room" mode
  - Cream `#FDF6F0` — warm neutral backgrounds
- **Terminal background** the mascot must live on: dark navy `#0E1620`.
- **Aesthetic:** flat, no gradients in the body, hand-drawn line-art for illustration. No emoji except 🇮🇳 in the "Made in India" footer. No AI-slop visual tropes.

---

## 3. Where the mascot lives

- **Primary (today):** Beside the LINKRIGHT banner in the terminal. Must render in monospace cells — pixel art, ASCII, or unicode block characters. Must work at very small sizes (16–48 px effective height).
- **Phase 2:** A web dashboard companion — sitting in the nav, a welcome panel, a floating helper bubble.
- **Phase 3:** A Chrome extension popup that parses JDs on LinkedIn / Greenhouse / Ashby pages.

The mascot must have **states tied to product moments** — at minimum: idle, reading a JD, building a resume, AI-generating, success, retry/error, long-running task, sleep.

It also needs **a voice** — short dialogue lines it says in different states. The voice should match LinkRight's brand voice above.

---

## 4. What I already have (and want you to depart from)

I currently have a mascot called **"Pip"** — a **14×10 teal pixel blob** with two black eyes, designed in flat pixel art. He picks up tools per state (silver hammer for building, silver magnifier for JD reading, cream coffee mug for long tasks, purple aura for AI work, gold star for success).

**Strengths of my current direction:**
- Reads at any size from 16 px to 256 px
- Brand-aligned colors (teal body, light-on-dark accessories)
- Cheap to render — pure SVG rects
- Clear state mapping

**Possible weaknesses (be honest):**
- Pixel-blob feel may be too cute / game-y for a serious career product
- The mascot does not visually evoke the **logo's climbing-the-arrow metaphor**
- Doesn't feel uniquely Indian / culturally rooted
- Could feel generic — "just another pixel buddy"

---

## 5. What I want from you

Propose **one distinct creative direction** that is materially different from a pixel blob. Bring a point of view. Some axes to consider (you don't have to use all):

- **Form:** Could the mascot be ASCII-native (built from real terminal characters)? A line-art figure that echoes the climbing-figure in the logo? An abstract glyph/sigil rather than a creature? A typographic mascot? A geometric primitive that animates?
- **Metaphor:** What does the mascot embody? A climber? A small operator? A guide / sherpa? A tool (e.g. a compass, anvil, chisel)? An evolving organism that levels up with the user's career?
- **Personality:** Wise mentor? Apprentice? Quiet co-worker? Field engineer? Strategist?
- **Cultural angle:** Could it draw on Indian visual heritage in a sophisticated way (without being kitschy)?
- **Behavioural depth:** How does it change with the user's career stage — from job-seeker mode to in-role performance mode to promotion-pursuit mode?

---

## 6. Output format I want from you

1. **Direction name + one-line pitch.**
2. **Why this direction** — what it expresses about LinkRight that a pixel blob doesn't.
3. **Visual description** — describe the mascot's form, palette, and silhouette specifically enough that a designer could draw it. If pixel art, give grid dimensions. If line art, describe stroke weight and style.
4. **Sketch how it scales** — CLI (16–48 px), dashboard (~64–128 px), extension favicon (32 px).
5. **Six behavioural states** with: visual description + one-line dialogue (in LinkRight's voice).
6. **One honest critique of my current "Pip" direction** based on what you've read.

Be specific and confident. I want a fresh point of view, not consensus.
````

Paste that and you'll get a directionally different proposal with enough constraints that it'll be implementable. Tell me if you want me to fold whatever Gemini comes back with into a new canvas section side-by-side with the current Pip direction so you can compare them.

## User

Save this design as a PDF: index.html

## Assistant

_[tool: write_file]_

_[tool: write_file]_

## User

Export this design as an editable PPTX: index.html

## User

Save as standalone HTML: index.html

## User

Save as standalone HTML: index.html

## Assistant

_[tool: grep]_

_[tool: copy_files]_

_[tool: str_replace_edit]_

_[tool: super_inline_html]_

_[tool: str_replace_edit]_

_[tool: super_inline_html]_

_[tool: show_html]_

_[tool: sleep]_

_[tool: get_webview_logs]_

Clean. Delivering the file.

_[tool: present_fs_item_for_download]_

Single self-contained file — works offline, no internet needed.

## User

can we try simple stickman like characters for the mascot ?

## Assistant

_[tool: write_file]_

Love this direction. The logo IS a stickman climbing figure — the mascot should echo that DNA directly. Hand-drawn line-art also matches the design system's voice exactly ("confident single-weight strokes, warm palette, no gradients inside the lines"). Let me design it.

_[tool: write_file]_

Now wire it into the showcase as the new top section, and add the script tag.

_[tool: str_replace_edit]_

_[tool: str_replace_edit]_

_[tool: grep]_

_[tool: str_replace_edit]_

_[tool: done]_

_[tool: fork_verifier_agent]_

Stickman direction is up at the top of the canvas as section 00. Five artboards:

1. **Hero** — the pitch: "What if Pip looked like the logo?" Big stickman in the `climb_reach` pose (mirroring the logo's climbing figure), plus three reasons this direction works.
2. **Terminal scene** — Pip's chunky pixel form sitting beside the LINKRIGHT banner, in the actual CLI context.
3. **Pose grid** — 12 named states: idle, wave, reading JD (with paper), building (at desk with laptop + sparks), AI thinking (purple thought bubble), success (arms up + star), retry (hand on head + sweat), coffee, interview (clipboard), negotiate (rupee), climb_reach (logo callback), running.
4. **Three CLI fidelities** — same character at three rendering levels: SVG line-art (sixel terminals), chunky unicode-block pixel, plain ASCII.
5. **Stickman vs blob** — six workflow moments compared side-by-side so you can judge which direction reads better.

The blob direction is still below as section 01+, untouched. Take a look and tell me which way to commit — or if you want me to push the stickman further (more poses, animation, a different head shape, hand-drawn jitter on the strokes).

## User

Verifier agent check completed

## Assistant

Verifier confirms everything renders cleanly — 12 distinct poses, all three CLI fidelities present, logo callback (climbing arrow + star) intact in the hero. Ready for your review.

## User

can we check a third direction with ascii art also ? I like blob, dont like stickman, but do want to see if ascii can be something better. Blob feels complicated and too difficult to recreate if product expands in future

## Assistant

_[tool: write_file]_

Strong critique — ASCII is the right third direction. It's the most maintainable form possible (a pose is just 4 lines of string), it's terminal-native, and it matches "builder-confident, anti-AI-slop." Let me build it.

_[tool: write_file]_

Wire it in.

_[tool: str_replace_edit]_

_[tool: str_replace_edit]_

_[tool: str_replace_edit]_

_[tool: done]_

_[tool: fork_verifier_agent]_

ASCII direction is up as section 00. Five artboards:

1. **Hero** — "Pip is 11 characters." Big animated ASCII Pip plus a code snippet showing that the entire mascot file is `idle = """┌───┐\n│• •│\n└───┘"""`.
2. **Terminal scene** — ASCII Pip sitting beside the LINKRIGHT banner at proper terminal scale.
3. **18 poses** — every state rendered as ASCII with color accents: gold ★ for success, purple ✦ for AI, silver ⊙ for tools, coral for sweat, cream Z for sleep, etc.
4. **Maintenance comparison** — blob code (24 lines of pixel grid) next to ASCII code (5 lines of string) for the same `coffee` state. Visceral proof of the "easy to recreate" argument.
5. **Three-way comparison** — ASCII / pixel blob / stickman side-by-side for 6 workflow moments so you can judge which reads best.

Stickman is now section 01, blob direction is sections 02–08. Take a look and tell me which one to commit. My honest read: **ASCII is the strongest fit for LinkRight's brand voice** (anti-AI-slop, builder-confident, terse) and by far the most maintainable, but the pixel blob has more visual warmth. The combination — ASCII as the canonical CLI form, blob/stickman as the dashboard form — is also viable.

## User

Verifier agent check completed

## Assistant

All three directions are live in the canvas — ASCII (section 00), Stickman (01), Blob (02–08). Pick a winner whenever you're ready.

