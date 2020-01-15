# -*- coding: utf-8 -*-
import csv
import json
import os
import requests
import sys
import time
from collections import defaultdict
from pprint import pprint

AUTH_KEY = "f04761bb65d44816e97e60de05e122d7abffa30c"  # Refreshes when you log into the main game
RES_VER = "123ef2a18f47ca29d712451e6091565d"  # ResourceVersion?

IDOLA_API_URL = "https://game.idola.jp/api"
IDOLA_HOME_NOW = IDOLA_API_URL + "/home/getnow"
IDOLA_ARENA_PARTY_DETAILS = IDOLA_API_URL + "/ant/partydetails"
IDOLA_ARENA_EVENT_INFO = IDOLA_API_URL + "/ant/eventinfo"
IDOLA_ARENA_RANKING = IDOLA_API_URL + "/ant/ranking"
IDOLA_ARENA_RANKING_OFFSET = IDOLA_API_URL + "/ant/offsetranking"
IDOLA_RAID_EVENT_INFO = IDOLA_API_URL + "/raid/geteventinfo"
IDOLA_RAID_RANKING = IDOLA_API_URL + "/raid/ranking"
IDOLA_RAID_RANKING_OFFSET = IDOLA_API_URL + "/raid/offsetranking"


APP_VERSION = "1.11.1"  # Needs to be the latest version of IDOLA


def unpack(s):
    return ", ".join(map(str, s))


def braced_number(number):
    return "(" + str(number) + ")"


def lb_bullet(number):
    if number == 0:
        return "\u25CB\u25CB\u25CB\u25CB"
    elif number == 1:
        return "\u25CF\u25CB\u25CB\u25CB"
    elif number == 2:
        return "\u25CF\u25CF\u25CB\u25CB"
    elif number == 3:
        return "\u25CF\u25CF\u25CF\u25CB"
    elif number == 4:
        return "\u25CF\u25CF\u25CF\u25CF"
    else:
        number


