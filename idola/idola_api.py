# -*- coding: utf-8 -*-
import csv
import hashlib
import json
import os
import pickle
import pylru
import requests
import sys
import time
from collections import defaultdict, OrderedDict
from dotenv import load_dotenv
from pprint import pprint


IDOLA_API_URL = "https://game.idola.jp/api"
IDOLA_API_INIT = "https://service.idola.jp/api/app/init"
IDOLA_USER_PRELOGIN = IDOLA_API_URL + "/user/prelogin"
IDOLA_USER_LOGIN = IDOLA_API_URL + "/user/login"
IDOLA_HOME_NOTICE = IDOLA_API_URL + "/home/notice"
IDOLA_HOME_NOW = IDOLA_API_URL + "/home/getnow"
IDOLA_ARENA_PARTY_DETAILS = IDOLA_API_URL + "/ant/partydetails"
IDOLA_ARENA_EVENT_INFO = IDOLA_API_URL + "/ant/eventinfo"
IDOLA_ARENA_RANKING = IDOLA_API_URL + "/ant/ranking"
IDOLA_ARENA_RANKING_OFFSET = IDOLA_API_URL + "/ant/offsetranking"
IDOLA_RAID_EVENT_INFO = IDOLA_API_URL + "/raid/geteventinfo"
IDOLA_RAID_RANKING = IDOLA_API_URL + "/raid/ranking"
IDOLA_RAID_RANKING_OFFSET = IDOLA_API_URL + "/raid/offsetranking"


def unpack(s):
    return ",".join(map(str, s))

def unpack_newline(s, style='\n'):
    return f"{style}".join(map(str, s))

def braced_number(number):
    return "(" + str(number) + ")"

def lb_bullet(number):
    if number == 0:
        return "``\u25CB\u25CB\u25CB\u25CB``"
    elif number == 1:
        return "``\u25CF\u25CB\u25CB\u25CB``"
    elif number == 2:
        return "``\u25CF\u25CF\u25CB\u25CB``"
    elif number == 3:
        return "``\u25CF\u25CF\u25CF\u25CB``"
    elif number == 4:
        return "``\u25CF\u25CF\u25CF\u25CF``"
    else:
        return number


profile_cache = pylru.lrucache(size=1000)
def update_profile_cache(name, profile_id):
    global profile_cache
    profile_cache[name] = int(profile_id)


class HTTPClient(object):
    # USER_AGENT = "Dalvik/2.1.0 (Linux; U; Android 5.1.1; Pixel XL Build/NOF26V)"
    USER_AGENT = "idola/43 CFNetwork/1121.2.2 Darwin/19.3.0"
    X_UNITY_VER = "2017.4.26f1"
    def post(self, url, body={}, headers={}):
        if not headers:
            headers = {
                "Content-Type": "application/json",
                "User-Agent": self.USER_AGENT,
            }
        json_output = json.dumps(body)
        response = requests.post(url, headers=headers, data=json_output)
        if response.status_code != 200:
            raise Exception(f"API Error: {response.status_code}")
        return response

    def get(self, url):
        headers = {
            "User-Agent": self.USER_AGENT,
        }
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            raise Exception(f"API Error: {response.status_code}")
        return response


