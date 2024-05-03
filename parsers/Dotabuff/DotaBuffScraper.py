import random
import sys

import requests
from bs4 import BeautifulSoup
import time
import re
from enum import Enum
from datetime import datetime
from dateutil.relativedelta import relativedelta
import json
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.common.exceptions import WebDriverException
from dataclasses import dataclass
from colorama import Fore, Style
import sqlite3
import socket
from collections import deque
from fake_useragent import UserAgent


@dataclass
class DayActivityStats:
    activity_date: datetime
    matches_won: int
    matches_lost: int


class MatchQueue:
    def __init__(self, q_id, match_link, is_assigned, agent):
        self.id = q_id
        self.agent = agent
        self.is_assigned = is_assigned
        self.match_link = match_link


def get_gaming_activity_as_day_activity_stats_list(year_activity_days):
    year_activity_days_parsed = []

    for day_el in year_activity_days:
        activity_matches_results_list = day_el.find_all('span')

        activity_date = datetime.strptime(day_el.find('h3').text, '%Y-%m-%d')
        activity_matches_won = int(activity_matches_results_list[0].text)
        activity_matches_lost = int(activity_matches_results_list[-1].text)

        year_activity_days_parsed.append(
            DayActivityStats(activity_date, activity_matches_won, activity_matches_lost))

    return year_activity_days_parsed


