# -*- coding: utf-8 -*-
import asyncio
import logging
import re
from dataclasses import dataclass, field

import aiohttp
import textdistance
from bs4 import BeautifulSoup
from fuzzywuzzy import fuzz, process

logger = logging.getLogger(f"idola.{__name__}")


BUMPED_IDOLA_URL = "https://bumped.org/idola"
WEAPON_DATABASE_URL = BUMPED_IDOLA_URL + "/idola-weapon-database/"
SOUL_DATABASE_URL = BUMPED_IDOLA_URL + "/idola-soul-database/"


@dataclass
class WeaponSymbol(object):
    en_name: str
    jp_name: str
    base_stats: str = field(repr=False)
    arena_stats: str = field(repr=False)
    effect: str = field(repr=False)
    icon_url: str = field(repr=False)
    url: str = field(repr=False, default=WEAPON_DATABASE_URL)


@dataclass
class SoulSymbol(object):
    en_name: str
    jp_name: str
    requirements: str
    base_stats: str = field(repr=False)
    arena_stats: str = field(repr=False)
    effect: str = field(repr=False)
    icon_url: str = field(repr=False)
    url: str = field(repr=False, default=SOUL_DATABASE_URL)


def custom_scorer(s1, s2):
    s1 = s1.lower().replace("'", "")
    s2 = s2.lower().replace("'", "")
    s1 = s1.encode("utf-8")
    s2 = s2.encode("utf-8")
    score = textdistance.levenshtein.normalized_similarity(s1, s2)
    if score < 0.7:
        score = textdistance.sorensen.normalized_similarity(s1, s2)
    if score < 0.7:
        score = textdistance.jaro_winkler.normalized_similarity(s1, s2)
    if score < 0.7:
        score = float(fuzz.partial_ratio(s1, s2)) / float(100)
    if s1 not in s2:
        score -= 0.2
    score = int(score * 100)
    if score > 100:
        score = 100
    return score


class BumpedParser(object):
    def __init__(self):
        super(BumpedParser, self).__init__()
        self._RENDER_TIMEOUT = 30

        self.weapon_symbols = {}
        self.soul_symbols = {}

        asyncio.run(self.start())

    async def start(self):
        logger.info("Parsing Bumped website")
        self.weapon_symbols = {}
        self.soul_symbols = {}
        await self.import_weapon_symbols()
        await self.import_soul_symbols()

    async def import_weapon_symbols(self):
        async with aiohttp.ClientSession() as session:
            async with session.get(WEAPON_DATABASE_URL) as r:
                html = await r.text()
        soup = BeautifulSoup(html, "html.parser")

        # Remove javascript and css from html
        for script in soup(["script", "style"]):
            script.extract()

        tables = soup.findAll("table", {"class": "pso2"})
        for table in tables:
            max_table_len = len(table.findAll("tr"))
            for row in table.findAll("tr")[1:max_table_len]:
                col = row.findAll("td")
                if len(col) != 5:
                    continue
                icon_url = col[0].find("img").get("src")
                name = col[1].getText().strip()
                stats = col[2].getText().strip()
                arena_stats = col[3].getText().strip()
                effect = col[4].getText().strip()

                en_name, _, jp_name = name.partition("\n")
                cleaned_effect = re.sub(r"\n{2,}", r" ", effect)
                cleaned_effect = cleaned_effect.replace("\n[\n", "[").replace(
                    "\n]", "]"
                )
                ws = WeaponSymbol(
                    en_name=en_name,
                    jp_name=jp_name,
                    base_stats=stats,
                    arena_stats=arena_stats,
                    effect=cleaned_effect,
                    icon_url=icon_url,
                )
                self.weapon_symbols[en_name] = ws
                self.weapon_symbols[jp_name] = ws

    async def import_soul_symbols(self):
        async with aiohttp.ClientSession() as session:
            async with session.get(SOUL_DATABASE_URL) as r:
                html = await r.text()
        soup = BeautifulSoup(html, "html.parser")

        # Remove javascript and css from html
        for script in soup(["script", "style"]):
            script.extract()

        tables = soup.findAll("table", {"class": "pso2"})
        for table in tables:
            max_table_len = len(table.findAll("tr"))
            req = False
            row = table.findAll("tr")[0]
            col = row.findAll("th")
            if col[3].getText() == "Req.":
                req = True
            for row in table.findAll("tr")[1:max_table_len]:
                col = row.findAll("td")
                if len(col) != 5:
                    continue
                icon_url = col[0].find("img").get("src")
                name = col[1].getText().strip()
                stats = col[2].getText().strip()

                if req:
                    requirements = col[3].getText().strip()
                    arena_stats = None
                else:
                    requirements = None
                    arena_stats = col[3].getText().strip()

                effect = col[4].getText().strip()

                en_name, _, jp_name = name.partition("\n")
                en_name = en_name.strip()
                jp_name = jp_name.strip()
                cleaned_effect = re.sub(r"\n{2,}", r" ", effect)
                cleaned_effect = cleaned_effect.replace("\n[\n", "[").replace(
                    "\n]", "]"
                )
                ss = SoulSymbol(
                    en_name=en_name,
                    jp_name=jp_name,
                    requirements=requirements,
                    base_stats=stats,
                    arena_stats=arena_stats,
                    effect=cleaned_effect,
                    icon_url=icon_url,
                )
                self.soul_symbols[en_name] = ss
                self.soul_symbols[jp_name] = ss

    def get_unfuzzed_weapon_name(self, weapon_name):
        unfuzz_weapon_name, score = process.extractOne(
            weapon_name, self.weapon_symbols.keys(), scorer=custom_scorer
        )
        if score < 60:
            return False
        return unfuzz_weapon_name

    def get_unfuzzed_soul_name(self, soul_name):
        unfuzz_soul_name, score = process.extractOne(
            soul_name, self.soul_symbols.keys(), scorer=custom_scorer
        )
        if score < 60:
            return False
        return unfuzz_soul_name

    def get_weapon_database(self):
        return set(
            weapon_symbol.en_name for weapon_symbol in self.weapon_symbol.values()
        )

    def get_soul_database(self):
        return set(soul_symbol.en_name for soul_symbol in self.soul_symbols.values())


if __name__ == "__main__":
    bp = BumpedParser()