class IdolaAPI(object):
    def __init__(self, app_ver, device_id, device_token, token_key):
        self.load_profile_cache()
        self.client = HTTPClient()
        self.app_ver = app_ver
        self.auth_key = ""
        self.device_id = device_id
        self.device_token = device_token
        self.res_ver = ""
        self.retrans_key = ""
        self.session_key = ""
        self.token_key = token_key
        self.uuid = "cee01c9f-2492-43aa-84eb-54ecf6b6da70"

        self.character_map = {}
        self.import_id_map(os.path.join("Idola", "Character ID.csv"))
        self.import_id_map(os.path.join("Idola", "Weapon ID.csv"))
        self.import_id_map(os.path.join("Idola", "Soul ID.csv"))
        self.import_id_map(os.path.join("Idola", "Idomag ID.csv"))

        self.api_init()
        self.pre_login()
        self.login()
        self.update_retrans_key()
        print("Idola API ready!")

    def import_id_map(self, csv_filepath):
        # https://github.com/NNSTJP/Idola
        with open(csv_filepath, newline="") as csvfile:
            char_csv = csv.reader(csvfile, delimiter=",")
            for row in char_csv:
                self.character_map[str(row[0])] = str(row[1])

    def get_name_from_id(self, char_id):
        if not char_id:
            return "-"
        for c_id in self.character_map:
            if str(char_id).startswith(c_id):
                return self.character_map[c_id]
        print(f"Unknown char_id: {char_id}")
        return "Unknown"

    def update_retrans_key(self):
        response = self.client.post(IDOLA_HOME_NOW)
        json_response = response.json()
        retrans_key = json_response["retrans_key"]
        print(f"Updating retrans_key: {retrans_key}")
        return retrans_key

    def api_init(self):
        headers = {
            "Content-Type": "application/json",
            "User-Agent": HTTPClient.USER_AGENT,
            "X-Unity-Version": HTTPClient.X_UNITY_VER,
        }
        body = {
            "app_ver": self.app_ver,
            "retrans_key": None,
            "uuid": "",
        }
        response = self.client.post(IDOLA_API_INIT, body, headers)
        json_response = response.json()
        self.retrans_key = json_response["retrans_key"]
        self.res_ver = json_response["res_version"]
        print(f"ResVer: {self.res_ver}")

    def pre_login(self):
        body = {
            "app_ver": self.app_ver,
            "res_ver": self.res_ver,
            "retrans_key": self.retrans_key,
            "uuid": self.uuid,
        }
        response = self.client.post(IDOLA_USER_PRELOGIN, body)
        json_response = response.json()
        self.session_key = json_response["replace"]["session_key"]
        self.retrans_key = json_response["retrans_key"]
        self.set_auth_key()

    def set_auth_key(self):
        to_hash = self.token_key + ":" + self.session_key
        auth_key = hashlib.sha1(to_hash.encode('utf-8')).hexdigest()
        self.auth_key = auth_key
        print(f"Auth_key: {auth_key}")

    def login(self):
        body = {
            "app_ver": self.app_ver,
            "res_ver": self.res_ver,
            "auth_key": self.auth_key,
            "retrans_key": self.retrans_key,
            "device_id": self.device_id,
            "device_token": self.device_token,
            "language_code": "English",
            "battle_type": 0,
            "battle_id": 0,
            "is_tutorial": True,
            "region": "JP",
            "localtime": 8,
            # "device_name": "Google Pixel XL",
            "device_name": "iPadPro11Inch",
            # "operating_system": "Android OS 5.1.1 / API-22 (NOF26V/500191128)",
            "operating_system": "iOS 13.3.1",

            "i_info": 0,
        }
        response = self.client.post(IDOLA_USER_LOGIN, body)
        json_response = response.json()
        retrans_key = json_response["retrans_key"]
        self.retrans_key = json_response["retrans_key"]

    def get_latest_arena_event_id(self):
        body = {
            "app_ver": self.app_ver,
            "res_ver": self.res_ver,
            "auth_key": self.auth_key,
            "retrans_key": self.retrans_key,
            "is_tutorial": "false",
            "readed_character_promotion_id_list": None,
        }
        response = self.client.post(IDOLA_HOME_NOTICE, body)
        json_response = response.json()
        event_id = json_response["replace"]["ant"]["event_id"]
        self.retrans_key = json_response["retrans_key"]
        return event_id

    def get_home_notice(self):
        body = {
            "app_ver": self.app_ver,
            "res_ver": self.res_ver,
            "auth_key": self.auth_key,
            "retrans_key": self.retrans_key,
            "is_tutorial": False,
            "readed_character_promotion_id_list": None,
        }
        response = self.client.post(IDOLA_HOME_NOTICE, body)
        json_response = response.json()
        home_notice = json_response["replace"]
        self.retrans_key = json_response["retrans_key"]
        return home_notice

    def get_arena_ranking_offset(self, event_id, offset=0):
        body = {
            "app_ver": self.app_ver,
            "res_ver": self.res_ver,
            "auth_key": self.auth_key,
            "retrans_key": self.retrans_key,
            "event_id": event_id,
            "ranking_offset": offset,
        }
        response = self.client.post(IDOLA_ARENA_RANKING_OFFSET, body)
        json_response = response.json()
        ranking_list = json_response["replace"]["ranking_list"]
        ranking_information = defaultdict(dict)
        for profile in ranking_list:
            profile_id = profile["friend_profile"]["profile_id"]
            ranking_information[profile_id]["name"] = profile["friend_profile"]["name"]
            ranking_information[profile_id]["arena_score_rank"] = profile["score_rank"]
            ranking_information[profile_id]["arena_score_point"] = profile[
                "score_point"
            ]
        self.retrans_key = json_response["retrans_key"]
        return ranking_information

    def get_arena_party_info(self, profile_id):
        body = {
            "app_ver": self.app_ver,
            "res_ver": self.res_ver,
            "auth_key": self.auth_key,
            "retrans_key": self.retrans_key,
            "profile_id": profile_id,
        }
        response = self.client.post(IDOLA_ARENA_PARTY_DETAILS, body)
        json_response = response.json()
        party_info = json_response["replace"]["party_info"]
        self.retrans_key = json_response["retrans_key"]
        return party_info

    def get_latest_raid_event_id(self):
        body = {
            "app_ver": self.app_ver,
            "res_ver": self.res_ver,
            "auth_key": self.auth_key,
            "retrans_key": self.retrans_key,
            "is_tutorial": "false",
            "readed_character_promotion_id_list": None,
        }
        response = self.client.post(IDOLA_HOME_NOTICE, body)
        json_response = response.json()
        event_id = json_response["replace"]["raid"]["event_id"]
        self.retrans_key = json_response["retrans_key"]
        return event_id

    def get_raid_battle_ranking(self, event_id=None, offset=0):
        if not event_id:
            event_id = self.get_latest_raid_event_id()
        body = {
            "app_ver": self.app_ver,
            "res_ver": self.res_ver,
            "auth_key": self.auth_key,
            "retrans_key": self.retrans_key,
            "idola_event_id": event_id,
            "ranking_offset": offset,
            "ranking_type": 2,
        }
        response = self.client.post(IDOLA_RAID_RANKING_OFFSET, body)
        json_response = response.json()
        ranking_list = json_response["replace"]["suppression_ranking"]
        self.retrans_key = json_response["retrans_key"]
        return ranking_list

    def get_raid_summon_ranking(self, event_id=None, offset=0):
        if not event_id:
            event_id = self.get_latest_raid_event_id()
        body = {
            "app_ver": self.app_ver,
            "res_ver": self.res_ver,
            "auth_key": self.auth_key,
            "retrans_key": self.retrans_key,
            "idola_event_id": event_id,
            "ranking_offset": offset,
            "ranking_type": 1,
        }
        response = self.client.post(IDOLA_RAID_RANKING_OFFSET, body)
        json_response = response.json()
        ranking_list = json_response["replace"]["creator_ranking"]
        self.retrans_key = json_response["retrans_key"]
        return ranking_list

    def show_arena_ranking_top_100_players(self, event_id=None):
        players = defaultdict(dict)
        if not event_id:
            event_id = self.get_latest_arena_event_id()
        top_100_ranking_information = [
            self.get_arena_ranking_offset(event_id, 0),
            self.get_arena_ranking_offset(event_id, 20),
            self.get_arena_ranking_offset(event_id, 40),
            self.get_arena_ranking_offset(event_id, 60),
            self.get_arena_ranking_offset(event_id, 80),
        ]
        for ranking_information_intervals in top_100_ranking_information:
            for profile_id, ranking_information in ranking_information_intervals.items():
                update_profile_cache(ranking_information["name"], profile_id)
                players[profile_id]["name"] = ranking_information["name"]
                players[profile_id]["arena_score_rank"] =  ranking_information["arena_score_rank"]
                players[profile_id]["arena_score_point"] = ranking_information["arena_score_point"]
        return players

    def show_raid_suppression_top_100_players(self, event_id=None):
        msg = []
        if not event_id:
            event_id = self.get_latest_raid_event_id()
        top_100_ranking_information = [
            self.get_raid_battle_ranking(event_id, 0),
            self.get_raid_battle_ranking(event_id, 20),
            self.get_raid_battle_ranking(event_id, 40),
            self.get_raid_battle_ranking(event_id, 60),
            self.get_raid_battle_ranking(event_id, 80),
        ]

        prev_profile_id = None
        for ranking_information_intervals in top_100_ranking_information:
            for ranking_information in sorted(
                ranking_information_intervals, key=lambda item: item["score_rank"],
            ):
                name = ranking_information["friend_profile"]["name"]
                profile_id = ranking_information["friend_profile"]["profile_id"]
                update_profile_cache(name, profile_id)
                if profile_id == prev_profile_id:
                    continue
                prev_profile_id = ranking_information["friend_profile"]["profile_id"]
                raid_score_rank = ranking_information["score_rank"]
                raid_score_point = ranking_information["score_point"]
                if raid_score_rank > 100:
                    break
                msg.append(
                    f"{raid_score_rank}: {raid_score_point:,d} - {name}({profile_id})"
                )
        return "\n".join(msg)

    def show_raid_creation_top_100_players(self, event_id=None):
        msg = []
        if not event_id:
            event_id = self.get_latest_raid_event_id()
        top_100_ranking_information = [
            self.get_raid_summon_ranking(event_id, 0),
            self.get_raid_summon_ranking(event_id, 20),
            self.get_raid_summon_ranking(event_id, 40),
            self.get_raid_summon_ranking(event_id, 60),
            self.get_raid_summon_ranking(event_id, 80),
        ]

        prev_profile_id = None
        for ranking_information_intervals in top_100_ranking_information:
            for ranking_information in sorted(
                ranking_information_intervals, key=lambda item: item["score_rank"],
            ):
                name = ranking_information["friend_profile"]["name"]
                profile_id = ranking_information["friend_profile"]["profile_id"]
                update_profile_cache(name, profile_id)
                if profile_id == prev_profile_id:
                    continue
                prev_profile_id = ranking_information["friend_profile"]["profile_id"]
                raid_score_rank = ranking_information["score_rank"]
                raid_score_point = ranking_information["score_point"]
                if raid_score_rank > 100:
                    break
                msg.append(
                    f"{raid_score_rank}: {raid_score_point:,d} - {name}({profile_id})"
                )
        return "\n".join(msg)

    def show_top_100_arena_border(self, event_id=None):
        msg = []
        if not event_id:
            event_id = self.get_latest_arena_event_id()
        border_score_point = None
        ranking_information_81_100 = self.get_arena_ranking_offset(event_id, 80)
        for ranking_information in ranking_information_81_100.values():
            if ranking_information["arena_score_rank"] == 100:
                border_score_point = ranking_information["arena_score_point"]
                break

        if border_score_point is None:
            raise Exception("Could not find the Top 100 border score")

        msg.append(f"Top 100 Arena border is currently {border_score_point:,d} points")
        return "\n".join(msg)

    def show_top_100_arena_border_number(self, event_id=None):
        msg = []
        if not event_id:
            event_id = self.get_latest_arena_event_id()
        border_score_point = None
        ranking_information_81_100 = self.get_arena_ranking_offset(event_id, 80)
        for ranking_information in ranking_information_81_100.values():
            if ranking_information["arena_score_rank"] == 100:
                border_score_point = ranking_information["arena_score_point"]
                break

        if border_score_point is None:
            raise Exception("Could not find the Top 100 border score")

        return border_score_point

    def show_top_100_raid_suppression_border(self, event_id=None):
        msg = []
        border_score_point = None
        event_id = self.get_latest_raid_event_id()
        ranking_information_81_100 = self.get_raid_battle_ranking(event_id, 80)
        for ranking_information in ranking_information_81_100:
            if ranking_information["score_rank"] == 100:
                border_score_point = ranking_information["score_point"]
                break

        if border_score_point is None:
            raise Exception("Could not find the Top 100 border score")

        msg.append(
            f"Top 100 Idola Raid Supression border is currently {border_score_point:,d} points"
        )
        return "\n".join(msg)

    def show_top_100_raid_suppression_border_number(self, event_id=None):
        border_score_point = None
        if not event_id:
            event_id = self.get_latest_raid_event_id()
        ranking_information_81_100 = self.get_raid_battle_ranking(event_id, 80)
        for ranking_information in ranking_information_81_100:
            if ranking_information["score_rank"] == 100:
                border_score_point = ranking_information["score_point"]
                break

        if border_score_point is None:
            raise Exception("Could not find the Top 100 border score")

        return border_score_point

    def show_top_100_raid_creator_border(self, event_id=None):
        msg = []
        border_score_point = None
        event_id = self.get_latest_raid_event_id()
        ranking_information_81_100 = self.get_raid_summon_ranking(event_id, 80)
        for ranking_information in ranking_information_81_100:
            if ranking_information["score_rank"] == 100:
                border_score_point = ranking_information["score_point"]
                break

        if border_score_point is None:
            raise Exception("Could not find the Top 100 border score")

        msg.append(
            f"Top 100 Idola Raid Summon border is currently {border_score_point:,d} points"
        )
        return "\n".join(msg)

    @staticmethod
    def destiny_bonus(level, status):
        if status == 0:
            return "-"
        else:
            return level

    def truncate(self, text):
        return (text if len(text) < 20 else text[:18] + "..")

    def get_arena_team_composition(self, profile_id):
        msg = []
        party_info = self.get_arena_party_info(profile_id)
        name = party_info["player_name"]
        arena_team_score = party_info["strength_value"]
        avatar_character_id = party_info["avator_character_id"]
        law_char_names = [
            self.truncate(self.get_name_from_id(character["character"]["char_id"]))
            + "\n"
            + lb_bullet(character["character"]["potential"])
            + braced_number(
                self.destiny_bonus(
                    character["destiny_bonus_level"], character["destiny_bonus_status"]
                )
            )
            for character in party_info["law"]
        ]
        law_wep_names = [
            self.truncate(self.get_name_from_id(character["weapon_symbol"]["symbol_id"]))
            + "\n"
            + "LV"
            + str(character["weapon_symbol"]["level"])
            for character in party_info["law"]
        ]
        law_soul_names = [
            self.truncate(self.get_name_from_id(character["soul_symbol"]["symbol_id"]))
            + "\n"
            + "LV"
            + str(character["soul_symbol"]["level"])
            for character in party_info["law"]
        ]
        try:
            law_idomag_type = self.get_name_from_id(
                party_info["law_idomag"]["idomag_type_id"]
            )
        except:
            law_idomag_type = None

        try:
            law_idomag_name = party_info["law_idomag"]["name"]
        except:
            law_idomag_name = None

        chaos_char_names = [
            self.truncate(self.get_name_from_id(character["character"]["char_id"]))
            + "\n"
            + lb_bullet(character["character"]["potential"])
            + braced_number(
                self.destiny_bonus(
                    character["destiny_bonus_level"], character["destiny_bonus_status"]
                )
            )
            for character in party_info["chaos"]
        ]
        chaos_wep_names = [
            self.truncate(self.get_name_from_id(character["weapon_symbol"]["symbol_id"]))
            + "\n"
            + "LV"
            + str(character["weapon_symbol"]["level"])
            for character in party_info["chaos"]
        ]
        chaos_soul_names = [
            self.truncate(self.get_name_from_id(character["soul_symbol"]["symbol_id"]))
            + "\n"
            + "LV"
            + str(character["soul_symbol"]["level"])
            for character in party_info["chaos"]
        ]
        try:
            chaos_idomag_type = self.get_name_from_id(
                party_info["chaos_idomag"]["idomag_type_id"]
            )
        except:
            chaos_idomag_type = None

        try:
            chaos_idomag_name = party_info["chaos_idomag"]["name"]
        except:
            chaos_idomag_name = None

        update_profile_cache(name, profile_id)
        return {
            "player_name": name,
            "avatar_id": avatar_character_id,
            "team_score": arena_team_score,
            "law_characters": unpack_newline(law_char_names),
            "law_weapon_symbols": unpack_newline(law_wep_names),
            "law_soul_symbols": unpack_newline(law_soul_names),
            "law_idomag": f"{law_idomag_type}({law_idomag_name})" if law_idomag_type else '-',
            "chaos_characters": unpack_newline(chaos_char_names),
            "chaos_weapon_symbols": unpack_newline(chaos_wep_names),
            "chaos_soul_symbols": unpack_newline(chaos_soul_names),
            "chaos_idomag": f"{chaos_idomag_type}({chaos_idomag_name})" if chaos_idomag_type else '-',
        }

    def get_profile_id_from_name(self, name):
        if name in profile_cache:
            return profile_cache.get(name)

        players = self.show_arena_ranking_top_100_players()
        for profile_id, ranking_information in players.items():
            if ranking_information["name"].startswith(name):
                return profile_id
        return None

    def get_arena_team_composition_from_name(self, name):
        profile_id = self.get_profile_id_from_name(name)
        if not profile_id:
            return None
        return self.get_arena_team_composition(int(profile_id))

    def save_profile_cache(self):
        profile_dict = OrderedDict()
        for k, v in profile_cache.items():
            profile_dict[k] = v
        pickle.dump(profile_dict, open("profile_cache.p", "wb"))
        return True

    def load_profile_cache(self):
        global profile_cache
        try:
            profile_dict = pickle.load(open("profile_cache.p", "rb"))
            for k, v in reversed(profile_dict.items()):
                profile_cache[k] = v
        except FileNotFoundError as e:
            print(f"Error: Could not load profile_cache - {e}")
            return False
        print("Profile cache loaded")
        return True


if __name__ == "__main__":
    load_dotenv()

    IDOLA_APP_VER = os.getenv('IDOLA_APP_VER')
    IDOLA_DEVICE_ID = os.getenv('IDOLA_DEVICE_ID')
    IDOLA_DEVICE_TOKEN = os.getenv('IDOLA_DEVICE_TOKEN')
    IDOLA_TOKEN_KEY = os.getenv('IDOLA_TOKEN_KEY')

    idola = IdolaAPI(IDOLA_APP_VER, IDOLA_DEVICE_ID, IDOLA_DEVICE_TOKEN, IDOLA_TOKEN_KEY)