class Player:
    def __init__(self, player_link, player_id, main_match_page, main_match_datetime, main_match_id):
        # Main Match
        self._main_match_page = main_match_page
        self._main_match_datetime = main_match_datetime
        self._main_match_id = main_match_id

        # Heroes Meta Page
        self._hero_winrate_overall = None
        self._hero_pickrate_overall = None
        self._hero_winrate_for_rank = None
        self._hero_pickrate_for_rank = None

        # Player Matches Page
        self._player_q_predicted_mmr = None

        # Player Heroes Page
        self._player_hero_kda_ratio_overall = None
        self._player_hero_winrate_overall = None
        self._player_hero_total_matches_played = None

        # Player Stats Page
        self._dire_time_played = None
        self._dire_winrate_all_time = None
        self._dire_games_played_all_time = None
        self._radiant_time_played = None
        self._radiant_winrate_all_time = None
        self._radiant_games_played_all_time = None
        self._player_time_played_all_matches = None
        self._player_winrate_over_time_stats_page = None
        self._all_matches_played_number = None

        ###
        self._player_nickname = None
        self._player_matches_abandoned = None
        self._player_matches_lost = None
        self._player_matches_won = None
        self._player_winrate_over_time = None
        self._player_rank_initial = None
        self._player_sentries = None
        self._player_observers = None
        self._player_building_dmg_dealt = None
        self._player_heal = None
        self._player_damage_dealt = None
        self._player_xpm = None
        self._player_gpm = None
        self._player_denies = None
        self._player_lasthits = None
        self._player_net = None
        self._player_assists_number = None
        self._player_deaths_number = None
        self._player_kills_number = None
        self._player_lane_result = None
        self._player_lane_option2 = None
        self._player_lane = None
        self._player_role = None
        self._hero_lvl = None
        self._hero_name = None
        self._hero_link = None
        self._player_link = player_link
        self._player_id = player_id
        self._visibility_status = PlayerStatus.UNKNOWN.name

        # Player activity

        self._week_matches_played = None
        self._week_matches_won = None
        self._week_winrate = None
        self._week_days_active = None
        self._week_activity_coef = None

        self._month_matches_played = None
        self._month_matches_won = None
        self._month_winrate = None
        self._month_days_active = None
        self._month_activity_coef = None

        # Player pages
        self._player_main_page_soup = None
        self._player_matches_page_soup = None
        self._player_stats_page_soup = None
        self._player_heroes_stats_page = None

        self._player_side = None

        self.__get_player_main_page()

        self.__set_player_status()
        self.__parse_player_stats_from_main_page()
        self.__parse_player_game_stats()
        self.__parse_player_hero_winrate_overall_from_meta_page()

        if self._visibility_status == PlayerStatus.VISIBLE.name:
            self.__get_player_stats_page()

            self.__get_player_matches_page()
            self.__get_player_heroes_stats_page()
            self.__parse_player_stats_from_stats_page()
            self.__parse_player_hero_stats()
            self.__parse_player_month_to_date_matches_stats_from_matches_page()
            self.__parse_player_gaming_activity_from_activity_page_performance_enhanced()

            self.__update_db_queue()

        self.__dump_all_data()

    @staticmethod
    def __get_matches_table_and_object_list(player_matches_page_arg):
        matches_list_table = player_matches_page_arg.find('div', class_='content-inner').find('table').find(
            'tbody')
        return matches_list_table, matches_list_table.find_all('tr', class_=False)

    @staticmethod
    def __extract_match_datetime_value(match_obj):
        return convert_str_to_datetime(match_obj.find('time').get('datetime'))

    def __get_last_available_match_datetime(self, player_matches_page_arg):
        _, match_object_list_temp = self.__get_matches_table_and_object_list(player_matches_page_arg)

        return self.__extract_match_datetime_value(match_object_list_temp[-1])

    def __parse_player_gaming_activity_from_activity_page_performance_enhanced(self):
        def get_processed_activity_data_by_activity_list(activity_data_list):
            total_games_played = 0
            total_games_won = 0
            days_with_games = []

            for activity in activity_data_list:
                games_played = activity.matches_won + activity.matches_lost

                total_games_played += games_played
                total_games_won += activity.matches_won

                if games_played > 0:
                    days_with_games.append(activity.activity_date.date())

            winrate = total_games_won / total_games_played if total_games_played > 0 else 0
            num_days_with_games = len(days_with_games)
            activity_consistency_coef = num_days_with_games / len(activity_data_list)

            return total_games_played, total_games_won, winrate, num_days_with_games, activity_consistency_coef

        player_activity_page = self.__get_player_activity_page_soup()

        year_2024_to_date_activity_table = player_activity_page.find('div', class_='player-activity-wrapper') \
            .find_all('div', class_='year-chart')[-1]

        year_activity_days = year_2024_to_date_activity_table.find_all('div', class_='year-chart-tooltip')

        year_activity_days_parsed_list = get_gaming_activity_as_day_activity_stats_list(year_activity_days)

        week_summary_end_datetime = self._main_match_datetime - relativedelta(weeks=1)
        month_summary_end_datetime = self._main_match_datetime - relativedelta(months=1)

        current_match_datetime_global_date = self._main_match_datetime.date()

        week_activity_list = []
        month_activity_list = []

        for day_activity_stats in year_activity_days_parsed_list:
            activity_date = day_activity_stats.activity_date.date()

            # Check if the activity date falls within the week summary range
            if week_summary_end_datetime.date() <= activity_date < current_match_datetime_global_date:
                week_activity_list.append(day_activity_stats)

            # Check if the activity date falls within the month summary range
            if month_summary_end_datetime.date() <= activity_date < current_match_datetime_global_date:
                month_activity_list.append(day_activity_stats)

        week_matches_played, week_matches_won, week_winrate, week_days_active, week_activity_q = \
            get_processed_activity_data_by_activity_list(week_activity_list)

        month_matches_played, month_matches_won, month_winrate, month_days_active, month_activity_q = \
            get_processed_activity_data_by_activity_list(month_activity_list)

        self._week_matches_played = week_matches_played
        self._week_matches_won = week_matches_won
        self._week_winrate = week_winrate
        self._week_days_active = week_days_active
        self._week_activity_coef = week_activity_q

        self._month_matches_played = month_matches_played
        self._month_matches_won = month_matches_won
        self._month_winrate = month_winrate
        self._month_days_active = month_days_active
        self._month_activity_coef = month_activity_q

        # obsolete
    def __parse_player_gaming_activity_from_activity_page(self):
        player_activity_page, player_activity_page_selenium_driver = \
            self.__get_player_activity_page_soup_and_selenium_driver()

        year_2024_to_date_activity_table = player_activity_page.find('div', class_='player-activity-wrapper') \
                                                                .find_all('div', class_='year-chart')[-1]

        year_to_date_activity_columns = year_2024_to_date_activity_table.find_all('div', class_='col')
        year_activity_days = []

        for col in year_to_date_activity_columns:
            for el in col.find_all('div', class_=lambda x: x and 'day matches-' in x):
                year_activity_days.append(el)

        data_hasqtip_values = [x.get('data-hasqtip') for x in year_activity_days]
        year_activity_days_selenium = []

        for hasqtip in data_hasqtip_values:
            xpath = f"//div[@data-hasqtip='{hasqtip}']"

            div_element = player_activity_page_selenium_driver.find_element(By.XPATH, xpath)
            year_activity_days_selenium.append(div_element)

        for el in year_activity_days_selenium:
            ActionChains(player_activity_page_selenium_driver).move_to_element(el).perform()

        player_activity_page = BeautifulSoup(player_activity_page_selenium_driver.page_source, 'html.parser')

        player_activity_by_day_elements = []

        for hp in data_hasqtip_values:
            player_activity_by_day_elements.append(player_activity_page.find('div', id=f'ui-tooltip-{hp}-content'))

        player_activity_stats_list = get_gaming_activity_as_day_activity_stats_list(player_activity_by_day_elements)

        player_activity_page_selenium_driver.quit()

    def __update_db_queue(self):
        matches_to_queue = self.__parse_player_month_played_matches_to_update_the_agent_queues()

        if matches_to_queue:
            _ = db_watcher_global.upload_queue_assignments(matches_to_queue)

    def __parse_player_month_played_matches_to_update_the_agent_queues(self):
        month_summary_end_date = self._main_match_datetime - relativedelta(weeks=2)
        last_available_match_datetime = self.__get_last_available_match_datetime(self._player_matches_page_soup)
        _, match_objs = self.__get_matches_table_and_object_list(self._player_matches_page_soup)

        if last_available_match_datetime >= month_summary_end_date:  # just take all matches
            return [get_root_link() + tr.find_all('td')[1]
                 .find('a', href=lambda href: href and href.startswith('/matches/'))
                 .get('href')
                 for tr in match_objs][:10]  # taking first 10 results to decrease the number of GET requests in future
        else:
            match_queue_list = []
            for match in match_objs:
                if self.__extract_match_datetime_value(match) >= month_summary_end_date:
                    match_queue_list.append(get_root_link() + match
                                            .find('a', href=lambda href: href and href.startswith('/matches/'))
                                            .get('href'))

            return match_queue_list[:10]  # taking first 10 results to decrease the number of GET requests in future

    def __parse_player_month_to_date_matches_stats_from_matches_page(self):
        def try_parse_player_q_mmr(init_index, match_object_list, month_summary_end_date):
            for idx in range(init_index, len(match_object_list)):
                current_match_to_parse = match_object_list[idx]
                current_match_to_parse_elements = current_match_to_parse.find_all('td')

                current_match_predicted_rank = current_match_to_parse_elements[1].find('div', class_='subtext').text

                if current_match_predicted_rank in ranks_to_mmr_dict_global:  # if overall match_info is present
                    current_match_summary_box = current_match_to_parse_elements[3]
                    # current_match_outcome = current_match_summary_box.find('a').text[:-6]  # Won/Lost
                    current_match_datetime = self.__extract_match_datetime_value(current_match_summary_box)

                    if current_match_datetime > month_summary_end_date:
                        if len(matches_predicted_mmrs_list) < global_mmr_coefficient:
                            matches_predicted_mmrs_list.append(convert_rank_to_mmr(current_match_predicted_rank))
                        else:
                            self._player_q_predicted_mmr = sum(matches_predicted_mmrs_list) / len(
                                matches_predicted_mmrs_list)
                            break
                    else:
                        break

        player_matches_page = self._player_matches_page_soup
        curr_page_number = 1

        # No way
        if self.__get_last_available_match_datetime(player_matches_page) > self._main_match_datetime:
            player_matches_page, curr_page_number = self.__get_player_matches_next_page(curr_page_number)

        # No way x2
        if self.__get_last_available_match_datetime(player_matches_page) > self._main_match_datetime:
            player_matches_page, curr_page_number = self.__get_player_matches_next_page(curr_page_number)

        # No way x3
        if self.__get_last_available_match_datetime(player_matches_page) > self._main_match_datetime:
            player_matches_page, curr_page_number = self.__get_player_matches_next_page(curr_page_number)

        # Might as well buy a lottery ticket or something
        if self.__get_last_available_match_datetime(player_matches_page) > self._main_match_datetime:
            raise Exception('The match requested was played during the Ancient Rome Era')

        matches_table, match_object_list = self.__get_matches_table_and_object_list(player_matches_page)
        target_start_match = matches_table.find('a', href=f'/matches/{self._main_match_id}').find_parent('tr')

        init_index = match_object_list.index(target_start_match)

        # Here starts the parsing

        month_summary_end_date = self._main_match_datetime - relativedelta(months=1)
        matches_predicted_mmrs_list = []

        try_parse_player_q_mmr(init_index=init_index, match_object_list=match_object_list,
                               month_summary_end_date=month_summary_end_date)

        if self._player_q_predicted_mmr is None:
            player_matches_page, curr_page_number = self.__get_player_matches_next_page(curr_page_number)
            matches_table, match_object_list = self.__get_matches_table_and_object_list(player_matches_page)

            try_parse_player_q_mmr(init_index=0, match_object_list=match_object_list,
                                   month_summary_end_date=month_summary_end_date)

    def __get_player_matches_next_page(self, current_page_number):
        new_page_number = current_page_number + 1
        next_page = request_manager_global.make_request_to_page_with_retries(
            self._player_link + f'/matches?enhance=overview&page={new_page_number}')

        return BeautifulSoup(next_page, 'html.parser'), new_page_number

    def __parse_player_hero_stats(self):
        self.__parse_player_hero_stats_from_heroes_page()

    def __parse_player_hero_winrate_overall_from_meta_page(self):
        def get_td_group_index(p_mmr):
            if p_mmr < 2100:
                return 1
            elif 2100 <= p_mmr < 3000:
                return 2
            elif 3000 <= p_mmr < 3900:
                return 3
            elif 3900 <= p_mmr < 4800:
                return 4
            elif p_mmr >= 4800:
                return 5
            else:
                return -1

        player_heroes_meta_page = heroes_meta_page_soup_global

        heroes_meta_table = player_heroes_meta_page.find('div', class_='content-inner').find('tbody')
        player_hero_a_tag = heroes_meta_table.find('a', href=self._hero_link, class_='link-type-hero')
        player_hero_box = player_hero_a_tag.find_parent('tr')

        if self._player_q_predicted_mmr:
            group_index = get_td_group_index(self._player_q_predicted_mmr)
        elif self._player_rank_initial:
            group_index = get_td_group_index(convert_rank_to_mmr(self._player_rank_initial))
        else:
            group_index = -1

        if group_index != -1:
            hero_winrate_pickrate_stats_list = player_hero_box.find_all('td',
                                                        class_=lambda x: x and f'r-tab r-group-{group_index}' in x)

            hero_pickrate_for_rank = re.search(r'\d+', hero_winrate_pickrate_stats_list[0].text).group()
            hero_winrate_for_rank = re.search(r'\d+', hero_winrate_pickrate_stats_list[1].text).group()

            self._hero_pickrate_for_rank = float(hero_pickrate_for_rank)
            self._hero_winrate_for_rank = float(hero_winrate_for_rank)

        hero_winrate_pickrate_stats_list_all = player_hero_box.find_all('td')[2:]
        hero_pickrate_overall, hero_winrate_overall = 0., 0.

        pr_idxs = [0, 2, 4, 6, 8]
        wr_idxs = [1, 3, 5, 7, 9]

        for idx in pr_idxs:
            hero_pickrate_overall += float(hero_winrate_pickrate_stats_list_all[idx].get('data-value'))

        for idx in wr_idxs:
            hero_winrate_overall += float(hero_winrate_pickrate_stats_list_all[idx].get('data-value'))

        hero_pickrate_overall /= len(pr_idxs)
        hero_winrate_overall /= len(wr_idxs)

        self._hero_pickrate_overall = hero_pickrate_overall
        self._hero_winrate_overall = hero_winrate_overall

    def __parse_player_hero_stats_from_heroes_page(self):
        all_heroes_table = self._player_heroes_stats_page.find('table', class_='sortable').find('tbody')

        player_hero_element = all_heroes_table.find('a', string=self._hero_name)

        hero_stats_table_row = player_hero_element.find_parent('tr')
        hero_stats_table_row_columns = hero_stats_table_row.find_all('td')

        self._player_hero_total_matches_played = int(hero_stats_table_row_columns[2].text)
        self._player_hero_winrate_overall = float(hero_stats_table_row_columns[3].text[:-1])
        self._player_hero_kda_ratio_overall = float(hero_stats_table_row_columns[4].text)

    def __parse_player_stats_from_stats_page(self):
        all_stats_table = self._player_stats_page_soup.find('div', class_='content-inner').find('table')

        all_table_parts = all_stats_table.find_all('tbody')

        lifetime_stats_table = all_table_parts[0]
        all_matches_stats_row = lifetime_stats_table.find_all('tr')[0]

        all_matches_stats_row_columns = all_matches_stats_row.find_all('td')

        self._all_matches_played_number = int(all_matches_stats_row_columns[1].text)
        self._player_winrate_over_time_stats_page = float(all_matches_stats_row_columns[2].text[:-1])
        self._player_time_played_all_matches = int(all_matches_stats_row_columns[3].text)

        ###
        lifetime_sides_stats_table = all_table_parts[3]
        radiant_dire_rows = lifetime_sides_stats_table.find_all('tr')

        radiant_row = radiant_dire_rows[0]
        radiant_row_columns = radiant_row.find_all('td')

        self._radiant_games_played_all_time = int(radiant_row_columns[1].text)
        self._radiant_winrate_all_time = float(radiant_row_columns[2].text[:-1])
        self._radiant_time_played = radiant_row_columns[3].text

        ###
        dire_row = radiant_dire_rows[1]
        dire_row_columns = dire_row.find_all('td')

        self._dire_games_played_all_time = int(dire_row_columns[1].text)
        self._dire_winrate_all_time = float(dire_row_columns[2].text[:-1])
        self._dire_time_played = dire_row_columns[3].text

    def __get_player_activity_page_soup_and_selenium_driver(self):
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')

        driver = webdriver.Chrome(options=options)
        driver.get(self._player_link + '/activity')

        player_activity_page = BeautifulSoup(driver.page_source, 'html.parser')
        player_activity_page_selenium_driver = driver

        return player_activity_page, player_activity_page_selenium_driver

    def __get_player_activity_page_soup(self):
        player_activity_page = request_manager_global.make_request_to_page_with_retries(self._player_link + '/activity')

        return BeautifulSoup(player_activity_page, 'html.parser')

    def __get_player_main_page(self):
        player_main_page = request_manager_global.make_request_to_page_with_retries(self._player_link)

        self._player_main_page_soup = BeautifulSoup(player_main_page, 'html.parser')

    def __get_player_matches_page(self):
        player_matches_page = request_manager_global.make_request_to_page_with_retries(self._player_link + '/matches')
        self._player_matches_page_soup = BeautifulSoup(player_matches_page, 'html.parser')

    def __get_player_stats_page(self):
        player_stats_page = request_manager_global.make_request_to_page_with_retries(self._player_link + '/scenarios')
        self._player_stats_page_soup = BeautifulSoup(player_stats_page, 'html.parser')

    def __get_player_heroes_stats_page(self):
        player_heroes_stats_page = request_manager_global.make_request_to_page_with_retries(
            self._player_link + '/heroes?game_mode=all_pick&metric=played')
        self._player_heroes_stats_page = BeautifulSoup(player_heroes_stats_page, 'html.parser')

    def __set_player_status(self):
        if self._player_main_page_soup.find('div', class_='page-show'):
            self._visibility_status = PlayerStatus.HIDDEN.name
        else:
            self._visibility_status = PlayerStatus.VISIBLE.name

        print_notification(f'PLayer_VisibilityStatus: {self._visibility_status}')

    def __parse_player_stats_from_main_page(self):
        player_nickname_box = (self._player_main_page_soup.find('div', class_='header-content-primary')
                                                         .find('div', class_='header-content-title'))

        self._player_nickname = player_nickname_box.find('h1').text

        player_stats_row = self._player_main_page_soup.find('div', class_='header-content-secondary')

        player_rank_element = player_stats_row.find('div', class_='rank-tier-wrapper')
        self._player_rank_initial = player_rank_element.get('title')[len('Rank '):]

        if self._player_rank_initial[0] == ' ':
            self._player_rank_initial = self._player_rank_initial[1:]

        player_stats_row_important = player_stats_row.find_all('dl')

        self._player_winrate_over_time = float(player_stats_row_important[2].find('dd').text[:-1])

        match_record_element = player_stats_row_important[1].find('dd')

        self._player_matches_won = match_record_element.find('span', class_='wins').text
        self._player_matches_lost = match_record_element.find('span', class_='losses').text
        self._player_matches_abandoned = match_record_element.find('span', class_='abandons').text

    def __parse_player_game_stats(self):
        player_table_row = self._main_match_page.find('tr', class_=lambda c: c and (
                'faction-radiant' in c or 'faction-dire' in c) and self._player_id in c)

        if 'faction-radiant' in player_table_row.get('class'):
            self._player_side = PlayerSide.RADIANT.name
        elif 'faction-dire' in player_table_row.get('class'):
            self._player_side = PlayerSide.DIRE.name

        # print(f'PlayerSide: {self._player_side}')

        hero_tag = player_table_row.find('a', href=lambda href: href and href.startswith('/heroes/'))

        self._hero_link = hero_tag.get('href')

        ###
        self._hero_name = hero_tag.find('img').get('title')
        # print(f'PlayerHeroName: {self._hero_name}')
        ###
        self._hero_lvl = int(hero_tag.find('span').text)
        # print(f'Hero lvl: {self._hero_lvl}')

        player_table_column_elements = player_table_row.find_all('td')  # all columns to parse by order

        ###
        player_role_element = player_table_column_elements[1]
        self._player_role = player_role_element.find('i').get('title')
        # print(f'playerRole: {self._player_role}')

        ###
        player_lane_element = player_table_column_elements[2]
        self._player_lane = player_lane_element.find('i').get('title')
        # print(f'PlayerLane: {self._player_lane}')

        ###
        player_lane_result_element = player_table_column_elements[3].find('div')
        self._player_lane_option2 = player_lane_result_element.find('span', class_='player-lane-text').find('acronym').text
        # print(f'PlayerLane2: {self._player_lane_option2}')

        self._player_lane_result = player_lane_result_element.find('acronym', class_='lane-outcome').text
        # print(f'PLayerLaneOutcome: {self._player_lane_result}')

        ###
        player_kills_number_element = player_table_column_elements[5]
        self._player_kills_number = parse_table_column_td_text(player_kills_number_element)
        # print(f'PlayerKills: {self._player_kills_number}')

        ###
        player_deaths_number_element = player_table_column_elements[6]
        self._player_deaths_number = parse_table_column_td_text(player_deaths_number_element)

        # print(f'PlayerDeaths: {self._player_deaths_number}')

        ###
        player_assists_number_element = player_table_column_elements[7]
        self._player_assists_number = parse_table_column_td_text(player_assists_number_element)

        # print(f'PlayerAssists: {self._player_assists_number}')

        ###
        player_net_element = player_table_column_elements[8]
        self._player_net = parse_table_column_td_text(player_net_element.find('acronym'))

        # print(f'PlayerNETWorth: {self._player_net}')

        ###
        player_lasthits_element = player_table_column_elements[9]
        self._player_lasthits = parse_table_column_td_text(player_lasthits_element)

        # print(f'PlayerLastHits: {self._player_lasthits}')

        ###
        player_denies_element = player_table_column_elements[11]
        self._player_denies = parse_table_column_td_text(player_denies_element)

        # print(f'PlayerDenies: {self._player_denies}')

        ###
        player_gpm_element = player_table_column_elements[12]
        self._player_gpm = parse_table_column_td_text(player_gpm_element)

        # print(f'PlayerGPM: {self._player_gpm}')

        ###
        player_xpm_element = player_table_column_elements[14]
        self._player_xpm = parse_table_column_td_text(player_xpm_element)

        # print(f'PlayerXPM: {self._player_xpm}')

        ###
        player_damage_dealt_element = player_table_column_elements[15]
        self._player_damage_dealt = parse_table_column_td_text(player_damage_dealt_element)

        # print(f'PlayerDMGDealt: {self._player_damage_dealt}')

        ###
        player_heal_element = player_table_column_elements[16]
        self._player_heal = parse_table_column_td_text(player_heal_element)

        # print(f'PlayerHeal: {self._player_heal}')

        ###
        player_building_dmg_dealt_element = player_table_column_elements[17]
        self._player_building_dmg_dealt = parse_table_column_td_text(player_building_dmg_dealt_element)

        # print(f'PlayerBuildingDMGDealt: {self._player_building_dmg_dealt}')

        ###
        player_observer_wards_element = player_table_column_elements[18].find('span', class_='color-item-observer-ward')
        self._player_observers = parse_table_column_td_text(player_observer_wards_element)

        # print(f'PlayerObservers: {self._player_observers}')

        ###
        player_sentry_wards_element = player_table_column_elements[18].find('span', class_='color-item-sentry-ward')
        self._player_sentries = parse_table_column_td_text(player_sentry_wards_element)

        # print(f'PlayerSentries: {self._player_sentries}')

    def __dump_all_data(self):
        data_to_add = {
            'player_id': self._player_id,
            'match_id': self._main_match_id,
            'hero_winrate_overall': self._hero_winrate_overall,  # NOT NULL
            'hero_pickrate_overall': self._hero_pickrate_overall,  # NOT NULL
            'hero_winrate_for_rank': self._hero_winrate_for_rank,
            'hero_pickrate_for_rank': self._hero_pickrate_for_rank,
            'player_q_predicted_mmr': self._player_q_predicted_mmr,
            'player_hero_kda_ratio_overall': self._player_hero_kda_ratio_overall,
            'player_hero_winrate_overall': self._player_hero_winrate_overall,
            'player_hero_total_matches_played': self._player_hero_total_matches_played,
            'dire_time_played': self._dire_time_played,
            'dire_winrate_all_time': self._dire_winrate_all_time,
            'dire_games_played_all_time': self._dire_games_played_all_time,
            'radiant_time_played': self._radiant_time_played,
            'radiant_winrate_all_time': self._radiant_winrate_all_time,
            'radiant_games_played_all_time': self._radiant_games_played_all_time,
            'player_time_played_all_matches': self._player_time_played_all_matches,
            'player_winrate_over_time_stats_page': self._player_winrate_over_time_stats_page,
            'player_all_matches_played_number': self._all_matches_played_number,
            'player_nickname': self._player_nickname,
            'player_matches_abandoned': self._player_matches_abandoned,
            'player_matches_lost': self._player_matches_lost,
            'player_matches_won': self._player_matches_won,
            'player_winrate_over_time_main_page': self._player_winrate_over_time,  # NOT NULL
            'player_match_rank_initial': self._player_rank_initial,
            'player_sentries': self._player_sentries,
            'player_observers': self._player_observers,
            'player_building_dmg_dealt': self._player_building_dmg_dealt,
            'player_heal': self._player_heal,
            'player_damage_dealt': self._player_damage_dealt,
            'player_xpm': self._player_xpm,
            'player_gpm': self._player_gpm,
            'player_denies': self._player_denies,
            'player_lasthits': self._player_lasthits,
            'player_net': self._player_net,
            'player_assists_number': self._player_assists_number,
            'player_deaths_number': self._player_deaths_number,
            'player_kills_number': self._player_kills_number,
            'player_lane_result': self._player_lane_result,
            'player_lane_option2': self._player_lane_option2,
            'player_lane': self._player_lane,
            'player_role': self._player_role,
            'hero_lvl': self._hero_lvl,
            'player_side': self._player_side,
            'week_matches_played': self._week_matches_played,
            'week_matches_won': self._week_matches_won,
            'week_winrate': self._week_winrate,
            'week_days_active': self._week_days_active,
            'week_activity_coef': self._week_activity_coef,
            'month_matches_played': self._month_matches_played,
            'month_matches_won': self._month_matches_won,
            'month_winrate': self._month_winrate,
            'month_days_active': self._month_days_active,
            'month_activity_coef': self._month_activity_coef,
        }

        if not db_watcher_global.dump_all_parsed_records(self._hero_link, self._hero_name,
                                                  self._player_link, self._visibility_status, data_to_add):
            print_error('Player processing failed...')
            global_await_exit_action()


