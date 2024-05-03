import json

import pandas as pd
import requests
import time
from utils.common import *
from typing import List
from joblib import load
import argparse

class PlayerData:
	def __init__(self, player_id, hero_id, player_side, player_match_rank_initial):
		self.player_id = player_id
		self.hero_id = hero_id
		self.player_side = player_side
		self.player_match_rank_initial = player_match_rank_initial


class RequestManager:
	def __init__(self):
		self._max_retries = 10
		self._retry_timeout = 15
		self._pre_request_timeout = 0

	def make_api_call(self, api_link):
		retries = 0

		while retries <= self._max_retries:

			retries += 1

			try:
				print(f'Awaiting {self._pre_request_timeout} seconds as a pre-request timeout')
				time.sleep(self._pre_request_timeout)

				response = requests.get(api_link)

				if 'X-Rate-Limit-Remaining-Minute' in response.headers:
					remaining_req_4_min = int(response.headers['X-Rate-Limit-Remaining-Minute'])

					if remaining_req_4_min <= 3:
						print_helper_global.print_message(MessageType.NOTIFICATION,
														  f'Exceeded requests/minute threshold. Going to sleep for 60 seconds')
						time.sleep(60)

				if 'X-Rate-Limit-Remaining-Day' in response.headers:
					print(f"Requests remaining for today: {response.headers['X-Rate-Limit-Remaining-Day']}/2000")

				if response.status_code == 200:
					print_helper_global.print_message(MessageType.SUCCESS,
													  f'Request to {api_link} is complete with status_code: 200')
					return response.json()
				elif response.status_code != 200:
					print_helper_global.print_message(MessageType.WARNING,
													  f'Request to {api_link} failed with status_code: {response.status_code}.')
					if response.status_code == 500 and retries == self._max_retries - 1:
						print_helper_global.print_message(MessageType.WARNING,
														  'API is unresponsive. Going for a long sleep for 20 seconds')
						time.sleep(20)
					if retries == self._max_retries:
						if response.status_code == 500:
							print_helper_global.print_message(MessageType.WARNING,
															  'API server is down. Requesting script termination')
							break

			except Exception as e:
				print_helper_global.print_message(MessageType.WARNING, f'Caught unexpected exception: {e}.')

			print_helper_global.print_message(MessageType.WARNING,
											  f'Failed to get the response. Retry in: {self._retry_timeout * retries} seconds')
			time.sleep(self._retry_timeout * retries)

		print_helper_global.print_message(MessageType.WARNING,
										  f'Failed to get the response after {retries} retries.')

		return False


