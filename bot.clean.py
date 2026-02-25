#!/usr/bin/env python3
"""All-in-one Pokemon Showdown bot.

Usage:
  py -3.11 bot.py

Optional env vars:
  SHOWDOWN_USERNAME (required)
  SHOWDOWN_PASSWORD
  SHOWDOWN_TARGET
  SHOWDOWN_FORMAT=gen9ou
  SHOWDOWN_SERVER=sim3.psim.us
  SHOWDOWN_TEAM
"""

from __future__ import annotations

import asyncio
import json
import os
import random
import re
from dataclasses import dataclass
from typing import Any


TYPE_CHART: dict[str, dict[str, float]] = {
    "Normal": {"Rock": 0.5, "Ghost": 0.0, "Steel": 0.5},
    "Fire": {"Fire": 0.5, "Water": 0.5, "Grass": 2.0, "Ice": 2.0, "Bug": 2.0, "Rock": 0.5, "Dragon": 0.5, "Steel": 2.0},
    "Water": {"Fire": 2.0, "Water": 0.5, "Grass": 0.5, "Ground": 2.0, "Rock": 2.0, "Dragon": 0.5},
    "Electric": {"Water": 2.0, "Electric": 0.5, "Grass": 0.5, "Ground": 0.0, "Flying": 2.0, "Dragon": 0.5},
    "Grass": {"Fire": 0.5, "Water": 2.0, "Grass": 0.5, "Poison": 0.5, "Ground": 2.0, "Flying": 0.5, "Bug": 0.5, "Rock": 2.0, "Dragon": 0.5, "Steel": 0.5},
    "Ice": {"Fire": 0.5, "Water": 0.5, "Grass": 2.0, "Ground": 2.0, "Flying": 2.0, "Dragon": 2.0, "Steel": 0.5, "Ice": 0.5},
    "Fighting": {"Normal": 2.0, "Ice": 2.0, "Poison": 0.5, "Flying": 0.5, "Psychic": 0.5, "Bug": 0.5, "Rock": 2.0, "Ghost": 0.0, "Dark": 2.0, "Steel": 2.0, "Fairy": 0.5},
    "Poison": {"Grass": 2.0, "Poison": 0.5, "Ground": 0.5, "Rock": 0.5, "Ghost": 0.5, "Steel": 0.0, "Fairy": 2.0},
    "Ground": {"Fire": 2.0, "Electric": 2.0, "Grass": 0.5, "Poison": 2.0, "Flying": 0.0, "Bug": 0.5, "Rock": 2.0, "Steel": 2.0},
    "Flying": {"Electric": 0.5, "Grass": 2.0, "Fighting": 2.0, "Bug": 2.0, "Rock": 0.5, "Steel": 0.5},
    "Psychic": {"Fighting": 2.0, "Poison": 2.0, "Psychic": 0.5, "Dark": 0.0, "Steel": 0.5},
    "Bug": {"Fire": 0.5, "Grass": 2.0, "Fighting": 0.5, "Poison": 0.5, "Flying": 0.5, "Psychic": 2.0, "Ghost": 0.5, "Dark": 2.0, "Steel": 0.5, "Fairy": 0.5},
    "Rock": {"Fire": 2.0, "Ice": 2.0, "Fighting": 0.5, "Ground": 0.5, "Flying": 2.0, "Bug": 2.0, "Steel": 0.5},
    "Ghost": {"Normal": 0.0, "Psychic": 2.0, "Ghost": 2.0, "Dark": 0.5},
    "Dragon": {"Dragon": 2.0, "Steel": 0.5, "Fairy": 0.0},
    "Dark": {"Fighting": 0.5, "Psychic": 2.0, "Ghost": 2.0, "Dark": 0.5, "Fairy": 0.5},
    "Steel": {"Fire": 0.5, "Water": 0.5, "Electric": 0.5, "Ice": 2.0, "Rock": 2.0, "Steel": 0.5, "Fairy": 2.0},
    "Fairy": {"Fire": 0.5, "Fighting": 2.0, "Poison": 0.5, "Dragon": 2.0, "Dark": 2.0, "Steel": 0.5},
}


def _clean_credential(value: str) -> str:
    value = value.strip()
    while len(value) >= 2 and ((value[0] == "\"" and value[-1] == "\"") or (value[0] == "\'" and value[-1] == "\'")):
        value = value[1:-1].strip()
    return value