class Match:
    def __init__(self, match_link):
        self._match_id = match_link.split('/')[-1]
        self._match_link = match_link
        self._match_datetime = None
        self._match_result = None
        self._match_duration = None
        self._radiant_score = None
        self._dire_score = None
        self._main_match_page = None

    def __add_match_to_database(self):
        res = db_watcher_global.add_match(self._match_id, self._match_link, self._match_datetime, self._match_result,
                                    self._match_duration, self._radiant_score, self._dire_score)

        return res

    def __set_match_page_object(self):
        if not self._main_match_page:
            main_match_page = request_manager_global.make_request_to_page_with_retries(self._match_link)

            print(f'Selenium res2: {main_match_page}')

            # TODO remove
            sys.exit()

            self._main_match_page = BeautifulSoup(main_match_page, 'html.parser')

    def __parse_main_match_fields(self):
        datetime_block = self._main_match_page.find('div', class_='header-content-secondary')
        match_datetime_parsed = datetime_block.find_all('dl')[-1].find('time').get('datetime')

        self._match_datetime = convert_str_to_datetime(match_datetime_parsed)

        ###
        self._match_result = self._main_match_page.find('div', class_='match-result').text

        ###
        match_results_block = self._main_match_page.find('div', class_='match-victory-subtitle')
        self._radiant_score = int(match_results_block.find('span', class_='the-radiant score').text)
        self._dire_score = int(match_results_block.find('span', class_='the-dire score').text)
        self._match_duration = match_results_block.find('span', class_='duration').text

    def __parse_player_links_as_objects(self):
        return self._main_match_page.find_all('a', class_=re.compile(r'\blink-type-player\b'))

    def __parse_player_links(self):
        return [f'https://www.dotabuff.com{link["href"]}' for link in self.__parse_player_links_as_objects()]

    def process_match(self):
        self.__set_match_page_object()
        self.__parse_main_match_fields()

        if not self.__add_match_to_database():
            return None

        player_links = self.__parse_player_links()

        if len(player_links) < 10:
            print_warning(f'Match {self._match_link} is skipped. Anonymous players found')
            return False

        player_links_objs = self.__parse_player_links_as_objects()

        player_ids = [f'player-{parse_player_id(pl)}' for pl in player_links_objs]

        player_links_ids = [[player_id, player_link] for player_id, player_link in zip(player_ids, player_links)]

        match_players_list = []

        # TODO finalize

        its = 0
        for player_id, player_link in player_links_ids:
            its += 1

            if its != 1:
                match_players_list.append(
                    Player(player_link, player_id, self._main_match_page, self._match_datetime, self._match_id))

                time.sleep(1)

                break