class ParseManager:
	def __init__(self):
		self._request_manager = RequestManager()

		self._base_url = 'https://api.opendota.com/api'

		self.radiant_team_const_str = 'Radiant'
		self.dire_team_const_str = 'Dire'

	def __get_player_totals_data(self, p_id):
		return self._request_manager.make_api_call(f'{self._base_url}/players/{p_id}/totals')

	def __get_player_counts_data(self, p_id):
		return self._request_manager.make_api_call(f'{self._base_url}/players/{p_id}/counts')

	def __get_player_heroes_data(self, p_id):
		return self._request_manager.make_api_call(f'{self._base_url}/players/{p_id}/heroes')

	def __parse_player_totals(self, player_id, dest_data_dict):
		player_totals_data_dict = self.__get_player_totals_data(player_id)

		if not player_totals_data_dict:
			return False

		fields_to_parse = [
			'kills', 'deaths', 'assists', 'kda', 'gold_per_min',
			'xp_per_min', 'last_hits', 'denies', 'lane_efficiency_pct',
			'level', 'hero_damage', 'tower_damage', 'hero_healing'
		]

		dicts_to_parse = [d for d in player_totals_data_dict if d['field'] in fields_to_parse]

		for d in dicts_to_parse:
			dest_data_dict[f"player_{d['field']}_average_all_matches"] = float(
				safe_divide(float(d['sum']), int(d['n'])))

		dest_data_dict['player_time_played_all_matches'] = (
			next((d for d in player_totals_data_dict if d['field'] == 'duration')), None)[0]['sum']

		return True

	def __parse_player_counts(self, player_id, dest_data_dict):
		player_counts_data_dict = self.__get_player_counts_data(player_id)

		if not player_counts_data_dict:
			return False

		try:
			leaver_status = player_counts_data_dict['leaver_status']

			dest_data_dict['player_matches_abandoned'] = sum(
				[int(data['games']) for key, data in leaver_status.items() if key not in ('0', '1')])

			winrate_all_time_dict = player_counts_data_dict['game_mode']['22']

			dest_data_dict['player_winrate_over_time'] = float(
				safe_divide(winrate_all_time_dict['win'], winrate_all_time_dict['games']))
			dest_data_dict['player_all_matches_played_number'] = int(winrate_all_time_dict['games'])
			dest_data_dict['player_matches_won'] = int(winrate_all_time_dict['win'])
			dest_data_dict['player_matches_lost'] = (dest_data_dict['player_all_matches_played_number'] -
													 dest_data_dict['player_matches_won'])

			fraction_games_dict = player_counts_data_dict['is_radiant']
			dire_dict = fraction_games_dict['0']
			radiant_dict = fraction_games_dict['1']

			dest_data_dict['dire_games_played_all_time'] = dire_dict['games']
			dest_data_dict['dire_winrate_all_time'] = float(safe_divide(dire_dict['win'],
																		dest_data_dict['dire_games_played_all_time']))

			dest_data_dict['radiant_games_played_all_time'] = radiant_dict['games']
			dest_data_dict['radiant_winrate_all_time'] = float(safe_divide(radiant_dict['win'],
																		   dest_data_dict[
																			   'radiant_games_played_all_time']))

			return True
		except KeyError as e:
			print_helper_global.print_message(MessageType.WARNING,
											  f'KeyError encountered ({e}) while parsing player_counts. Player ID: {player_id}')
			print_helper_global.print_message(MessageType.WARNING,
											  f'Prediction impossible')
			return False

	def __parse_player_heroes(self, player_id, hero_id, dest_data_dict):
		player_heroes = self.__get_player_heroes_data(player_id)

		if not player_heroes:
			return False

		data_dict = player_heroes

		selected_dict = next((d for d in data_dict if d['hero_id'] == hero_id), None)

		dest_data_dict['player_hero_total_matches_played'] = int(selected_dict['games'])
		player_hero_total_matches_played = dest_data_dict['player_hero_total_matches_played']

		dest_data_dict['player_hero_winrate_overall'] = float(safe_divide(int(selected_dict['win']),
																		  player_hero_total_matches_played))
		dest_data_dict['player_heroes'] = data_dict

		return True

	def __parse_match_data_stage_one(self, players_data: List[PlayerData], match_data_dict_out):

		for player in players_data:
			player_match_data_dict = {}

			player_match_data_dict['player_id'] = str(player.player_id)
			player_match_data_dict['hero_id'] = player.hero_id
			player_match_data_dict['player_match_rank_initial'] = player.player_match_rank_initial
			player_match_data_dict['player_side'] = player.player_side

			if not self.__parse_player_totals(player.player_id, player_match_data_dict):
				return False

			if not self.__parse_player_counts(player.player_id, player_match_data_dict):
				return False

			if not self.__parse_player_heroes(player.player_id, player.hero_id, player_match_data_dict):
				return False

			match_data_dict_out['players'].append(player_match_data_dict)

		average_match_mmr = sum(
			[sum(ranks_to_mmr[p['player_match_rank_initial']]) / 2 for p in match_data_dict_out['players']]) / 10

		match_data_dict_out['average_match_mmr'] = average_match_mmr

		return True

	@staticmethod
	def __parse_match_data_stage_two(match_data_dict):
		def handle_pick_conf_coef(winrate, total_played):
			if winrate != -1. and total_played > 10:
				temp = winrate * 100

				if temp < 20:
					return -2
				elif 20 <= temp <= 45:
					return -1
				elif 80 >= temp >= 55:
					return 1
				elif temp > 80:
					return 2
				else:
					return 0
			else:
				return 0

		for player in match_data_dict['players']:
			player['player_q_mmr_diff'] = (sum(ranks_to_mmr[player['player_match_rank_initial']])
										   / 2 - match_data_dict['average_match_mmr'])

			player_id, hero_id, player_side = player['player_id'], player['hero_id'], player['player_side']
			player_heroes = player['player_heroes']

			player_heroes_pick_confidence_score_allies = 0
			player_heroes_pick_confidence_score_enemies = 0

			for p in match_data_dict['players']:
				if p['player_id'] != player_id:
					ph_dict = next((d for d in player_heroes if d['hero_id'] == p['hero_id']), None)

					if p['player_side'] == player_side:
						games_with_total = ph_dict['with_games']
						games_with_won = ph_dict['with_win']

						hero_with_winrate = float(safe_divide(games_with_won, games_with_total))

						player_heroes_pick_confidence_score_allies += handle_pick_conf_coef(hero_with_winrate,
																							games_with_total)
					else:
						games_against_total = ph_dict['against_games']
						games_against_won = ph_dict['against_win']

						hero_against_winrate = float(safe_divide(games_against_won, games_against_total))

						player_heroes_pick_confidence_score_enemies += handle_pick_conf_coef(hero_against_winrate,
																							 games_against_total)

					p['player_heroes_pick_confidence_score_allies'] = player_heroes_pick_confidence_score_allies
					p['player_heroes_pick_confidence_score_enemies'] = player_heroes_pick_confidence_score_enemies

	def process_match(self, players_data):

		res_dict = {'players': []}

		if not self.__parse_match_data_stage_one(players_data, res_dict):
			return False

		self.__parse_match_data_stage_two(res_dict)

		return res_dict


