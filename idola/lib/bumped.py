# -*- coding: utf-8 -*-
import asyncio
import logging
import re
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Optional

import textdistance
from bs4 import BeautifulSoup
from fuzzywuzzy import fuzz, process
from pyppeteer import launch

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


def custom_scorer(string1: str, string2: str) -> int:
    string1 = string1.lower().replace("'", "")
    string2 = string2.lower().replace("'", "")

    score = textdistance.levenshtein.normalized_similarity(string1, string2)
    if score < 0.7:
        score = textdistance.sorensen.normalized_similarity(string1, string2)
    if score < 0.7:
        score = textdistance.jaro_winkler.normalized_similarity(string1, string2)
    if score < 0.7:
        score = float(fuzz.partial_ratio(string1, string2)) / float(100)
    if string1 not in string2:
        score -= 0.2
    score = int(score * 100) if score < 100 else 100
    return score


@contextmanager
async def get_browser():
    browser = await launch(headless=True)
    try:
        yield browser
    finally:
        await browser.close()


class BumpedParser(object):
    def __init__(self):
        super(BumpedParser, self).__init__()
        self._RENDER_TIMEOUT = 30
        self._FUZZY_THRESHOLD_SCORE = 60
        self.weapon_symbols = {}
        self.soul_symbols = {}

        asyncio.run(self.start())

    async def start(self) -> None:
        logger.info("Parsing Bumped website")
        self.weapon_symbols = {}
        self.soul_symbols = {}
        await self.import_weapon_symbols()
        await self.import_soul_symbols()
        logger.info("Finished parsing Bumped website")

    async def import_weapon_symbols(self) -> None:
        with get_browser() as browser:
            page = await browser.newPage()
            await page.goto(WEAPON_DATABASE_URL)
            html = await page.content()
            soup = BeautifulSoup(html, "html.parser")

            # Remove javascript and css from html
            for script in soup(["script", "style"]):
                script.extract()

            tables = soup.findAll("table", {"class": "pso2"})
            for table in tables:
                max_table_len = len(table.findAll("tr"))
                for row in table.findAll("tr")[1:max_table_len]:
                    col = row.findAll("td")
                    symbol_data = self._extract_weapon_symbol_data(col)
                    weapon_symbol = WeaponSymbol(**symbol_data)
                    self.weapon_symbols[symbol_data["en_name"]] = weapon_symbol
                    self.weapon_symbols[symbol_data["jp_name"]] = weapon_symbol

    def _extract_weapon_symbol_data(self, bumped_table_col: list) -> dict:
        icon_url = bumped_table_col[0].find("img").get("src")
        name = bumped_table_col[1].getText().strip()
        stats = bumped_table_col[2].getText().strip()
        arena_stats = bumped_table_col[3].getText().strip()
        effect = bumped_table_col[4].getText().strip()

        en_name, _, jp_name = name.partition("\n")
        cleaned_effect = re.sub(r"\n{2,}", r" ", effect).replace("\n[\n", "[").replace("\n]", "]")
        return {
            "en_name": en_name,
            "jp_name": jp_name,
            "stats": stats,
            "arena_stats": arena_stats,
            "effect": cleaned_effect,
            "icon_url": icon_url,
        }

    async def import_soul_symbols(self) -> None:
        with get_browser() as browser:
            page = await browser.newPage()
            await page.goto(SOUL_DATABASE_URL)
            html = await page.content()
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
                    soul_symbol_data = self._extract_soul_symbol_data(col, req)
                    soul_symbol = SoulSymbol(**soul_symbol_data)
                    self.soul_symbols[soul_symbol_data["en_name"]] = soul_symbol
                    self.soul_symbols[soul_symbol_data["jp_name"]] = soul_symbol

    def _extract_soul_symbol_data(self, bumped_table_col: list, req: bool) -> dict:
        icon_url = bumped_table_col[0].find("img").get("src")
        name = bumped_table_col[1].getText().strip()
        stats = bumped_table_col[2].getText().strip()

        if req:
            requirements = bumped_table_col[3].getText().strip()
            arena_stats = None
        else:
            requirements = None
            arena_stats = bumped_table_col[3].getText().strip()

        effect = bumped_table_col[4].getText().strip()

        en_name, _, jp_name = name.partition("\n")
        en_name = en_name.strip()
        jp_name = jp_name.strip()
        cleaned_effect = re.sub(r"\n{2,}", r" ", effect).replace("\n[\n", "[").replace("\n]", "]")

        return {
            "en_name": en_name,
            "jp_name": jp_name,
            "requirements": requirements,
            "base_stats": stats,
            "arena_stats": arena_stats,
            "effect": cleaned_effect,
            "icon_url": icon_url,
        }

    def get_unfuzzed_weapon_name(self, weapon_name: str) -> Optional[str]:
        unfuzz_weapon_name, score = process.extractOne(weapon_name, self.weapon_symbols.keys(), scorer=custom_scorer)
        if score < self._FUZZY_THRESHOLD_SCORE:
            return None
        return unfuzz_weapon_name

    def get_unfuzzed_soul_name(self, soul_name: str) -> Optional[str]:
        unfuzz_soul_name, score = process.extractOne(soul_name, self.soul_symbols.keys(), scorer=custom_scorer)
        if score < self._FUZZY_THRESHOLD_SCORE:
            return None
        return unfuzz_soul_name

    def get_weapon_database(self) -> set[str]:
        return set(weapon_symbol.en_name for weapon_symbol in self.weapon_symbols.values())

    def get_soul_database(self) -> set[str]:
        return set(soul_symbol.en_name for soul_symbol in self.soul_symbols.values())