def _require_runtime_deps() -> tuple[Any, Any]:
    try:
        import aiohttp  # type: ignore
        import websockets  # type: ignore
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Missing dependency: {}. Install with: py -3.11 -m pip install -r requirements.txt".format(exc.name)
        ) from exc
    return aiohttp, websockets


@dataclass
class KnownMon:
    species: str = ""
    hp_fraction: float = 1.0
    status: str = ""


class BattleState:
    def __init__(self) -> None:
        self.roomid: str | None = None
        self.my_team: dict[str, KnownMon] = {}
        self.last_request: dict[str, Any] | None = None

    def update_from_request(self, req: dict[str, Any]) -> None:
        self.last_request = req
        side = req.get("side", {})
        for mon in side.get("pokemon", []):
            ident = mon.get("ident", "")
            details = mon.get("details", "")
            species = details.split(",")[0].strip()
            hp = mon.get("condition", "100/100")
            hp_fraction, status = parse_condition(hp)
            self.my_team[ident] = KnownMon(species=species, hp_fraction=hp_fraction, status=status)


def parse_condition(condition: str) -> tuple[float, str]:
    if condition in {"0 fnt", "0", "fnt"}:
        return 0.0, "fnt"
    if "/" in condition:
        hp_part, *status_parts = condition.split()
        cur, mx = hp_part.split("/")
        try:
            frac = float(cur) / max(float(mx), 1.0)
        except ValueError:
            frac = 1.0
        return frac, status_parts[0] if status_parts else ""
    return 1.0, ""


def type_multiplier(move_type: str, target_types: tuple[str, ...]) -> float:
    if not move_type or not target_types:
        return 1.0
    chart = TYPE_CHART.get(move_type, {})
    mult = 1.0
    for t in target_types:
        mult *= chart.get(t, 1.0)
    return mult


def move_power(move: dict[str, Any]) -> float:
    base = float(move.get("basePower", 0) or 0)
    if move.get("category") == "Status":
        return 0.0
    accuracy = move.get("accuracy", 100)
    if isinstance(accuracy, bool):
        accuracy = 100
    return base * (float(accuracy) / 100.0)


def choose_best_switch(team: list[dict[str, Any]], active_idx: int) -> int:
    candidates: list[tuple[int, float]] = []
    for idx, mon in enumerate(team, start=1):
        if idx - 1 == active_idx:
            continue
        hp, _ = parse_condition(mon.get("condition", "0 fnt"))
        if hp <= 0:
            continue
        stats = mon.get("stats", {})
        bulk = float(stats.get("hp", 70)) + float(stats.get("def", 70)) + float(stats.get("spd", 70))
        speed = float(stats.get("spe", 70)) * 0.3
        candidates.append((idx, hp * (bulk + speed)))
    if not candidates:
        return 1
    candidates.sort(key=lambda x: x[1], reverse=True)
    return candidates[0][0]


def choose_action(req: dict[str, Any]) -> str:
    active = (req.get("active") or [{}])[0]
    side = req.get("side") or {}
    my_pokemon = side.get("pokemon", [])

    active_idx = next((i for i, mon in enumerate(my_pokemon) if mon.get("active")), 0)
    active_mon = my_pokemon[active_idx] if my_pokemon else {}
    active_types = tuple(active_mon.get("types", []))

    if req.get("forceSwitch"):
        return f"/choose switch {choose_best_switch(my_pokemon, active_idx)}"

    moves = active.get("moves", [])
    opp_types: tuple[str, ...] = ()

    best_score = -1.0
    best_choice = None

    for i, mv in enumerate(moves, start=1):
        if mv.get("disabled") or mv.get("pp", 1) <= 0:
            continue

        name = mv.get("move", "")
        mtype = mv.get("type", "")
        raw = move_power(mv)
        stab = 1.5 if mtype in active_types else 1.0
        eff = type_multiplier(mtype, opp_types)
        score = raw * stab * eff

        if mv.get("priority", 0) > 0:
            score *= 1.1
        if mv.get("category") == "Status":
            if re.search(r"(swords dance|nasty plot|calm mind|dragon dance|quiver dance)", name, re.I):
                score = max(score, 55.0)
            elif re.search(r"(recover|roost|slack off|soft-boiled|moonlight|wish)", name, re.I):
                score = max(score, 35.0)
            else:
                score = max(score, 12.0)

        if score > best_score:
            best_score = score
            best_choice = i

    if best_choice is None:
        return f"/choose switch {choose_best_switch(my_pokemon, active_idx)}"

    suffixes: list[str] = []
    if active.get("canTerastallize") and random.random() < 0.2:
        suffixes.append("terastallize")
    if active.get("canMegaEvo"):
        suffixes.append("mega")
    if active.get("canZMove") and random.random() < 0.4:
        suffixes.append("zmove")

    if suffixes:
        return f"/choose move {best_choice} {' '.join(suffixes)}"
    return f"/choose move {best_choice}"