class DataProcessor:
	def __init__(self):
		self._parse_manager = ParseManager()
		self._player_ranks_to_mmr_dict = ranks_to_mmr.copy()

		self._aggregation_rules = {
			'player_q_mmr_diff': 'sum',
			'player_hero_winrate_overall': 'mean',
			'player_hero_total_matches_played': 'sum',
			'dire_winrate_all_time': 'mean',
			'dire_games_played_all_time': 'mean',
			'radiant_winrate_all_time': 'mean',
			'radiant_games_played_all_time': 'mean',
			'player_heroes_pick_confidence_score_allies': 'sum',
			'player_heroes_pick_confidence_score_enemies': 'sum',
			'player_heroes_pick_confidence_score_total': 'sum',
			'player_time_played_all_matches': 'mean',
			'player_winrate_over_time': 'mean',
			'player_all_matches_played_number': 'mean',
			'player_matches_abandonment_rate': 'mean',
			'player_matches_lost': 'mean',
			'player_matches_won': 'mean',
			'player_match_rank_initial_mmr': 'mean',
			'player_kda_average_all_matches': 'mean',
			'hero_pickrate_average': 'mean',
			'hero_winrate_average': 'mean',
			'hero_pickrate_for_rank': 'mean',
			'hero_winrate_for_rank': 'mean',
			'player_match_rank_initial': lambda x: list(x),
			'player_id': lambda x: list(x),
			'hero_id': lambda x: list(x),
			'player_side': 'first'
		}

		self._column_mapping = {
			'player_q_mmr_diff': 'team_q_mmr_diff_sum',
			'player_hero_winrate_overall': 'team_heroes_winrate_overall_mean',
			'player_hero_total_matches_played': 'team_heroes_total_matches_played_sum',
			'dire_winrate_all_time': 'team_players_dire_winrate_all_time_mean',
			'dire_games_played_all_time': 'team_players_dire_games_played_all_time_mean',
			'radiant_winrate_all_time': 'team_players_radiant_winrate_all_time_mean',
			'radiant_games_played_all_time': 'team_players_radiant_games_played_all_time_mean',
			'player_heroes_pick_confidence_score_allies': 'team_heroes_pick_confidence_score_allies_sum',
			'player_heroes_pick_confidence_score_enemies': 'team_heroes_pick_confidence_score_enemies_sum',
			'player_heroes_pick_confidence_score_total': 'team_heroes_pick_confidence_score_total_sum',
			'player_time_played_all_matches': 'team_players__time_played_all_matches_mean',
			'player_winrate_over_time': 'team_players_winrate_over_time_mean',
			'player_all_matches_played_number': 'team_players_all_matches_played_number_mean',
			'player_matches_abandonment_rate': 'team_players_matches_abandonment_rate_mean',
			'player_matches_lost': 'team_players_matches_lost_mean',
			'player_matches_won': 'team_players_matches_won_mean',
			'player_match_rank_initial_mmr': 'team_players_match_rank_initial_mmr_mean',
			'player_kda_average_all_matches': 'team_players_kda_average_all_matches_mean',
			'hero_pickrate_average': 'team_heroes_pickrate_average_mean',
			'hero_winrate_average': 'team_heroes_winrate_average_mean',
			'hero_pickrate_for_rank': 'team_heroes_pickrate_for_rank_mean',
			'hero_winrate_for_rank': 'team_heroes_winrate_for_rank_mean',
			'player_match_rank_initial': 'team_players_match_ranks_initial',
			'player_id': 'team_players_id_list',
			'hero_id': 'team_heroes_id_list',
			'player_side': 'team_side'
		}

		self._columns_to_subtract = ['team_q_mmr_diff_sum', 'team_heroes_winrate_overall_mean',
							   'team_heroes_total_matches_played_sum', 'team_players_dire_winrate_all_time_mean',
							   'team_players_dire_games_played_all_time_mean',
							   'team_players_radiant_winrate_all_time_mean',
							   'team_players_radiant_games_played_all_time_mean',
							   'team_heroes_pick_confidence_score_allies_sum',
							   'team_heroes_pick_confidence_score_enemies_sum',
							   'team_heroes_pick_confidence_score_total_sum',
							   'team_players__time_played_all_matches_mean',
							   'team_players_winrate_over_time_mean', 'team_players_all_matches_played_number_mean',
							   'team_players_matches_abandonment_rate_mean', 'team_players_matches_lost_mean',
							   'team_players_matches_won_mean', 'team_players_match_rank_initial_mmr_mean',
							   'team_players_kda_average_all_matches_mean', 'team_heroes_pickrate_average_mean',
							   'team_heroes_winrate_average_mean', 'team_heroes_pickrate_for_rank_mean',
							   'team_heroes_winrate_for_rank_mean']

	def __transform_to_mmr(self, player_rank):
		return sum(self._player_ranks_to_mmr_dict[player_rank]) / 2

	def process_data(self, players_data_raw):
		match_data_raw = self._parse_manager.process_match(players_data_raw)

		df = pd.DataFrame(match_data_raw['players'])
		df = df.drop(columns=['player_heroes'])

		df_heroes = pd.read_csv('heroes_table.csv')

		df = pd.merge(df, df_heroes, on='hero_id', how='inner')

		df['player_side'] = df['player_side'].astype('category')
		df['player_match_rank_initial'] = df['player_match_rank_initial'].astype('category')

		df['player_match_rank_initial_mmr'] = df['player_match_rank_initial'].apply(self.__transform_to_mmr)
		df['player_match_rank_initial_mmr'] = df['player_match_rank_initial_mmr'].astype('float64')

		winrate_columns = [col for col in df.columns if 'winrate' in col.lower() and 'hero' not in col.lower()]
		pickrate_columns = [col for col in df.columns if 'pickrate' in col.lower() and 'hero' not in col.lower()]

		df[winrate_columns] *= 100
		df[pickrate_columns] *= 100

		df['player_hero_winrate_overall'] *= 100

		closest_player_idx = df['player_q_mmr_diff'].abs().idxmin()
		closest_player_rank = df.loc[closest_player_idx, 'player_match_rank_initial'].split(' ')[0]

		if closest_player_rank.lower() in ['herald', 'guardian', 'crusader']:
			closest_player_rank = 'up_to_crusader'

		pickrate_column = f'hero_pickrate_{closest_player_rank.lower()}'
		winrate_column = f'hero_winrate_{closest_player_rank.lower()}'

		df['hero_pickrate_for_rank'] = df[pickrate_column]
		df['hero_winrate_for_rank'] = df[winrate_column]

		df['player_heroes_pick_confidence_score_total'] = (df['player_heroes_pick_confidence_score_allies'] +
														  df['player_heroes_pick_confidence_score_enemies'])
		df['player_matches_abandonment_rate'] = (df['player_matches_abandoned'] / df[
			'player_all_matches_played_number']) * 100

		df.reset_index(drop=True, inplace=True)

		df = df.groupby(['player_side'], as_index=False, observed=False).agg(self._aggregation_rules)

		df.rename(columns=self._column_mapping, inplace=True)

		exclude_columns = ['team_players_match_ranks_initial', 'team_players_id_list', 'team_heroes_id_list']

		df.reset_index()
		df = df.drop(columns=exclude_columns)

		df['match_id'] = 1
		df_dire = df[df['team_side'] == 'Dire']
		df_radiant = df[df['team_side'] == 'Radiant']

		result_dire = (df_dire.set_index('match_id')[self._columns_to_subtract] -
					   df_radiant.set_index('match_id')[self._columns_to_subtract])
		result_radiant = (df_radiant.set_index('match_id')[self._columns_to_subtract] -
						  df_dire.set_index('match_id')[self._columns_to_subtract])

		return result_dire, result_radiant


