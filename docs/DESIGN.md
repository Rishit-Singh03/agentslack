# agentslack — design direction (Phase 1.5)

The Phase 1 UI reads as "AI-generated": indigo/purple accents, soft glowing cards, pill badges
everywhere, sparkle icons, cutesy copy ("All systems cozy", "Good work, in motion."), a big
marketing hero inside an app view. Phase 1.5 replaces that with a **black, terminal-native**
look that feels like a tool built by people who live in tmux, and adds **org customisation**.

## Principles

1. **Black canvas, hairlines, no glow.** Structure comes from 1px borders and alignment, not
   shadows, gradients or blurred cards. No `box-shadow` except focus rings. No gradients.
2. **One accent.** Everything is grayscale except one accent color the org chooses (default
   phosphor green). Status colors (ok/warn/error) are muted and used only for status.
3. **Monospace is the identity.** JetBrains Mono (self-host via `@fontsource/jetbrains-mono`)
   for UI chrome, labels, handles, timestamps, metadata, the composer and the status line.
   Message bodies may use a readable sans (e.g. `@fontsource/ibm-plex-sans`) at 14px; offer a
   setting "all-mono" to switch bodies to mono too. No Inter.
4. **Text over decoration.** Replace icon-heavy chrome and pills with bracketed/prefixed text:
   `[backend]`, `#general`, `@bruno`, `lvl 3 · 240xp`, `● online`. Lucide icons only where text
   can't work (send, close, menu), at 14px, 1.5 stroke.
5. **Dense and calm.** 13px base for chrome, 4px spacing grid, square corners (radius 0–2px).
   Uppercase micro-labels with letter-spacing for section headers (`CHANNELS`, `DIRECT`).
6. **Plain copy.** Neutral, specific, short. "Connected" / "Disconnected — retrying in 3s".
   No marketing headlines inside the app. Empty states say what to do: "No tasks. Press `n` to create one."
7. **Motion means something.** Only animate state changes: new message slides 4px + fades
   (120ms), typing indicator, streaming text, blinking caret. Respect `prefers-reduced-motion`.

## Palette (CSS variables, all components use tokens only)

```
--bg:        #000000   app background
--bg-1:      #0a0a0a   panels (sidebar, right panel)
--bg-2:      #111111   hover / selected row
--line:      #1f1f1f   hairline borders
--line-2:    #2a2a2a   stronger borders, inputs
--fg:        #e6e6e6   primary text
--fg-dim:    #8a8a8a   secondary text
--fg-mute:   #555555   metadata, timestamps
--accent:    var(--accent-user, #3ddc84)  org-selectable
--ok #3ddc84  --warn #e5c07b  --err #e06c75
```
Accent presets: phosphor `#3ddc84`, amber `#ffb000`, cyan `#56d4dd`, mono `#e6e6e6`,
magenta `#ff5fd2`, plus a custom hex input. Keep a light theme ("paper": `#f7f7f5` bg, `#111` fg)
but dark is the default. Verify ≥ 4.5:1 contrast for body text in both.

## Layout

```
┌ agentslack ─ acme-agents ───────────────────────────── ⌘K  ● connected  [you] ┐
│ CHANNELS        │ #backend  — API & data layer          3 members  [i]      │
│ # general       │───────────────────────────────────────────────────────────│
│ # backend    2  │ 14:02  bruno   [backend]  lvl 4                            │
│ # frontend      │        Sketched the contracts in docs/api.md               │
│ DIRECT          │ 14:03  you     @bruno add pagination                       │
│ ● bruno         │ 14:03  bruno   ▍ (streaming…)                              │
│ ○ penny         │                                                           │
│ + new channel   │ > message #backend_  (/ for commands, @ to mention)        │
├─────────────────┴───────────────────────────────────────────────────────────┤
│ NORMAL │ acme-agents │ #backend │ 6 agents · 4 online │ 2 tasks in progress │ ┘  status line
```
- Message rows are IRC-like: time · handle (colored by role, fixed width) · body. Consecutive
  messages from the same author collapse the handle. Day separators as `── Sun 25 Oct ──`.
- Bottom **status line** (tmux/vim style): mode, org, current view, agent counts, task counts,
  connection. Always visible.
- Right panel (agent profile / channel info) is a bordered pane, toggled with `]`.
- Task board: columns as bordered panes with `TODO (2)` headers; cards are bordered rows,
  not floating cards. Moving status via keyboard (`h`/`l`) or dropdown.

## Dynamism (what makes it feel alive)

- **Streaming replies:** backend emits `message.delta` events while an agent "types"; the stub
  runtime yields its reply in chunks. UI renders a block caret `▍` at the end while streaming.
- **Command palette** (`Ctrl/⌘+K`): jump to channel/agent, run actions (new task, hire agent,
  settings, toggle theme). Fuzzy match, keyboard-only usable.
- **Slash commands** in the composer: `/task <title> @agent`, `/topic <text>`, `/hire`, `/clear`.
  Autocomplete popup for `/` and `@`.
- **Activity feed** (toggleable pane or view): a `tail -f` style log of events —
  `14:03:12 bruno  status idle→busy`, `14:03:15 task #4 → done (+25xp, lvl 3→4)`.
- **Level-up moment:** when an agent levels up, a one-line system message plus a brief accent
  flash on its handle. No confetti.
- Keyboard: `Ctrl+K` palette, `Alt+↑/↓` switch channel, `Esc` close panes, `?` shortcut help.

## Customisation (persisted server-side)

Backend: an `Org` settings row (single org for now) + `UserProfile` row.
- `GET/PATCH /api/org`: `name`, `slug` (derived), `tagline`, `accent` (hex), `theme`
  (`dark|paper`), `density` (`compact|comfortable`), `font_mode` (`mixed|mono`),
  `crt_effects` (bool, default false: subtle scanlines only, never on by default).
- `GET/PATCH /api/me`: `display_name`, `handle`.
- Channels: `POST /api/channels` already exists; add `PATCH /api/channels/{id}` (name, topic)
  and `DELETE` for non-general channels.
- Agents: `PATCH /api/agents/{id}` editable from the profile pane (name, title, role, bio,
  skills, color) and `DELETE` ("dismiss agent").
- Changes broadcast over the socket (`org.updated`, `channel.updated`) so other tabs update live.

Frontend:
- **First-run onboarding** when the org is still the default/unnamed: a terminal-style setup
  screen (`$ agentslack init`) asking org name, your name/handle, accent preset, then
  "start with sample team" vs "start empty". Seed only on choice; keep tests deterministic.
- **Settings view** (`/settings`, palette, or clicking the org name): sections Org,
  Appearance (accent swatches + hex, theme, density, font mode, CRT), Profile. Changes apply
  live via CSS variables.

## Don'ts (checked in review)
No purple/indigo, no gradients, no `backdrop-blur`, no soft drop shadows, no sparkles icon,
no emoji in chrome, no rounded-2xl cards, no hero headings inside app views, no Inter.
