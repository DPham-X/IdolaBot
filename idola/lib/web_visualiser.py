import json
import logging
from copy import deepcopy
from itertools import chain
from urllib.parse import quote

from .util import shorten_url

logger = logging.getLogger(f"idola.{__name__}")


base_data = {
    "Party": "01",
    "CharacterID": [
        "100000 01",
        "100000 01",
        "100000 01",
        "100000 01",
        "100000 02",
        "100000 02",
        "100000 02",
        "100000 02",
    ],
    "CharacterLB": ["0", "0", "0", "0", "0", "0", "0", "0"],
    "CharacterD": ["0.5", "0.5", "0.5", "0.5", "0.5", "0.5", "0.5", "0.5"],
    "CharacterDB": ["0", "0", "0", "0", "0", "0", "0", "0"],
    "CharacterSPD": ["0", "0", "0", "0", "0", "0", "0", "0"],
    "WeaponID": [
        "200000000",
        "200000000",
        "200000000",
        "200000000",
        "200000000",
        "200000000",
        "200000000",
        "200000000",
    ],
    "WeaponSPD": ["0", "0", "0", "0", "0", "0", "0", "0"],
    "SoulID": [
        "300000000",
        "300000000",
        "300000000",
        "300000000",
        "300000000",
        "300000000",
        "300000000",
        "300000000",
    ],
    "SoulSPD": ["0", "0", "0", "0", "0", "0", "0", "0"],
    "SupportSPD": ["0", "0", "0", "0", "0", "0", "0", "0"],
    "IdoMagID": ["12700000 00", "12700000 00"],
    "IdoMagSPD": ["0", "0"],
    "IdoMagSPD01": ["0", "0"],
    "IdoMagSPD02": ["0", "0"],
    "IdoMagSPD03": ["0", "0"],
    "IdoMagSPD04": ["0", "0"],
    "IdoMagELE01": ["0", "0"],
    "IdoMagELE02": ["0", "0"],
    "IdoMagELE03": ["0", "0"],
    "IdoMagELE04": ["0", "0"],
}


class PartyStats(object):
    @classmethod
    def _import_party_info(cls, party_info):
        data = deepcopy(base_data)
        cls._set_main_party(data, party_info)
        cls._set_character(data, party_info)
        cls._set_character_lb(data, party_info)
        cls._set_character_d(data, party_info)
        cls._set_character_db(data, party_info)
        cls._set_weapon_symbols(data, party_info)
        cls._set_soul_symbols(data, party_info)
        cls._set_idomag(data, party_info)
        return data

    @classmethod
    def _set_main_party(cls, data, party_info):
        side_priority = party_info["side_priority"]
        data["Party"] = f"{side_priority:02d}"

    @classmethod
    def _set_character(cls, data, party_info):
        law_characters = [
            str(character["character"]["char_id"]) for character in party_info["law"]
        ]
        chaos_characters = [
            str(character["character"]["char_id"]) for character in party_info["chaos"]
        ]
        character_ids_encoded = []
        for character in chain(law_characters, chaos_characters):
            character_ids_encoded.append(character[:-2] + " " + character[-2:])
        data["CharacterID"] = character_ids_encoded

    @classmethod
    def _set_character_lb(cls, data, party_info):
        law_characters = [
            str(character["character"]["potential"]) for character in party_info["law"]
        ]
        chaos_characters = [
            str(character["character"]["potential"])
            for character in party_info["chaos"]
        ]
        lb_encoded = []
        for character in chain(law_characters, chaos_characters):
            lb_encoded.append(character)
        data["CharacterLB"] = lb_encoded

    @classmethod
    def _set_character_d(cls, data, party_info):
        law_characters = [
            character["destiny_bonus_status"] for character in party_info["law"]
        ]
        chaos_characters = [
            character["destiny_bonus_status"] for character in party_info["chaos"]
        ]
        d_encoded = []
        for db_status in chain(law_characters, chaos_characters):
            d_encoded.append(1 if db_status >= 1 else 0.5)
        data["CharacterD"] = d_encoded

    @classmethod
    def _set_character_db(cls, data, party_info):
        law_characters = [
            str(character["destiny_bonus_level"]) for character in party_info["law"]
        ]
        chaos_characters = [
            str(character["destiny_bonus_level"]) for character in party_info["chaos"]
        ]
        db_encoded = []
        for character in chain(law_characters, chaos_characters):
            db_encoded.append(character)
        data["CharacterDB"] = db_encoded

    @classmethod
    def _set_weapon_symbols(cls, data, party_info):
        law_weapon_symbols = [
            str(character["weapon_symbol"]["symbol_id"])
            for character in party_info["law"]
        ]
        chaos_weapon_symbols = [
            str(character["weapon_symbol"]["symbol_id"])
            for character in party_info["chaos"]
        ]
        weapon_symbols = [
            character for character in chain(law_weapon_symbols, chaos_weapon_symbols)
        ]
        data["WeaponID"] = weapon_symbols

    @classmethod
    def _set_soul_symbols(cls, data, party_info):
        law_soul_symbols = [
            str(character["soul_symbol"]["symbol_id"])
            for character in party_info["law"]
        ]
        chaos_soul_symbols = [
            str(character["soul_symbol"]["symbol_id"])
            for character in party_info["chaos"]
        ]
        soul_symbols = [
            character for character in chain(law_soul_symbols, chaos_soul_symbols)
        ]
        data["SoulID"] = soul_symbols

    @classmethod
    def _set_idomag(cls, data, party_info):
        law_idomag = str(party_info["law_idomag"]["idomag_type_id"])
        chaos_idomag = str(party_info["chaos_idomag"]["idomag_type_id"])
        encoded_idomag = []
        for character in chain([law_idomag, chaos_idomag]):
            encoded_idomag.append(character[:-2] + " " + character[-2:])
        data["IdoMagID"] = encoded_idomag


class AfuureusIdolaStatusTool(PartyStats):
    url = "https://afuureus.github.io/"

    @classmethod
    def generate_shareable_link(cls, party_info):
        data = cls._import_party_info(party_info)
        link = (
            cls.url
            + "?"
            + "build="
            + quote(json.dumps(data, separators=(",", ":")), safe="~@#$&()*!+=:;,.?/'")
            + "&format=nnstjp"
        )
        shortened_link = shorten_url(link)
        return shortened_link


class NNSTJPWebVisualiser(PartyStats):
    url = "https://kinomyu.github.io/NNSTJP.github.io/Idola/index.html"

    @classmethod
    def generate_shareable_link(cls, party_info):
        data = cls._import_party_info(party_info)
        link = (
            cls.url
            + "?"
            + quote(json.dumps(data, separators=(",", ":")), safe="~@#$&()*!+=:;,.?/'")
        )
        shortened_link = shorten_url(link)
        return shortened_link
