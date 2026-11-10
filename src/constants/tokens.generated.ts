// Generated from design/system/tokens.json by scripts/build-theme.mjs. Do not edit by hand.
export const Colors = {
  "light": {
    "paper": "#fbf5ec",
    "card": "#ffffff",
    "ink": "#2b1d14",
    "ink2": "#6b5647",
    "line": "#eadfd0",
    "line2": "#f1e8dc",
    "orange": "#ef852e",
    "onOrange": "#2b1d14",
    "orangeText": "#b4531a",
    "orangeSoft": "#fde6d2",
    "orangeBorder": "#f6c9a2",
    "plum": "#4b2e5a",
    "onPlum": "#fbf5ec",
    "plumSoft": "#e7daec",
    "plumLine": "#6e4f7e",
    "beatOn": "#4b2e5a",
    "teal": "#2f7a6e",
    "okBg": "#ddf0ea",
    "okFg": "#1f5f55",
    "waitBg": "#fcefcf",
    "waitFg": "#7a4f00",
    "badBg": "#f8dcd6",
    "badFg": "#8f2f22",
    "planBg": "#eee6f2",
    "planFg": "#4b2e5a",
    "offBg": "#efe7dd",
    "offFg": "#5a4636",
    "scrim": "rgba(43, 29, 20, 0.45)",
    "avatarPlum": "#4b2e5a",
    "avatarOrange": "#ef852e",
    "avatarTeal": "#2f7a6e",
    "avatarPeach": "#f6c9a2",
    "avatarLilac": "#6e4f7e"
  },
  "dark": {
    "paper": "#1a1310",
    "card": "#261c17",
    "ink": "#f5ece2",
    "ink2": "#bca898",
    "line": "#3a2c24",
    "line2": "#31251f",
    "orange": "#f0904a",
    "onOrange": "#1a1310",
    "orangeText": "#f5a66a",
    "orangeSoft": "#3d2618",
    "orangeBorder": "#6a3e22",
    "plum": "#3a2547",
    "onPlum": "#f5ece2",
    "plumSoft": "#dccbe5",
    "plumLine": "#5a3f6a",
    "beatOn": "#c9a6dd",
    "teal": "#5fb8a6",
    "okBg": "#183a33",
    "okFg": "#8fd9c4",
    "waitBg": "#3d3010",
    "waitFg": "#f2cf7a",
    "badBg": "#43201a",
    "badFg": "#f2a396",
    "planBg": "#33243f",
    "planFg": "#d6bfe6",
    "offBg": "#33291f",
    "offFg": "#cdb8a3",
    "scrim": "rgba(0, 0, 0, 0.6)",
    "avatarPlum": "#4b2e5a",
    "avatarOrange": "#ef852e",
    "avatarTeal": "#2f7a6e",
    "avatarPeach": "#f6c9a2",
    "avatarLilac": "#6e4f7e"
  }
} as const;

export const Space = {
  "1": 4,
  "2": 8,
  "3": 12,
  "4": 16,
  "5": 20,
  "6": 24,
  "8": 32,
  "12": 48
} as const;

export const Radii = {
  "sm": 12,
  "field": 14,
  "row": 20,
  "card": 24,
  "sheet": 28,
  "pill": 999
} as const;

export const Duration = {
  "fast": 120,
  "base": 220,
  "slow": 320
} as const;

/** Cubic-bezier control points, ready for reanimated's Easing.bezier(...). */
export const Curves = {
  "outSoft": [
    0.2,
    0.8,
    0.2,
    1
  ],
  "bounce": [
    0.3,
    1.5,
    0.5,
    1
  ]
} as const;