class ShowdownBot:
    def __init__(
        self,
        *args: Any,
        account_configuration: Any | None = None,
        server_configuration: Any | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize bot.

        Legacy args/kwargs from older poke_env-style launchers are accepted and
        ignored so stale runners do not crash with unexpected keyword errors.
        """
        self.username = _clean_credential(os.getenv("SHOWDOWN_USERNAME", ""))
        self.password = _clean_credential(os.getenv("SHOWDOWN_PASSWORD", ""))
        self.target = os.getenv("SHOWDOWN_TARGET", "")
        self.battle_format = os.getenv("SHOWDOWN_FORMAT", "gen9ou")
        self.server = os.getenv("SHOWDOWN_SERVER", "sim3.psim.us")
        self.team = os.getenv("SHOWDOWN_TEAM", "")
        self.state = BattleState()
        self.ws: Any | None = None

        # Legacy compatibility placeholders; intentionally unused by this bot.
        self._legacy_account_configuration = account_configuration
        self._legacy_server_configuration = server_configuration
        self._legacy_extra_args = args
        self._legacy_extra_kwargs = kwargs

    async def send(self, msg: str) -> None:
        if not self.ws:
            raise RuntimeError("Websocket not connected")
        await self.ws.send(msg)

    async def login(self, challstr: str) -> None:
        if not self.username:
            raise RuntimeError("SHOWDOWN_USERNAME is required")

        aiohttp, _ = _require_runtime_deps()
        async with aiohttp.ClientSession() as session:
            if self.password:
                payload = {
                    "act": "login",
                    "name": self.username,
                    "pass": self.password,
                    "challstr": challstr,
                }
                async with session.post("https://play.pokemonshowdown.com/action.php", data=payload) as resp:
                    text = await resp.text()
                try:
                    assertion = json.loads(text[1:])["assertion"]
                except Exception as exc:
                    raise RuntimeError(
                        "Login failed while parsing assertion response. "
                        "Check SHOWDOWN_USERNAME/SHOWDOWN_PASSWORD and try again."
                    ) from exc
            else:
                payload = {"act": "getassertion", "userid": self.username, "challstr": challstr}
                async with session.post("https://play.pokemonshowdown.com/action.php", data=payload) as resp:
                    assertion = await resp.text()

        await self.send(f"|/trn {self.username},0,{assertion}")

    async def challenge_target(self) -> None:
        if not self.target:
            return
        if self.team:
            await self.send(f"|/utm {self.team}")
        await self.send(f"|/challenge {self.target}, {self.battle_format}")

    async def handle_room_line(self, roomid: str, line: str) -> None:
        if line.startswith("|request|"):
            req = json.loads(line[len("|request|"):])
            self.state.roomid = roomid
            self.state.update_from_request(req)
            if req.get("wait"):
                return
            action = choose_action(req)
            await self.send(f"{roomid}|{action}")

    async def run(self) -> None:
        _, websockets = _require_runtime_deps()
        ws_url = f"wss://{self.server}/showdown/websocket"
        async with websockets.connect(ws_url, ping_interval=20, ping_timeout=20) as ws:
            self.ws = ws
            while True:
                raw = await ws.recv()
                if raw.startswith("|challstr|"):
                    challstr = raw.split("|challstr|", 1)[1]
                    await self.login(challstr)
                    await asyncio.sleep(0.5)
                    await self.challenge_target()
                    continue

                if not raw.startswith(">"):
                    continue

                lines = raw.split("\n")
                roomid = lines[0][1:]
                for line in lines[1:]:
                    if line:
                        await self.handle_room_line(roomid, line)


class YourSimpleBot(ShowdownBot):
    """Compatibility name."""


async def main(**legacy_kwargs: Any) -> None:
    """Run bot entrypoint (accepts ignored legacy kwargs for compatibility)."""
    bot = YourSimpleBot(**legacy_kwargs)
    await bot.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
