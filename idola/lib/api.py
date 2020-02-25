# -*- coding: utf-8 -*-
import csv
import datetime
import hashlib
import json
import os
import pickle
import traceback
from collections import OrderedDict, defaultdict

import pylru
import pytz
import requests
from dotenv import load_dotenv


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


def unpack_newline(s, style="\n"):
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
discord_profile_ids = {}


def update_profile_cache(name, profile_id):
    global profile_cache
    profile_cache[name] = int(profile_id)


class HTTPClient(object):
    def __init__(self, user_agent):
        self.USER_AGENT = user_agent
        self.X_UNITY_VER = "2017.4.26f1"

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
    def __init__(self, user_agent, app_ver, device_id, device_token, token_key, uuid):
        self.load_profile_cache()
        self.load_discord_profile_ids()
        self.client = HTTPClient(user_agent)
        self.app_ver = app_ver
        self.auth_key = ""
        self.device_id = device_id
        self.device_token = device_token
        self.res_ver = ""
        self.retrans_key = ""
        self.session_key = ""
        self.token_key = token_key
        self.uuid = uuid
        self.character_map = {}

        self.import_id_map(os.path.join("lib", "idola_map", "Character ID.csv"))
        self.import_id_map(os.path.join("lib", "idola_map", "Weapon ID.csv"))
        self.import_id_map(os.path.join("lib", "idola_map", "Soul ID.csv"))
        self.import_id_map(os.path.join("lib", "idola_map", "Idomag ID.csv"))

        self.start()
        print("Idola API ready!")

    def start(self):
        try:
            self.api_init()
            self.pre_login()
            self.login()
            self.update_retrans_key()
        except Exception as e:
            print(e, traceback.format_exc())

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
        self.retrans_key = json_response["retrans_key"]

    def update_res_ver(self):
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
        self.res_ver = json_response["res_version"]
        print(f"ResVer updated to {self.res_ver}")

    def api_init(self):
        headers = {
            "Content-Type": "application/json",
            "User-Agent": self.client.USER_AGENT,
            "X-Unity-Version": self.client.X_UNITY_VER,
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
        auth_key = hashlib.sha1(to_hash.encode("utf-8")).hexdigest()
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
            "language_code": "Japanese",
            "battle_type": 0,
            "battle_id": 0,
            "is_tutorial": True,
            "region": "JP",
            "localtime": 8,
            "device_name": "Google Pixel XL",
            # "device_name": "iPadPro11Inch",
            "operating_system": "Android OS 5.1.1 / API-22 (NOF26V/500191128)",
            # "operating_system": "iOS 13.3.1",
            "i_info": 0,
        }
        response = self.client.post(IDOLA_USER_LOGIN, body)
        json_response = response.json()
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
            "is_tutorial": "false",
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
            ranking_information[profile_id]["arena_score_point"] = profile["score_point"]
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

    def get_arena_ranking(self, event_id, offset=0):
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
        self.retrans_key = json_response["retrans_key"]
        return ranking_list

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

    def get_raid_creation_ranking(self, event_id=None, offset=0):
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

    @staticmethod
    def epoch_to_datetime(epoch_time):
        utc_datetime = datetime.datetime.utcfromtimestamp(epoch_time)
        return utc_datetime

    @staticmethod
    def datetime_jp_format(d1):
        localised_utc = pytz.utc.localize(d1)
        jp_tz = pytz.timezone("Asia/Tokyo")
        jp_datetime = jp_tz.normalize(localised_utc)
        return jp_datetime.strftime("%Y-%m-%d %H:%M:%S %Z%z")

    @staticmethod
    def datetime_difference(d1, d2):
        days = abs((d2 - d1).days)
        seconds = abs((d2 - d1).seconds)
        hours, seconds = divmod(seconds, 3600)
        minutes, _ = divmod(seconds, 60)
        return f"{days}d {hours}h {minutes}m"

    @staticmethod
    def get_current_time():
        cur_time = datetime.datetime.utcnow()
        return cur_time

    @staticmethod
    def destiny_bonus(level, status):
        if status == 0:
            return "-"
        else:
            return level

    @staticmethod
    def truncate(text):
        return text if len(text) < 20 else text[:18] + ".."

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
            for (profile_id, ranking_information,) in ranking_information_intervals.items():
                update_profile_cache(ranking_information["name"], profile_id)
                players[profile_id]["name"] = ranking_information["name"]
                players[profile_id]["arena_score_rank"] = ranking_information["arena_score_rank"]
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
            for ranking_information in sorted(ranking_information_intervals, key=lambda item: item["score_rank"]):
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
                msg.append(f"{raid_score_rank}: {raid_score_point:,d} - {name}({profile_id})")
        return "\n".join(msg)

    def show_raid_creation_top_100_players(self, event_id=None):
        msg = []
        if not event_id:
            event_id = self.get_latest_raid_event_id()
        top_100_ranking_information = [
            self.get_raid_creation_ranking(event_id, 0),
            self.get_raid_creation_ranking(event_id, 20),
            self.get_raid_creation_ranking(event_id, 40),
            self.get_raid_creation_ranking(event_id, 60),
            self.get_raid_creation_ranking(event_id, 80),
        ]

        prev_profile_id = None
        for ranking_information_intervals in top_100_ranking_information:
            for ranking_information in sorted(ranking_information_intervals, key=lambda item: item["score_rank"],):
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
                msg.append(f"{raid_score_rank}: {raid_score_point:,d} - {name}({profile_id})")
        return "\n".join(msg)

    def get_top_100_arena_border(self, event_id=None):
        try:
            if not event_id:
                event_id = self.get_latest_arena_event_id()
            ranking_information = self.get_arena_ranking(event_id, 99)
            sorted_ranking_information = sorted(
                [player_information["score_point"] for player_information in ranking_information], reverse=True
            )
            return sorted_ranking_information[0]
        except IndexError as e:
            print(e, traceback.format_exc())
            return None

    def get_top_500_arena_border(self, event_id=None):
        try:
            if not event_id:
                event_id = self.get_latest_arena_event_id()
            ranking_information = self.get_arena_ranking(event_id, 499)
            sorted_ranking_information = sorted(
                [player_information["score_point"] for player_information in ranking_information], reverse=True
            )
            return sorted_ranking_information[0]
        except IndexError as e:
            print(e, traceback.format_exc())
            return None

    def get_top_1000_arena_border(self, event_id=None):
        try:
            if not event_id:
                event_id = self.get_latest_arena_event_id()
            ranking_information = self.get_arena_ranking(event_id, 999)
            sorted_ranking_information = sorted(
                [player_information["score_point"] for player_information in ranking_information], reverse=True
            )
            return sorted_ranking_information[0]
        except IndexError as e:
            print(e, traceback.format_exc())
            return None

    def get_top_100_raid_suppression_border(self, event_id=None):
        try:
            if not event_id:
                event_id = self.get_latest_raid_event_id()
            ranking_information = self.get_raid_battle_ranking(event_id, 99)
            sorted_ranking_information = sorted(
                [player_information["score_point"] for player_information in ranking_information], reverse=True
            )
            return sorted_ranking_information[0]
        except IndexError as e:
            print(e, traceback.format_exc())
            return None

    def get_top_500_raid_suppression_border(self, event_id=None):
        try:
            if not event_id:
                event_id = self.get_latest_raid_event_id()
            ranking_information = self.get_raid_battle_ranking(event_id, 499)
            sorted_ranking_information = sorted(
                [player_information["score_point"] for player_information in ranking_information], reverse=True
            )
            return sorted_ranking_information[0]
        except IndexError as e:
            print(e, traceback.format_exc())
            return None

    def get_top_1000_raid_suppression_border(self, event_id=None):
        try:
            if not event_id:
                event_id = self.get_latest_raid_event_id()
            ranking_information = self.get_raid_battle_ranking(event_id, 999)
            sorted_ranking_information = sorted(
                [player_information["score_point"] for player_information in ranking_information], reverse=True
            )
            return sorted_ranking_information[0]
        except IndexError as e:
            print(e, traceback.format_exc())
            return None

    def get_top_5000_raid_suppression_border(self, event_id=None):
        try:
            if not event_id:
                event_id = self.get_latest_raid_event_id()
            ranking_information = self.get_raid_battle_ranking(event_id, 4999)
            sorted_ranking_information = sorted(
                [player_information["score_point"] for player_information in ranking_information], reverse=True
            )
            return sorted_ranking_information[0]
        except IndexError as e:
            print(e, traceback.format_exc())
            return None

    def get_top_100_raid_creation_border(self, event_id=None):
        try:
            event_id = self.get_latest_raid_event_id()
            ranking_information = self.get_raid_creation_ranking(event_id, 99)
            sorted_ranking_information = sorted(
                [player_information["score_point"] for player_information in ranking_information], reverse=True
            )
            return sorted_ranking_information[0]
        except IndexError as e:
            print(e, traceback.format_exc())
            return None

    def get_top_500_raid_creation_border(self, event_id=None):
        try:
            event_id = self.get_latest_raid_event_id()
            ranking_information = self.get_raid_creation_ranking(event_id, 499)
            sorted_ranking_information = sorted(
                [player_information["score_point"] for player_information in ranking_information], reverse=True
            )
            return sorted_ranking_information[0]
        except IndexError as e:
            print(e, traceback.format_exc())
            return None

    def get_top_1000_raid_creation_border(self, event_id=None):
        try:
            if not event_id:
                event_id = self.get_latest_raid_event_id()
            ranking_information = self.get_raid_creation_ranking(event_id, 999)
            sorted_ranking_information = sorted(
                [player_information["score_point"] for player_information in ranking_information], reverse=True
            )
            return sorted_ranking_information[0]
        except IndexError as e:
            print(e, traceback.format_exc())
            return None

    def get_top_5000_raid_creation_border(self, event_id=None):
        try:
            if not event_id:
                event_id = self.get_latest_raid_event_id()
            ranking_information = self.get_raid_creation_ranking(event_id, 4999)
            sorted_ranking_information = sorted(
                [player_information["score_point"] for player_information in ranking_information], reverse=True
            )
            return sorted_ranking_information[0]
        except IndexError as e:
            print(e, traceback.format_exc())
            return None

    def get_image_from_character_id(self, char_id):
        char_image_template = "https://raw.githubusercontent.com/NNSTJP/Idola/master/Character%20Icon/{}.png"
        default_image = "https://i0.wp.com/bumped.org/idola/wp-content/uploads/2019/11/character-rappy-thumb.png"
        s_char_id = str(char_id)
        if s_char_id not in self.character_map:
            return default_image
        image_name = s_char_id[:-2] + "%20" + s_char_id[-2:]
        return char_image_template.format(image_name)

    def get_arena_team_composition(self, profile_id):
        party_info = self.get_arena_party_info(profile_id)
        name = party_info["player_name"]
        arena_team_score = party_info["strength_value"]
        avatar_url = self.get_image_from_character_id(party_info["avator_character_id"])

        law_char_names = [
            self.truncate(self.get_name_from_id(character["character"]["char_id"]))
            + "\n"
            + lb_bullet(character["character"]["potential"])
            + braced_number(self.destiny_bonus(character["destiny_bonus_level"], character["destiny_bonus_status"],))
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
            law_idomag_type = self.get_name_from_id(party_info["law_idomag"]["idomag_type_id"])
        except Exception:
            law_idomag_type = None

        try:
            law_idomag_name = party_info["law_idomag"]["name"]
        except Exception:
            law_idomag_name = None

        chaos_char_names = [
            self.truncate(self.get_name_from_id(character["character"]["char_id"]))
            + "\n"
            + lb_bullet(character["character"]["potential"])
            + braced_number(self.destiny_bonus(character["destiny_bonus_level"], character["destiny_bonus_status"],))
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
            chaos_idomag_type = self.get_name_from_id(party_info["chaos_idomag"]["idomag_type_id"])
        except Exception:
            chaos_idomag_type = None

        try:
            chaos_idomag_name = party_info["chaos_idomag"]["name"]
        except Exception:
            chaos_idomag_name = None

        update_profile_cache(name, profile_id)
        return {
            "player_name": name,
            "avatar_url": avatar_url,
            "team_score": arena_team_score,
            "law_characters": unpack_newline(law_char_names),
            "law_weapon_symbols": unpack_newline(law_wep_names),
            "law_soul_symbols": unpack_newline(law_soul_names),
            "law_idomag": f"{law_idomag_type}({law_idomag_name})" if law_idomag_type else "-",
            "chaos_characters": unpack_newline(chaos_char_names),
            "chaos_weapon_symbols": unpack_newline(chaos_wep_names),
            "chaos_soul_symbols": unpack_newline(chaos_soul_names),
            "chaos_idomag": f"{chaos_idomag_type}({chaos_idomag_name})" if chaos_idomag_type else "-",
            "party_info": party_info,
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

    def get_raid_event_end_date(self):
        home_notice = self.get_home_notice()
        raid_end_date = home_notice["raid"]["end_date"]
        return self.epoch_to_datetime(raid_end_date) - datetime.timedelta(hours=5)

    def get_arena_event_end_date(self):
        home_notice = self.get_home_notice()
        arena_end_date = home_notice["ant"]["end_date"]
        return self.epoch_to_datetime(arena_end_date) - datetime.timedelta(hours=5)

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

    def register_discord_profile_id(self, discord_id, profile_id):
        discord_profile_ids[discord_id] = profile_id
        return True

    def get_profile_id_from_discord_id(self, discord_id):
        return discord_profile_ids.get(discord_id, None)

    def save_discord_profile_ids(self):
        pickle.dump(discord_profile_ids, open("discord_profile_ids.p", "wb"))
        return True

    def load_discord_profile_ids(self):
        global discord_profile_ids
        try:
            discord_profile_ids = pickle.load(open("discord_profile_ids.p", "rb"))
        except FileNotFoundError as e:
            print(f"Error: Could not load profile_cache - {e}")
            return False
        print("Discord ID DB loaded")
        return True

if __name__ == "__main__":
    load_dotenv()

    IDOLA_USER_AGENT = os.getenv("IDOLA_USER_AGENT")
    IDOLA_APP_VER = os.getenv("IDOLA_APP_VER")
    IDOLA_DEVICE_ID = os.getenv("IDOLA_DEVICE_ID")
    IDOLA_DEVICE_TOKEN = os.getenv("IDOLA_DEVICE_TOKEN")
    IDOLA_TOKEN_KEY = os.getenv("IDOLA_TOKEN_KEY")
    IDOLA_UUID = os.getenv("IDOLA_UUID")

    idola = IdolaAPI(IDOLA_USER_AGENT, IDOLA_APP_VER, IDOLA_DEVICE_ID, IDOLA_DEVICE_TOKEN, IDOLA_TOKEN_KEY, IDOLA_UUID,)