class HTTPClient(object):
    USER_AGENT = (
        "Dalvik/2.1.0 (Linux; U; Android 5.1.1; Pixel XL Build/NOF26V)"  # android
    )

    def post(self, url, body={}):
        headers = {
            "Content-Type": "application/json",
            "User-Agent": self.USER_AGENT,
        }
        time.sleep(1)  # Fast requests return same message..
        response = requests.post(url, headers=headers, data=json.dumps(body))
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
    def __init__(self, auth_key):
        self.client = HTTPClient()
        self.auth_key = auth_key
        self.res_ver = RES_VER
        self.retrans_key = self.update_retrans_key()

        self.character_map = {}
        self.import_id_map(os.path.join("idola_id", "Character ID.csv"))
        self.import_id_map(os.path.join("idola_id", "Weapon ID.csv"))
        self.import_id_map(os.path.join("idola_id", "Soul ID.csv"))
        self.import_id_map(os.path.join("idola_id", "Idomag ID.csv"))

    def import_id_map(self, csv_filepath):
        with open(csv_filepath, newline="") as csvfile:
            char_csv = csv.reader(csvfile, delimiter=",")
            for row in char_csv:
                self.character_map[str(row[0])] = str(row[1])

    def get_name_from_id(self, char_id):
        for c_id in self.character_map:
            if str(char_id).startswith(c_id):
                return self.character_map[c_id]
        return "Unknown"

    def update_retrans_key(self):
        response = self.client.post(IDOLA_HOME_NOW)
        json_response = response.json()
        retrans_key = json_response["retrans_key"]
        print(f"Updating retrans_key: {retrans_key}")
        return retrans_key

    def get_latest_arena_event_id(self):
        body = {
            "app_ver": APP_VERSION,
            "res_ver": self.res_ver,
            "auth_key": self.auth_key,
            "retrans_key": self.retrans_key,
        }
        response = self.client.post(IDOLA_ARENA_EVENT_INFO, body)
        json_response = response.json()
        event_id = json_response["replace"]["ant_event_info"]["event_id"]
        self.retrans_key = json_response["retrans_key"]
        return event_id

    def get_arena_ranking_offset(self, event_id, offset=0):
        body = {
            "app_ver": APP_VERSION,
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
            "app_ver": APP_VERSION,
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
            "app_ver": APP_VERSION,
            "res_ver": self.res_ver,
            "auth_key": self.auth_key,
            "retrans_key": self.retrans_key,
            "is_tutorial": "false",
        }
        response = self.client.post(IDOLA_RAID_EVENT_INFO, body)
        json_response = response.json()
        event_id = json_response["replace"]["raid_event_info"]["event_id"]
        self.retrans_key = json_response["retrans_key"]
        return event_id

    def get_raid_battle_ranking(self, event_id=None, offset=0):
        if not event_id:
            event_id = self.get_latest_raid_event_id()
        body = {
            "app_ver": APP_VERSION,
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
        body = {
            "app_ver": APP_VERSION,
            "res_ver": self.res_ver,
            "auth_key": self.auth_key,
            "retrans_key": self.retrans_key,
            "idola_event_id": 62,
            "ranking_offset": offset,
            "ranking_type": 1,
        }
        response = self.client.post(IDOLA_RAID_RANKING_OFFSET, body)
        json_response = response.json()
        ranking_list = json_response["replace"]["creator_ranking"]
        self.retrans_key = json_response["retrans_key"]
        return ranking_list

    def show_arena_ranking_top_100_players(self, event_id=None):
        if not event_id:
            event_id = self.get_latest_arena_event_id()
        top_100_ranking_information = [
            self.get_arena_ranking_offset(event_id, 0),
            self.get_arena_ranking_offset(event_id, 20),
            self.get_arena_ranking_offset(event_id, 40),
            self.get_arena_ranking_offset(event_id, 60),
            self.get_arena_ranking_offset(event_id, 80),
        ]
        print("Idola Top 100 Arena Rankings")
        for ranking_information_intervals in top_100_ranking_information:
            for profile_id, ranking_information in sorted(
                ranking_information_intervals.items(),
                key=lambda item: item[1]["arena_score_rank"],
            ):
                name = ranking_information["name"]
                arena_score_rank = ranking_information["arena_score_rank"]
                arena_score_point = ranking_information["arena_score_point"]
                print(
                    f"{arena_score_rank}: {name}({profile_id}) - {arena_score_point:,d}"
                )

    def show_raid_suppression_top_100_players(self, event_id=None):
        if not event_id:
            event_id = self.get_latest_raid_event_id()
        top_100_ranking_information = [
            self.get_raid_battle_ranking(event_id, 0),
            self.get_raid_battle_ranking(event_id, 20),
            self.get_raid_battle_ranking(event_id, 40),
            self.get_raid_battle_ranking(event_id, 60),
            self.get_raid_battle_ranking(event_id, 80),
        ]

        print("Idola Top 100 Idola Suppression Rankings")
        prev_profile_id = None
        for ranking_information_intervals in top_100_ranking_information:
            for ranking_information in sorted(
                ranking_information_intervals, key=lambda item: item["score_rank"],
            ):
                name = ranking_information["friend_profile"]["name"]
                profile_id = ranking_information["friend_profile"]["profile_id"]
                if profile_id == prev_profile_id:
                    continue
                prev_profile_id = ranking_information["friend_profile"]["profile_id"]
                raid_score_rank = ranking_information["score_rank"]
                raid_score_point = ranking_information["score_point"]
                if raid_score_rank > 100:
                    break
                print(
                    f"{raid_score_rank}: {name}({profile_id}) - {raid_score_point:,d}"
                )

    def show_raid_creation_top_100_players(self, event_id=None):
        if not event_id:
            event_id = self.get_latest_raid_event_id()
        top_100_ranking_information = [
            self.get_raid_summon_ranking(event_id, 0),
            self.get_raid_summon_ranking(event_id, 20),
            self.get_raid_summon_ranking(event_id, 40),
            self.get_raid_summon_ranking(event_id, 60),
            self.get_raid_summon_ranking(event_id, 80),
        ]

        print("Idola Top 100 Idola Suppression Rankings")
        prev_profile_id = None
        for ranking_information_intervals in top_100_ranking_information:
            for ranking_information in sorted(
                ranking_information_intervals, key=lambda item: item["score_rank"],
            ):
                name = ranking_information["friend_profile"]["name"]
                profile_id = ranking_information["friend_profile"]["profile_id"]
                if profile_id == prev_profile_id:
                    continue
                prev_profile_id = ranking_information["friend_profile"]["profile_id"]
                raid_score_rank = ranking_information["score_rank"]
                raid_score_point = ranking_information["score_point"]
                if raid_score_rank > 100:
                    break
                print(
                    f"{raid_score_rank}: {name}({profile_id}) - {raid_score_point:,d}"
                )

    def show_top_100_arena_border(self, event_id=None):
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

        print(f"Top 100 Arena border is currently at {border_score_point:,d}")

    def show_top_100_raid_suppression_border(self, event_id=None):
        border_score_point = None
        event_id = self.get_latest_raid_event_id()
        ranking_information_81_100 = self.get_raid_battle_ranking(event_id, 80)
        for ranking_information in ranking_information_81_100:
            if ranking_information["score_rank"] == 100:
                border_score_point = ranking_information["score_point"]
                break

        if border_score_point is None:
            raise Exception("Could not find the Top 100 border score")

        print(
            f"Top 100 Idola Raid Supression border is currently at {border_score_point:,d}"
        )

    def show_top_100_raid_creator_border(self, event_id=None):
        border_score_point = None
        event_id = self.get_latest_raid_event_id()
        ranking_information_81_100 = self.get_raid_summon_ranking(event_id, 80)
        for ranking_information in ranking_information_81_100:
            if ranking_information["score_rank"] == 100:
                border_score_point = ranking_information["score_point"]
                break

        if border_score_point is None:
            raise Exception("Could not find the Top 100 border score")

        print(
            f"Top 100 Idola Raid Summon border is currently at {border_score_point:,d}"
        )

    @staticmethod
    def destiny_bonus(level, status):
        if status == 0:
            return "NA"
        else:
            return level

    def show_arena_team_composition(self, profile_id):
        party_info = self.get_arena_party_info(profile_id)
        name = party_info["player_name"]
        arena_team_score = party_info["strength_value"]

        law_char_names = [
            self.get_name_from_id(character["character"]["char_id"])
            + " "
            + lb_bullet(character["character"]["potential"])
            + braced_number(
                self.destiny_bonus(
                    character["destiny_bonus_level"], character["destiny_bonus_status"]
                )
            )
            for character in party_info["law"]
        ]
        law_wep_names = [
            self.get_name_from_id(character["weapon_symbol"]["symbol_id"])
            + " LV"
            + str(character["weapon_symbol"]["level"])
            for character in party_info["law"]
        ]
        law_soul_names = [
            self.get_name_from_id(character["soul_symbol"]["symbol_id"])
            + " LV"
            + str(character["soul_symbol"]["level"])
            for character in party_info["law"]
        ]
        law_idomag_type = self.get_name_from_id(
            party_info["law_idomag"]["idomag_type_id"]
        )
        law_idomag_name = party_info["law_idomag"]["name"]

        chaos_char_names = [
            self.get_name_from_id(character["character"]["char_id"])
            + " "
            + lb_bullet(character["character"]["potential"])
            + braced_number(
                self.destiny_bonus(
                    character["destiny_bonus_level"], character["destiny_bonus_status"]
                )
            )
            for character in party_info["chaos"]
        ]
        chaos_wep_names = [
            self.get_name_from_id(character["weapon_symbol"]["symbol_id"])
            + " LV"
            + str(character["weapon_symbol"]["level"])
            for character in party_info["chaos"]
        ]
        chaos_soul_names = [
            self.get_name_from_id(character["soul_symbol"]["symbol_id"])
            + " LV"
            + str(character["soul_symbol"]["level"])
            for character in party_info["chaos"]
        ]
        chaos_idomag_type = self.get_name_from_id(
            party_info["chaos_idomag"]["idomag_type_id"]
        )
        chaos_idomag_name = party_info["chaos_idomag"]["name"]

        print(f"== Arena Team ==")
        print(f"Player Name: {name}")
        print(f"Team Score: {arena_team_score:,d}")
        print(f"Law Characters: {unpack(law_char_names)}")
        print(f"Law Weapon Symbol: {unpack(law_wep_names)}")
        print(f"Law Soul Symbol: {unpack(law_soul_names)}")
        print(f"Law Idomag: {law_idomag_type}({law_idomag_name})")
        print(f"Chaos Characters: {unpack(chaos_char_names)}")
        print(f"Chaos Weapon Symbol: {unpack(chaos_wep_names)}")
        print(f"Chaos Soul Symbol: {unpack(chaos_soul_names)}")
        print(f"Chaos Idomag: {chaos_idomag_type}({chaos_idomag_name})")


def main():
    idola = IdolaAPI(auth_key=AUTH_KEY)
    idola.show_arena_ranking_top_100_players()
    idola.show_raid_suppression_top_100_players()
    idola.show_raid_creation_top_100_players()
    idola.show_top_100_arena_border()
    idola.show_top_100_raid_suppression_border()
    idola.show_top_100_raid_creator_border()
    idola.show_arena_team_composition(profile_id=186534332)


if __name__ == "__main__":
    sys.exit(main())