def print_warning(message):
    print(f'{Fore.YELLOW} {message} {Style.RESET_ALL}')


def print_error(message):
    print(f'{Fore.RED} {message} {Style.RESET_ALL}')


def print_notification(message):
    print(f'\n{Fore.CYAN} {message} {Style.RESET_ALL}\n')


def get_root_link():
    return 'https://www.dotabuff.com'


class DatabaseWatcher:
    def __init__(self, database_path):
        self._database_path = database_path
        self._operation_lock_time = 2

        self._connection = None
        self._cursor = None

        self.agent_name = socket.gethostname()

        self.__open_database_connection()

    def dispose(self):
        self.__close_existing_connection()

    def __close_existing_connection(self):
        if self._cursor:
            self._cursor.close()

        if self._connection:
            self._connection.close()

    def __refresh_connection_cursor(self):
        self._cursor = self._connection.cursor()

    def __open_database_connection(self):
        self._connection = sqlite3.connect(self._database_path)
        self.__refresh_connection_cursor()

    def __try_execute_query(self, query, params, is_readonly, is_execute_many=False, allow_commit=True):
        try:
            res = [True, None]

            if params:
                if is_execute_many:
                    self._cursor.executemany(query, params)
                else:
                    self._cursor.execute(query, params)
            else:
                self._cursor.execute(query)

            if is_readonly:
                res = [self._cursor.fetchall(), None]
            elif not is_readonly and allow_commit:
                self._connection.commit()

        except sqlite3.Error as e:
            res = [False, e]

        return res[0], res[1]

    def __try_perform_operation_with_retries(self, operation_name, operation_pointer, retry_count=5, *args, **kwargs):
        retries = 0
        err = None

        while retries < retry_count:
            try:
                res, err = operation_pointer(*args, **kwargs)

                if isinstance(res, list):
                    if len(res) == 0:
                        return res, err

                if res:
                    return res, err
                else:
                    raise Exception(err)
            except Exception as e:
                print_warning(f'Run into exception: {e}. Retries: {retries+1}/{retry_count}')

                time.sleep(self._operation_lock_time)
                retries += 1

                err = e

        print_error(f'The operation {operation_name} failed after retries.')

        return False, err

    def __try_update_queue_assignments(self, q_limit):
        try:
            self.__refresh_connection_cursor()
            self._cursor.execute('BEGIN EXCLUSIVE')

            self._cursor.execute('SELECT id FROM match_queue WHERE is_assigned = ? LIMIT ?', (False, q_limit))
            rows = self._cursor.fetchall()

            ids = [row[0] for row in rows]

            self._cursor.execute(
                'UPDATE match_queue SET is_assigned = ?, agent = ? WHERE id IN ({})'.format(','.join('?' * len(ids))),
                [True, self.agent_name] + ids)

            self._connection.commit()
            self._cursor.execute('COMMIT')

            return True, None
        except sqlite3.Error as e:
            error = e

        return False, error

    def __try_get_existing_player(self, player_id):
        query = 'SELECT * FROM players WHERE id = ?'
        params = (player_id,)

        res, _ = self.__try_perform_operation_with_retries(
            'Check for existing player in DB',
            self.__try_execute_query,
            query=query,
            params=params,
            is_readonly=True
        )

        return res

    def __add_player(self, player_id, player_link, player_visible):
        res = self.__try_get_existing_player(player_id)

        if not res:
            query = 'INSERT INTO players (id, player_link, player_visible) VALUES (?, ?, ?)'
            params = (player_id, player_link, player_visible)

            res, _ = self.__try_perform_operation_with_retries(
                'Add new player to the database',
                self.__try_execute_query,
                query=query,
                params=params,
                is_readonly=False,
                allow_commit=False
            )

        return res

    def __try_get_existing_hero(self, hero_link):
        query = 'SELECT * FROM heroes WHERE hero_link = ?'
        params = (hero_link,)

        res, _ = self.__try_perform_operation_with_retries(
            'Check for existing hero in DB',
            self.__try_execute_query,
            query=query,
            params=params,
            is_readonly=True
        )

        return res

    def __add_hero(self, hero_name, hero_link):
        res = self.__try_get_existing_hero(hero_link)

        if not res:
            query = 'INSERT INTO heroes (hero_name, hero_link) VALUES (?, ?)'
            params = (hero_name, hero_link)

            res, _ = self.__try_perform_operation_with_retries(
                'Add new hero to the database',
                self.__try_execute_query,
                query=query,
                params=params,
                is_readonly=False,
                allow_commit=False
            )

        return res

    def __try_get_existing_match(self, match_id):
        query = 'SELECT * FROM matches WHERE id = ?'
        params = (match_id,)

        res, _ = self.__try_perform_operation_with_retries(
            'Check for existing match in DB',
            self.__try_execute_query,
            query=query,
            params=params,
            is_readonly=True
        )

        return res

    def add_match(self, match_id, match_link, match_datetime, match_outcome, match_duration,
                  match_radiant_score, match_dire_score):
        res = self.__try_get_existing_match(match_id)

        if not res:
            query = ('INSERT INTO matches (id, match_link, match_datetime, match_outcome, match_duration, '
                     'match_radiant_score, match_dire_score) VALUES (?, ?, ?, ?, ?, ?, ?)')
            params = (match_id, match_link, match_datetime, match_outcome,
                      match_duration, match_radiant_score, match_dire_score)

            res, _ = self.__try_perform_operation_with_retries(
                'Add new match to the database',
                self.__try_execute_query,
                query=query,
                params=params,
                is_readonly=False
            )

        return res

    def __add_match_stats_record(self, hero_link, p_id, data):
        hero_id = self.__try_get_existing_hero(hero_link)[0][0]
        data['hero_id'] = hero_id
        match_id = data['match_id']
        player_id = p_id

        query = 'SELECT match_id FROM match_stats WHERE match_id = ? AND player_id = ? AND hero_id = ?'
        params = (match_id, player_id, hero_id)

        res, _ = self.__try_perform_operation_with_retries(
            'Check for existing match_stats record',
            self.__try_execute_query,
            query=query,
            params=params,
            is_readonly=True
        )

        if res:
            print_warning(f'Such match_stats record already exists. match_id: {match_id}; player_id: {player_id}')
            print_warning('Skipping the iteration')

            return False

        columns = ', '.join(data.keys())
        placeholders = ', '.join('?' * len(data))

        query = f'INSERT INTO match_stats ({columns}) VALUES ({placeholders})'
        params = tuple(data.values())

        res, err = self.__try_perform_operation_with_retries(
            'Adding match_stats record',
            self.__try_execute_query,
            query=query,
            params=params,
            is_readonly=False,
            allow_commit=False
        )

        if err:
            error_msg = str(err)

            if 'Error binding parameter' in error_msg:
                start_index = error_msg.find('Error binding parameter') + len('Error binding parameter')
                end_index = error_msg.find('-')
                failing_param_index = int(error_msg[start_index:end_index].strip())

                failing_param_name = list(data.keys())[failing_param_index]
                failing_param_value = data[failing_param_name]

                print_warning(f'Param_Name: {failing_param_name}; Param_Value: {failing_param_value}')

        return res

    def dump_all_parsed_records(self, hero_link, hero_name, player_link, player_visible, data):
        player_id = data['player_id']

        self._connection.execute('BEGIN')
        self.__refresh_connection_cursor()

        _ = self.__add_player(player_id, player_link, player_visible)
        _ = self.__add_hero(hero_name, hero_link)

        res = self.__add_match_stats_record(hero_link, player_id, data)

        self._connection.commit()
        self.__refresh_connection_cursor()

        if not res:
            print_warning(f"Transaction for match_stats with match_id: \
                          {data['match_id']} and player_id: {player_id} has failed")
            print_warning('Skipping the iteration')

            self._connection.rollback()

        return res

    def update_queue_assignments(self, limit):
        self.__refresh_connection_cursor()

        res, _ = self.__try_perform_operation_with_retries(
            'Update agent queue in DB',
            self.__try_update_queue_assignments,
            q_limit=limit,
        )

        return res

    def upload_queue_assignments(self, queue_assignments):
        self.__refresh_connection_cursor()

        query_match_queue = 'SELECT match_link FROM match_queue WHERE match_link IN ({})'.format(
            ','.join(['?'] * len(queue_assignments)))

        existing_links_match_queue, _ = self.__try_perform_operation_with_retries(
            'Check for match_link duplicates (match_queue) before uploading new assignments',
            self.__try_execute_query,
            query=query_match_queue,
            params=queue_assignments,
            is_readonly=True
        )

        query_matches = 'SELECT match_link FROM matches WHERE match_link IN ({})'.format(
            ','.join(['?'] * len(queue_assignments)))

        existing_links_matches, _ = self.__try_perform_operation_with_retries(
            'Check for match_link duplicates (matches) before uploading new assignments',
            self.__try_execute_query,
            query=query_matches,
            params=queue_assignments,
            is_readonly=True
        )

        existing_links_match_queue = set(existing_links_match_queue)
        existing_links_matches = set(existing_links_matches)

        duplicate_links = existing_links_match_queue.union(existing_links_matches)

        unique_match_links = [link for link in queue_assignments if link not in duplicate_links]

        if not unique_match_links:
            return False

        query = 'INSERT INTO match_queue (match_link, is_assigned, agent) VALUES (?, ?, ?)'
        params = [(match_link, False, None) for match_link in unique_match_links]

        res, _ = self.__try_perform_operation_with_retries(
            'Upload new unassigned queue assignments',
            self.__try_execute_query,
            query=query,
            params=params,
            is_readonly=False,
            is_execute_many=True
        )

        return res

    def try_acquire_agent_queue(self, limit):
        self.__refresh_connection_cursor()

        query = 'SELECT * FROM match_queue WHERE is_assigned = 1 AND agent = ? LIMIT ?'
        params = (self.agent_name, limit)

        rows, _ = self.__try_perform_operation_with_retries(
            'Acquire agent queue',
            self.__try_execute_query,
            query=query,
            params=params,
            is_readonly=True
        )

        if rows:
            ids = [row[0] for row in rows]

            delete_query = 'DELETE FROM match_queue WHERE id IN ({})'.format(','.join(['?'] * len(ids)))
            params = ids

            res, _ = self.__try_perform_operation_with_retries(
                'Release the unloaded DB queue',
                self.__try_execute_query,
                query=delete_query,
                params=params,
                is_readonly=False,
                retry_count=1
            )

            if not res:
                print_error('DB queue release failed')
                global_await_exit_action()

            return [MatchQueue(*row) for row in rows]

        return False


