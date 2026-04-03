# Sample Skill: `speak-animal`

The scaffolded plugin includes a generic skill that demonstrates
how skills bridge MCP tools with Claude's natural abilities.

## What it generates

```yaml
---
name: speak-animal
description: Speak as any animal. Use when asked to talk like, speak as,
  say something as, or imitate any animal.
user-invocable: true
argument-hint: "[animal]"
---
```

## How it works

The skill instructs Claude to:

1. Check if a `speak_<animal>` tool exists for the requested species
2. If yes — call the tool and present the result
3. If no — admit it's not an expert, then improvise

This demonstrates a key skill pattern: **graceful degradation**. The
skill doesn't fail when a tool is missing — it falls back to Claude's
own capabilities while being transparent about it.

## Expected output — tool available

```
> speak alligator

🐊 "After while, crocodile!"
```

## Expected output — no tool, improvisation

```
> speak penguin

I'm not an expert on that one, but I'll give it my best shot.

*waddles forward, flippers outstretched*

NOOT NOOT! 🐧
...
```

## Next steps

Replace `speak-animal` with a skill that orchestrates your real
tools. Keep the pattern: check what's available, use it when you
can, degrade gracefully when you can't.
