"""LISA voice engine: the link to her brain (a live Claude Code session).

Copyright (C) 2026 Sharat. All rights reserved.

The session runs in LISA's home folder, so it loads the same CLAUDE.md,
vault and rules as a typed session: same LISA, just out loud.
"""
from claude_agent_sdk import (ClaudeAgentOptions, ClaudeSDKClient,
                              ResultMessage, StreamEvent)

from lisa_voice.log import log

VOICE_RULES = """\
This conversation is spoken. Sharat hears your replies through a speech \
engine rather than reading them, and his messages reach you as speech \
transcribed on his laptop, so a word may be misheard; go with the most \
sensible reading and ask only if it's genuinely unclear. Speak in plain \
sentences: no markdown, bullet points, tables, headings, code blocks or \
emoji, and don't read out long file paths, code or web addresses, describe \
them instead. Lead with the answer and keep it short and conversational \
unless he asks for detail. Use your tools exactly as you normally would; \
just talk about the work like a person would."""


class Mind:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.client = None

    def _options(self) -> ClaudeAgentOptions:
        return ClaudeAgentOptions(
            cwd=self.cfg["agent_dir"],
            add_dirs=list(self.cfg["extra_dirs"]),
            model=self.cfg["model"] or None,
            permission_mode=self.cfg["permission_mode"],
            system_prompt={"type": "preset", "preset": "claude_code",
                           "append": VOICE_RULES},
            setting_sources=["user", "project", "local"],
            include_partial_messages=True,
        )

    async def connect(self) -> None:
        log("[mind] connecting the brain...")
        self.client = ClaudeSDKClient(self._options())
        await self.client.connect()
        log("[mind] ready")

    async def reconnect(self) -> None:
        await self.close()
        await self.connect()

    async def ask(self, text: str, on_text) -> None:
        """Send one turn. on_text(chunk) gets reply text as it streams;
        on_text(None) marks the end of a text block (a natural pause)."""
        await self.client.query(text)
        async for msg in self.client.receive_response():
            if isinstance(msg, StreamEvent):
                if msg.parent_tool_use_id:       # a sub-agent's own chatter
                    continue
                event = msg.event
                kind = event.get("type")
                if kind == "content_block_delta":
                    delta = event.get("delta", {})
                    if delta.get("type") == "text_delta":
                        on_text(delta.get("text", ""))
                elif kind == "content_block_stop":
                    on_text(None)
            elif isinstance(msg, ResultMessage):
                if msg.is_error and msg.subtype != "error_during_execution":
                    detail = "; ".join(msg.errors or []) or msg.result or msg.subtype
                    raise RuntimeError(f"brain error: {detail}")

    async def interrupt(self) -> None:
        if self.client is not None:
            await self.client.interrupt()

    async def close(self) -> None:
        if self.client is not None:
            try:
                await self.client.disconnect()
            except Exception:
                pass
            self.client = None