class QueueWatcher:
    def __init__(self):
        self._current_agent_queue = None
        self._in_memory_threshold = 2
        self._in_memory_load_limit = 15
        self._in_memory_threshold_first_time = 1
        self._in_db_threshold = 30
        self._is_first_execution = True
        self._agent_lock_time_seconds = 1  # TODO change back

        self._db_watcher = DatabaseWatcher(database_path_global)

    def __lock_agent_operations(self):
        print_notification(f'QueueWatcher is getting locked for {self._agent_lock_time_seconds} seconds')
        print_notification('Please use that time to exit the application safely')

        time.sleep(self._agent_lock_time_seconds)

        print_warning('QueueWatcher is now unlocked')
        print_warning('Exiting the application now would cause damage to the queues.')

        time.sleep(1)

    def __load_in_memory_queue(self):
        self.__lock_agent_operations()

        if self._is_first_execution:
            temp_queue = self._db_watcher.try_acquire_agent_queue(1)
            in_memory_threshold = self._in_memory_threshold_first_time
        else:
            temp_queue = self._db_watcher.try_acquire_agent_queue(self._in_memory_load_limit)
            in_memory_threshold = self._in_memory_threshold

        if len(temp_queue) < in_memory_threshold:
            if self._db_watcher.update_queue_assignments(self._in_db_threshold):
                temp_queue = self._db_watcher.try_acquire_agent_queue(self._in_memory_load_limit)

                if len(temp_queue) < in_memory_threshold:
                    print_error('Failed updating the queue')
                    global_await_exit_action()
            else:
                print_error('Failed updating the queue. DB error')
                global_await_exit_action()

        self._current_agent_queue = deque(temp_queue)

    def fetch_agent_queue_item(self):
        if not self._current_agent_queue:
            self.__load_in_memory_queue()

        return self._current_agent_queue.popleft()