class MatchResultPredictor:
	def __init__(self):
		self._rf_model = load('random_forest_model.joblib')
		self._lr_model = load('logistic_regression_model.joblib')

		self._data_processor = DataProcessor()

	def predict(self, raw_data):
		data_dire, data_radiant = self._data_processor.process_data(raw_data)

		res_rf_dire = self._rf_model.predict_proba(data_dire)[0]
		res_lr_dire = self._lr_model.predict_proba(data_dire)[0]

		res_rf_radiant = self._rf_model.predict_proba(data_radiant)[0]
		res_lr_radiant = self._lr_model.predict_proba(data_radiant)[0]

		radiant_win_prediction_perc = 100 * (sum([res_rf_dire[0], res_lr_dire[0], res_rf_radiant[1], res_lr_radiant[1]]) / 4)

		return [radiant_win_prediction_perc > 50.0, radiant_win_prediction_perc]


parser = argparse.ArgumentParser(description='Takes string representing a full filepath')
parser.add_argument('--filepath', type=str, help='Path to .json file that contains match data.')

args = parser.parse_args()

filepath = args.filepath
print_helper_global = PrintHelper(False)

try:
	with open(filepath, 'r', encoding='utf-8') as f:
		players_data_raw = json.load(f)

	players_data = [PlayerData(*row.values()) for row in players_data_raw]

	match_predictor = MatchResultPredictor()

	is_radiant_win, radiant_win_perc = match_predictor.predict(players_data)

	print_helper_global.print_message(MessageType.SUCCESS, f'RadiantWin: {is_radiant_win}. Confidence: {radiant_win_perc}')
except Exception as e:
	print_helper_global.print_message(MessageType.ERROR, f'Failed with unexpected error: {e}')
