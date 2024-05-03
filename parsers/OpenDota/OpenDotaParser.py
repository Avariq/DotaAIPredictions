import argparse
from utils.common import *
	

print_helper_global = PrintHelper(True)


try:

	import requests
	import time
	import re
	from enum import Enum
	from datetime import datetime
	from dateutil.relativedelta import relativedelta
	import json
	from dataclasses import dataclass
	from colorama import Fore, Style
	import sqlite3
	import socket
	from collections import deque
	import psycopg2


	class MatchQueue:
		def __init__(self, q_id, match_id, is_assigned, agent, is_processed):
			self.id = q_id
			self.match_id = match_id
			self.is_assigned = is_assigned
			self.agent = agent
			self.is_processed = is_processed


	def save_failed_response_to_json(response, filename='failed_request.json'):
		try:
			with open(filename, 'w') as f:
				json.dump({
					'status_code': response.status_code,
					'headers': dict(response.headers),
					'reason': response.reason,
					'body': response.text
				}, f, indent=4)
			print(f'Failed response saved to {filename}')
		except Exception as e:
			print(f'Error saving failed response: {e}')


	class RequestManager:
		def __init__(self, proxy_server=None):
			self._request_count = 0
			self._max_retries = 7
			self._retry_timout = 15
			self._pre_request_timeout = 0

			self._termination_requested = False

			self._proxies = None

			if proxy_server:
				self._proxies = proxy_server

		def make_api_call(self, api_link):
			retries = 0
			while retries <= self._max_retries:
				if self._termination_requested:
					break

				retries += 1

				try:
					print(f'Awaiting {self._pre_request_timeout} seconds as a pre-request timeout')
					time.sleep(self._pre_request_timeout)
					if self._proxies:
						response = requests.get(api_link, proxies=self._proxies)
					else:
						response = requests.get(api_link)

					self._request_count += 1

					if 'X-Rate-Limit-Remaining-Minute' in response.headers:
						remaining_req_4_min = int(response.headers['X-Rate-Limit-Remaining-Minute'])

						if remaining_req_4_min <= 3:
							print_helper_global.print_message(MessageType.NOTIFICATION, 
													f'Exceeded requests/minute threshold. Going to sleep for 60 seconds')
							time.sleep(60)
					elif self._request_count % 55 == 0:
						print_helper_global.print_message(MessageType.NOTIFICATION, 
														  f'Requests made: {self._request_count}. Going to sleep for a minute')
						time.sleep(60)

					if 'X-Rate-Limit-Remaining-Day' in response.headers:
						print(f"Requests remaining for today: {response.headers['X-Rate-Limit-Remaining-Day']}/2000")

					if response.status_code == 200:
						print_helper_global.print_message(MessageType.SUCCESS, 
														  f'Request to {api_link} is complete with status_code: 200')
						return response.json()
					elif response.status_code == 429:
						print_helper_global.print_message(MessageType.WARNING, 'Seems like all the requests have been used')
						self._termination_requested = True
					elif response.status_code == 500 or response.status_code == 404 or response.status_code != 200:
						print_helper_global.print_message(MessageType.WARNING, f'Request to {api_link} failed with status_code: {response.status_code}.')
						if response.status_code == 500 and retries == self._max_retries - 1:
							print_helper_global.print_message(MessageType.WARNING, 'Many 500s. Going for a long sleep for 30 minutes...')
							time.sleep(60 * 30)
						if response.status_code == 404 and retries > 2:
							print_helper_global.print_message(MessageType.WARNING,
															  'Unexpected API provider 404 error detected multiple times. Aborting the retry strategy')
							break
						if retries == self._max_retries:
							if response.status_code == 500:
								print_helper_global.print_message(MessageType.WARNING,
																  'Still got the 500 status code. Requesting script termination...')
								self._termination_requested = True
							else:
								print_helper_global.print_message(MessageType.WARNING, 
									f'API call to endpoint {api_link} failed with status_code: {response.status_code}')
								print_helper_global.print_message(MessageType.WARNING,
																  f"Request's response is to be saved as a json file: failed_request.json")
								print_helper_global.print_message(MessageType.WARNING, 
									f'Total requests made: {self._request_count}. Note: 2000 request is a maximum per day')

								save_failed_response_to_json(response)

								global_await_exit_action()

				except Exception as e:
					print_helper_global.print_message(MessageType.WARNING, f'Caught unexpected exception: {e}.')

				print_helper_global.print_message(MessageType.WARNING,
												  f'Failed to get the response. Retry in: {self._retry_timout * retries} seconds')
				time.sleep(self._retry_timout * retries)

			print_helper_global.print_message(MessageType.WARNING,
											  f'Failed to get the response after {retries} retries. Skipping iteration')

			if self._termination_requested:
				print_helper_global.print_message(MessageType.WARNING,
												  'Termination of the script has been requested. Finishing up the execution...')
				global_await_exit_action()

			return False


	class ParseManager:
		def __init__(self, request_manager):
			self._request_manager = request_manager
			self._db_watcher = DatabaseWatcher()

			self._base_url = 'https://api.opendota.com/api'

			self.radiant_team_const_str = 'Radiant'
			self.dire_team_const_str = 'Dire'

		def __get_match_data(self, match_id):
			# return match_data_global_temp
			return self._request_manager.make_api_call(f'{self._base_url}/matches/{match_id}')

		def __get_player_totals_data(self, p_id):
			# return player_totals_data_global_temp
			return self._request_manager.make_api_call(f'{self._base_url}/players/{p_id}/totals')

		def __get_player_counts_data(self, p_id):
			# return player_counts_data_global_temp
			return self._request_manager.make_api_call(f'{self._base_url}/players/{p_id}/counts')

		def __get_player_heroes_data(self, p_id):
			# return player_heroes_data_global_temp
			return self._request_manager.make_api_call(f'{self._base_url}/players/{p_id}/heroes')

		@staticmethod
		def __parse_main_match_data(match_data, dest_data_dict):
			dest_data_dict['match_id'] = str(match_data['match_id'])
			dest_data_dict['match_datetime'] = datetime.fromtimestamp(match_data['start_time'])
			dest_data_dict['match_radiant_score'] = int(match_data['radiant_score'])
			dest_data_dict['match_dire_score'] = int(match_data['dire_score'])
			dest_data_dict['radiant_win'] = match_data['radiant_win']
			dest_data_dict['match_duration'] = match_data['duration']

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
				dest_data_dict[f"player_{d['field']}_average_all_matches"] = float(safe_divide(float(d['sum']), int(d['n'])))

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
																   dest_data_dict['radiant_games_played_all_time']))

				return True
			except KeyError as e:
				print_helper_global.print_message(MessageType.WARNING,
												  f'KeyError encountered ({e}) while parsing player_counts. Player ID: {player_id}')
				print_helper_global.print_message(MessageType.WARNING,
												  f'Skipping the iteration')
				return False

		def __parse_player_heroes(self, player_id, hero_id, dest_data_dict):
			player_heroes = self.__get_player_heroes_data(player_id)

			if not player_heroes:
				return False

			data_dict = player_heroes

			selected_dict = next((d for d in data_dict if d['hero_id'] == hero_id), None)

			if not selected_dict:
				print_helper_global.print_message(MessageType.ERROR, 'Failed parsing player match_hero info')
				global_await_exit_action()

			dest_data_dict['player_hero_total_matches_played'] = int(selected_dict['games'])
			player_hero_total_matches_played = dest_data_dict['player_hero_total_matches_played']

			dest_data_dict['player_hero_winrate_overall'] = float(safe_divide(int(selected_dict['win']),
																			  player_hero_total_matches_played))
			dest_data_dict['player_heroes'] = data_dict

			return True

		def __parse_match_data_stage_one(self, match_data_dict_in, match_data_dict_out):
			if not all('account_id' in d for d in match_data_dict_in['players']):
				print_helper_global.print_message(MessageType.WARNING,
												  'Not all of the players are accessible. Skipping iteration')
				return False

			for player in match_data_dict_in['players']:
				player_match_data_dict = {}

				player_match_data_dict['match_id'] = str(match_data_dict_in['match_id'])
				player_match_data_dict['player_id'] = str(player['account_id'])
				player_match_data_dict['hero_id'] = player['hero_id']
				player_match_data_dict['player_has_won'] = bool(player['win'])
				player_match_data_dict['player_nickname'] = player['personaname']
				player_match_data_dict['player_match_rank_initial'] = rank_tiers_to_ranks[str(player['rank_tier'])]
				player_match_data_dict['player_xpm'] = player['xp_per_min']
				player_match_data_dict['player_gpm'] = player['gold_per_min']
				player_match_data_dict['player_denies'] = player['denies']
				player_match_data_dict['player_lasthits'] = player['last_hits']
				player_match_data_dict['player_net'] = player['net_worth']
				player_match_data_dict['player_assists_number'] = player['assists']
				player_match_data_dict['player_deaths_number'] = player['deaths']
				player_match_data_dict['player_kills_number'] = player['kills']
				player_match_data_dict['hero_lvl'] = player['level']
				player_match_data_dict['player_side'] = self.radiant_team_const_str \
					if player['isRadiant'] else self.dire_team_const_str

				if not self.__parse_player_totals(player['account_id'], player_match_data_dict):
					return False

				if not self.__parse_player_counts(player['account_id'], player_match_data_dict):
					return False

				if not self.__parse_player_heroes(player['account_id'], player['hero_id'], player_match_data_dict):
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

							player_heroes_pick_confidence_score_allies += handle_pick_conf_coef(hero_with_winrate, games_with_total)
						else:
							games_against_total = ph_dict['against_games']
							games_against_won = ph_dict['against_win']

							hero_against_winrate = float(safe_divide(games_against_won, games_against_total))

							player_heroes_pick_confidence_score_enemies += handle_pick_conf_coef(hero_against_winrate, games_against_total)

						p['player_heroes_pick_confidence_score_allies'] = player_heroes_pick_confidence_score_allies
						p['player_heroes_pick_confidence_score_enemies'] = player_heroes_pick_confidence_score_enemies

		def process_match(self, match_id):
			match_data = self.__get_match_data(match_id)

			if not match_data:
				return False

			res_dict = {'players': []}

			self.__parse_main_match_data(match_data, res_dict)
			if not self.__parse_match_data_stage_one(match_data, res_dict):
				return False

			self.__parse_match_data_stage_two(res_dict)

			if self._db_watcher.dump_all_parsed_records(res_dict):
				print_helper_global.print_message(MessageType.NOTIFICATION, f'MatchId: {match_id} has been processed')
			else:
				print_helper_global.print_message(MessageType.WARNING, f'Failed processing the match with id: {match_id}')

		def dispose(self):
			self._db_watcher.dispose()


	class DatabaseWatcher:
		def __init__(self, agent_name=None):
			self._operation_lock_time = 3

			self._connection = None
			self._cursor = None

			if agent_name:
				self.agent_name = agent_name
			else:
				self.agent_name = socket.gethostname()

			self.__open_database_connection()

		def dispose(self):
			if self._connection:
				self._connection.close()

		def __open_database_connection(self):
			self._connection = psycopg2.connect(
							dbname='dota_ai_od',
							user='limited_user',
							password='*removed*',
							host='*azure*',
							port='5432'
						)

			self._connection.autocommit = False

			self.__refresh_connection_cursor()

		def __refresh_connection_cursor(self):
			self._cursor = self._connection.cursor()

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

			except psycopg2.Error as e:
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
					print_helper_global.print_message(MessageType.WARNING, f'Run into exception: {e}. Retries: {retries+1}/{retry_count}')

					time.sleep(self._operation_lock_time)
					retries += 1

					err = e

			print_helper_global.print_message(MessageType.ERROR, f'The operation {operation_name} failed after retries.')

			return False, err

		def __try_update_queue_assignments(self, q_limit):
			try:
				with self._connection.cursor() as cursor:
					cursor.execute("""
						SELECT id FROM match_queue
						WHERE is_assigned = FALSE AND is_processed = FALSE
						ORDER BY id ASC
						LIMIT %s FOR UPDATE""", (q_limit,))

					rows = cursor.fetchall()

					ids = [row[0] for row in rows]

					cursor.execute("""
						UPDATE match_queue
						SET is_assigned = TRUE, agent = %s
						WHERE id = ANY(%s)
					""", (self.agent_name, ids))

					self._connection.commit()

				return True, None
			except psycopg2.Error as e:
				error = e

			return False, error

		def __try_get_existing_player(self, player_id):
			query = 'SELECT * FROM players WHERE id = %s'
			params = (str(player_id),)

			res, _ = self.__try_perform_operation_with_retries(
				'Check for existing player in DB',
				self.__try_execute_query,
				query=query,
				params=params,
				is_readonly=True
			)

			return res

		def __add_player(self, player_id, allow_commit):
			res = self.__try_get_existing_player(player_id)

			if not res:
				query = 'INSERT INTO players (id) VALUES (%s)'
				params = (player_id,)

				res, _ = self.__try_perform_operation_with_retries(
					'Add new player to the database',
					self.__try_execute_query,
					query=query,
					params=params,
					is_readonly=False,
					allow_commit=allow_commit
				)

			return res

		def __try_get_existing_match(self, match_id):
			query = 'SELECT * FROM matches WHERE id = %s'
			params = (str(match_id),)

			res, _ = self.__try_perform_operation_with_retries(
				'Check for existing match in DB',
				self.__try_execute_query,
				query=query,
				params=params,
				is_readonly=True
			)

			return res

		def __add_match(self, match_id, match_datetime, radiant_win, match_duration,
					  match_radiant_score, match_dire_score, allow_commit):
			res = self.__try_get_existing_match(match_id)

			if not res:
				query = """
					INSERT INTO matches (id, datetime, radiant_win, duration, radiant_score, dire_score)
					VALUES (%s, %s, %s, %s, %s, %s)
				"""
				params = (str(match_id), match_datetime, radiant_win, match_duration, match_radiant_score, match_dire_score)

				res, _ = self.__try_perform_operation_with_retries(
					'Add new match to the database',
					self.__try_execute_query,
					query=query,
					params=params,
					is_readonly=False,
					allow_commit=allow_commit
				)

			return res

		def dump_all_parsed_records(self, data):
			self.__refresh_connection_cursor()

			match_id = data['match_id']
			match_datetime = data['match_datetime']
			match_outcome = data['radiant_win']
			match_duration = data['match_duration']
			match_radiant_score = data['match_radiant_score']
			match_dire_score = data['match_dire_score']
			average_match_mmr = data['average_match_mmr']

			_ = self.__add_match(match_id, match_datetime, match_outcome, match_duration,
								 match_radiant_score, match_dire_score, False)

			for player in data['players']:
				_ = self.__add_player(player['player_id'], False)

				player.pop('player_heroes', None)
				player['average_match_mmr'] = average_match_mmr

				columns = ', '.join(player.keys())
				placeholders = ', '.join(['%s' for _ in player])

				query = f'INSERT INTO match_stats ({columns}) VALUES ({placeholders})'
				params = tuple(player.values())

				res, _ = self.__try_perform_operation_with_retries(
					f'Add match_stats record for Match_Id: {match_id}, Player_Id: {player["player_id"]}, Hero_Id: {player["hero_id"]}',
					self.__try_execute_query,
					query=query,
					params=params,
					is_readonly=False,
					allow_commit=False
				)

				if not res:
					print_helper_global.print_message(MessageType.WARNING, f'Transaction for match_stats with match_id:' +
										  f'{data["match_id"]} and player_id: {player["player_id"]} has failed')
					print_helper_global.print_message(MessageType.WARNING, 'Skipping the iteration')

					self._connection.rollback()
					return False

			self._connection.commit()

			return True

		def update_queue_assignments(self, limit):
			self.__refresh_connection_cursor()

			res, _ = self.__try_perform_operation_with_retries(
				'Update agent queue in DB',
				self.__try_update_queue_assignments,
				q_limit=limit,
			)

			return res

		def try_acquire_agent_queue(self, limit):
			self.__refresh_connection_cursor()

			query = 'SELECT * FROM match_queue WHERE is_assigned = %s AND is_processed = %s AND agent = %s LIMIT %s'
			params = (True, False, self.agent_name, limit)

			rows, _ = self.__try_perform_operation_with_retries(
				'Acquire agent queue',
				self.__try_execute_query,
				query=query,
				params=params,
				is_readonly=True
			)

			if rows:
				return [MatchQueue(*row) for row in rows]

			if isinstance(rows, list):
				print_helper_global.print_message(MessageType.WARNING, 'Failed fetching the queue: Queue is empty')
				return []
			else:
				print_helper_global.print_message(MessageType.ERROR, 'Failed fetching the queue')

			global_await_exit_action()

		def mark_queue_item_as_processed(self, queue_item):
			self.__refresh_connection_cursor()

			query = 'UPDATE match_queue SET is_processed = %s WHERE id = %s'
			params = (True, queue_item.id)

			res, _ = self.__try_perform_operation_with_retries(
				'Release queue item',
				self.__try_execute_query,
				query=query,
				params=params,
				is_readonly=False
			)

			if not res:
				print_helper_global.print_message(MessageType.ERROR, 'Failed releasing the queue item')
				global_await_exit_action()


	class QueueWatcher:
		def __init__(self, proxy_server=None):
			self._current_agent_queue = None
			self._in_memory_threshold = 5
			self._in_memory_load_limit = 30
			self._in_db_threshold = 70
			self._agent_lock_time_seconds = 15

			if proxy_server:
				self._db_watcher = DatabaseWatcher(f'{socket.gethostname()}:{proxy_server}')
			else:
				self._db_watcher = DatabaseWatcher()

			self._current_queue_item = None

		def __lock_agent_operations(self):
			print_helper_global.print_message(MessageType.NOTIFICATION,
											  f'QueueWatcher is getting locked for {self._agent_lock_time_seconds} seconds')
			print_helper_global.print_message(MessageType.NOTIFICATION,
											  'Please use that time to exit the application safely if necessary')

			time.sleep(self._agent_lock_time_seconds)

			print_helper_global.print_message(MessageType.WARNING,
											  'QueueWatcher is now unlocked')
			print_helper_global.print_message(MessageType.WARNING,
											  'Exiting the application now may cause damage to the queues.')

			time.sleep(3)

		def __load_in_memory_queue(self):
			self.__lock_agent_operations()

			temp_queue = self._db_watcher.try_acquire_agent_queue(self._in_memory_load_limit)
			in_memory_threshold = self._in_memory_threshold

			if len(temp_queue) < in_memory_threshold:
				if self._db_watcher.update_queue_assignments(self._in_db_threshold):
					temp_queue = self._db_watcher.try_acquire_agent_queue(self._in_memory_load_limit)

					if len(temp_queue) < in_memory_threshold:
						print_helper_global.print_message(MessageType.ERROR, 'Failed updating the queue')
						global_await_exit_action()
				else:
					print_helper_global.print_message(MessageType.ERROR, 'Failed updating the queue. DB error')
					global_await_exit_action()

			self._current_agent_queue = deque(temp_queue)

		def __mark_prev_queue_item_as_processed(self):
			if self._current_queue_item:
				self._db_watcher.mark_queue_item_as_processed(self._current_queue_item)

		def fetch_agent_queue_item(self):
			self.__mark_prev_queue_item_as_processed()

			if not self._current_agent_queue:
				self.__load_in_memory_queue()

			self._current_queue_item = self._current_agent_queue.popleft()

			return self._current_queue_item

		def dispose(self):
			self._db_watcher.dispose()


	with open('../../process_to_terminate.txt', 'w') as file:
		file.write(str(os.getpid()))

	parser = argparse.ArgumentParser(description='Takes https proxy_server string')
	parser.add_argument('--proxy_server', type=str, help='proxy server address')

	args = parser.parse_args()

	proxy_server = args.proxy_server

	if proxy_server:
		print_helper_global.print_message(MessageType.NOTIFICATION, f'Using proxy server: {proxy_server}')
		proxies = {'https': proxy_server}

		request_manager_global = RequestManager(proxies)
		queue_watcher_global = QueueWatcher(proxy_server)
	else:
		request_manager_global = RequestManager()
		queue_watcher_global = QueueWatcher()

	time.sleep(3)

	while True:
		current_match = queue_watcher_global.fetch_agent_queue_item()

		print_helper_global.print_message(MessageType.NOTIFICATION,
										  f'Starting the processing of the match with ID: {current_match.match_id}')

		parse_manager = ParseManager(request_manager_global)
		_ = parse_manager.process_match(current_match.match_id)
		parse_manager.dispose()

except Exception as e:
	print_helper_global.print_message(MessageType.ERROR, f'Caught unhandled exception: {e}')

global_await_exit_action()