class RequestManager:
    def __init__(self):
        self._selenium_driver = self.__get_selenium_driver()
        # self._user_agent = self.__get_random_user_agent()
        self._user_agent = 'NyrinelAvalire'

        self._sleep_time = int(config_global['request_sleep_time_seconds'])
        self._sleep_time_q = float(config_global['request_sleep_time_q'])
        self._max_retries = int(config_global['request_max_retries'])
        self._sleep_time_threshold = int(config_global['request_sleep_time_seconds_threshold'])
        self._sleep_time_final_retry_minutes = int(config_global['sleep_time_final_retry_minutes'])
        self._use_selenium = config_global['use_selenium']

    @staticmethod
    def __create_chrome_driver(headless=True):
        chrome_options = webdriver.ChromeOptions()
        if headless:
            chrome_options.add_argument('--headless')
        return webdriver.Chrome(options=chrome_options)

    @staticmethod
    def __create_firefox_driver(headless=True):
        firefox_options = webdriver.FirefoxOptions()
        service = Service('geckodriver.exe')
        if headless:
            firefox_options.add_argument('-headless')
        return webdriver.Firefox(service=service, options=firefox_options)

    def __get_selenium_driver(self):
        preferred_browser = config_global['selenium_browser']

        if preferred_browser == 'firefox':
            return self.__create_firefox_driver()
        else:
            return self.__create_chrome_driver()

    @staticmethod
    def __put_request_asleep(seconds):
        print(f'Sleeping between requests for {seconds} seconds')
        time.sleep(seconds)

    def make_request_to_page_with_retries(self, link):
        retry_count = 0

        while retry_count < self._max_retries:
            if retry_count >= self._max_retries - 2:
                self._use_selenium = not self._use_selenium  # try different method once JIC

            result = self.__make_request_to_page(link)

            print(f'Selenium res: {result}')
            self.__put_request_asleep(self._sleep_time)

            if result:
                return result
            else:
                if self._sleep_time > self._sleep_time_threshold:
                    print_warning('Threshold sleep time reached. Skipping the retries.')
                    self._sleep_time = self._sleep_time_threshold
                    break

                if retry_count == 0:
                    self.__put_request_asleep(
                        self._sleep_time_threshold * 2)  # additional sleep to avoid request avalanche effect

                if retry_count % 3 == 0:
                    self._sleep_time = int(self._sleep_time * self._sleep_time_q)

                retry_count += 1
                print_warning(f'Got error during the web-request. Retries: {retry_count}/{self._max_retries}')

        print_warning('\nCould not get the response after retries. Invoking the final retry timeout...\n')

        self.__put_request_asleep(60 * self._sleep_time_final_retry_minutes)

        result = self.__make_request_to_page(link)

        if result:
            return result
        else:
            print_error('\nFinal request retry was unsuccessful. Manual calibration required')
            global_await_exit_action()

    def __make_request_to_page(self, link):
        if self._use_selenium:
            return self.__make_get_request_selenium(link)
        else:
            return self.__make_get_request(link)

    # TODO implement additional human-like simulation
    def __make_get_request_selenium(self, link):
        try:
            print(f'Making Selenium request to link: {link}')
            self._selenium_driver.get(link)

            return self._selenium_driver.page_source
        except WebDriverException as e:
            if '429' in str(e):
                print_warning('Encountered the 429 StatusCode')
            else:
                print_warning(f'Selenium request failed with: {e}')

            return False

    @staticmethod
    def __get_random_user_agent():
        ua = UserAgent(browsers=['chrome', 'firefox'], platforms='pc')

        return ua.random

    def __make_get_request(self, link):
        headers = {
            'User-Agent': self._user_agent
        }

        print_notification(f'Using following user-agent: {self._user_agent}')

        print(f'Making get request to link: {link}')
        response = requests.get(link, headers=headers)

        if response.status_code == 429:
            print_warning(f'Encountered the 429 StatusCode.')

            if 'Retry-After' in response.headers:
                requested_sleep_time = float(response.headers['Retry-After'])
                print_warning(f'Got the Retry-After header:')
                print_warning(f'Waiting for {requested_sleep_time} seconds to remove the 429 lock')

                time.sleep(requested_sleep_time)
                response = requests.get(link, headers=headers)
        if response.status_code == 200:
            return response.text

        return False

    def dispose(self):
        config_global['request_sleep_time_seconds'] = self._sleep_time
        config_global['request_sleep_time_q'] = self._sleep_time_q
        config_global['request_max_retries'] = self._max_retries
        config_global['request_sleep_time_seconds_threshold'] = self._sleep_time_threshold
        config_global['sleep_time_final_retry_minutes'] = self._sleep_time_final_retry_minutes
        config_global['use_selenium'] = self._use_selenium

        update_config(config_global)


