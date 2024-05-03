import sqlite3
import json
import os
import sys
from colorama import Fore, Style
from datetime import datetime


def print_notification(message):
	print(f'\n{Fore.CYAN} {message} {Style.RESET_ALL}\n')
	print_to_log_file(message, 'notification')


def print_success(message):
	print(f'\n{Fore.LIGHTGREEN_EX} {message} {Style.RESET_ALL}\n')
	print_to_log_file(message, 'success')


def print_warning(message):
	print(f'{Fore.YELLOW} {message} {Style.RESET_ALL}')
	print_to_log_file(message, 'warning')


def print_to_log_file(message, message_type):
	now = datetime.now()
	timestamp = now.strftime('[%Y-%m-%d %H:%M:%S]')
	with open('../match_queue_parser_log.txt', 'a') as f:
		f.write(f'{timestamp}:{message_type.upper()}: {message}' + '\n')


directory = 'match_queue_response_dump'
for filename in os.listdir(directory):
	filepath = os.path.join(directory, filename)

	with open(filepath, 'r', encoding='utf-8') as file:
		data = json.load(file)

	print_notification(f'Working on {filepath}')

	matches = data['rows']

	conn = sqlite3.connect('../../DotaAIDB/dota_ai_od.db')
	cursor = conn.cursor()

	counter = 0
	records_to_parse = data['rowCount']

	for match in matches:
		counter += 1

		res_dict = {}

		res_dict['match_id'] = match['match_id']
		res_dict['start_time'] = match['start_time']
		res_dict['duration'] = match['duration']
		res_dict['lobby_type'] = match['lobby_type']
		res_dict['game_mode'] = match['game_mode']
		res_dict['avg_rank_tier'] = match['avg_rank_tier']
		res_dict['num_rank_tier'] = match['num_rank_tier']

		print(res_dict)

		columns = ', '.join(res_dict.keys())
		placeholders = ', '.join(['?' for _ in res_dict])

		query = f'INSERT INTO public_matches ({columns}) VALUES ({placeholders})'
		params = tuple(res_dict.values())

		try:
			cursor.execute(query, params)
			conn.commit()

			print_success(f'Rows processed: {counter}/{records_to_parse}')
		except sqlite3.Error as e:
			print_warning(f'Skipping iteration: {e}')

	conn.close()






