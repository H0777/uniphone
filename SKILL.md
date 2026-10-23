---
name: uniphone
description: "Control the user's phone (Android via ADB, or iPhone via macOS Mirroring): open apps, tap, type, swipe, read the screen - with any agent."
---

# uniphone

Agent-agnostic phone control. Eyes: a real UI tree on Android (uiautomator)
or OCR on iOS (the mirroring window is a video stream). Hands: adb input /
HID CGEvents. For task-specific edits use agent-workspace/agent_helpers.py.
For setup problems read install.md.

## When Not to Use

If the task is doable on the computer or the web - a website, an API, an app
with a web equivalent - do it there. Use uniphone only when the task
genuinely needs the phone: mobile-only apps, things tied to the user's phone
number or 2FA, testing how something looks on the phone.

## Usage

```bash
uniphone <<'PY'
print(screen_info())
PY
```

- Helpers are pre-imported. Coordinates are driver units (device px on
  Android, screen points on iOS) - screen_info() shows bounds + image size.
- Driver: UNIPHONE_DRIVER=android|ios-mirror (auto-detected by default).
  UNIPHONE_SERIAL picks a specific adb device.

## Screen Workflow

- Prefer ui_tree() over eyeballing screenshots: every visible string comes
  back with a tap-ready center - [{text, x, y, w, h, clickable?}]. Filter in
  Python before printing.
- Tap by label: tap_text("Sign in"). On failure it raises with what IS
  visible - read the exception before retrying.
- Icons without labels: screenshot(), view the image, compute the point
  (image px scaled into the bounds from screen_info()), then tap(x, y).
- **Verify after every action**: wait_stable() then ui_tree()/screenshot().
  The capture is the ground truth.
- Navigation: home(), back(), open_app("Notes"), swipe("up"), scroll(),
  type_text("..."), press("enter"), long_press(x, y).
- Long lists: scroll_collect(extract, key=...) walks to the true end,
  de-duping; scroll_until(done) stops on a predicate. End-of-list is decided
  by whether the screen actually moved, never by your parser.
- Typing is ASCII by default. Arabic/emoji on Android work via ADBKeyboard
  (install.md); iOS typing is US-keyboard Latin only.

## Consent

This is the user's real phone. Stop and ask before anything outward-facing or
hard to reverse: sending a message, posting, purchasing, deleting, changing
settings. Navigating and reading for the user's own task is fine; don't
linger in personal content (Messages, Photos, Mail) beyond what the task needs.

## Connection is the user's job

The harness never connects the phone. Allowing the USB-debugging prompt,
pairing iPhone Mirroring, locking the iPhone when it says "iPhone in Use" -
physical, user-only actions. When connection_state() isn't 'ready': STOP,
relay the message, ask the user. Never tap Connect/Continue, never
loop-poll; retry once after they confirm.

## Gotchas

- Android: `uiautomator dump` occasionally fails on a busy screen - the
  driver retries once; if it keeps failing, wait_stable() first.
- Android: 'unauthorized' means the RSA prompt is on the phone - the user
  must tap Allow.
- iOS: unfocused input is swallowed silently - the mirroring window must be
  frontmost (helpers activate it, but re-activate if a click steals focus).
- iOS: the window moves - never cache coordinates across calls.
- iOS: unlocking the physical phone pauses mirroring ("iPhone in Use").
- iOS: Home-Screen labels are not tap targets - the icon is ~35 points above
  the label; use tap_icon("Weather") from agent_helpers.