class PlayerStatus(Enum):
    VISIBLE = 'Visible'
    HIDDEN = 'Hidden'
    UNKNOWN = 'Unknown'


class PlayerSide(Enum):
    DIRE = 'Dire'
    RADIANT = 'Radiant'


def parse_player_id(player_link_obj):
    return player_link_obj.get('href').split('/players/')[1]


def nullify_dash_if_found(text):
    return None if text == '-' else text


def parse_table_column_td_text(column_td_to_parse):
    if column_td_to_parse.find('span'):
        res = column_td_to_parse.find('span').text
    else:
        res = column_td_to_parse.text

    return nullify_dash_if_found(res)


def convert_str_to_datetime(datetime_string):
    return datetime.strptime(datetime_string, '%Y-%m-%dT%H:%M:%S%z')


def convert_rank_to_mmr(rank_to_convert):
    l, u = int(ranks_to_mmr_dict_global[rank_to_convert][0]), int(ranks_to_mmr_dict_global[rank_to_convert][1])

    return (l + u) / 2


def global_await_action():
    print()
    _ = input('Press Enter to continue')
    print()


def global_await_exit_action():
    global_await_action()
    sys.exit()


def read_global_config():
    with open('config.json', 'r') as file:
        cfg = json.load(file)

    return cfg


def update_config(new_values_dict):
    cfg = read_global_config()
    cfg.update(new_values_dict)

    with open('config.json', 'w') as file:
        json.dump(cfg, file, indent=4)


def get_player_heroes_meta_page_soup():
    with open('heroes_meta_page_soup_file.html', 'r', encoding='utf-8') as file:
        soup_str = file.read()

    return BeautifulSoup(soup_str, 'html.parser')

# TODO config for exiting the script
# Config section


config_global = read_global_config()

global_mmr_coefficient = 7
with open('ranks_to_mmr.json', 'r') as rtmmr:
    ranks_to_mmr_dict_global = json.load(rtmmr)


re_pattern_players = r'/players/\d+'

heroes_meta_page_soup_global = get_player_heroes_meta_page_soup()

database_path_global = '../../DotaAIDB/dota_ai.db'

queue_watcher_global = QueueWatcher()

current_queued_match = queue_watcher_global.fetch_agent_queue_item()

if not current_queued_match:
    print_error('Failed fetching the agent queue')
    global_await_exit_action()

current_match_url = current_queued_match.match_link
match_to_process = Match(current_match_url)

# TODO return to iterative approach
db_watcher_global = DatabaseWatcher(database_path_global)
request_manager_global = RequestManager()
match_to_process.process_match()
db_watcher_global.dispose()
request_manager_global.dispose()


