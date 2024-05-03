import sqlite3
import sys
from colorama import Fore, Style
from datetime import datetime


def print_to_log_file(message, message_type):
	now = datetime.now()
	timestamp = now.strftime('[%Y-%m-%d %H:%M:%S]')
	with open('../match_queue_filler_log.txt', 'a') as f:
		f.write(f'{timestamp}:{message_type.upper()}: {message}' + '\n')


def print_warning(message):
	print(f'{Fore.YELLOW} {message} {Style.RESET_ALL}')
	print_to_log_file(message, 'warning')


def print_error(message):
	print(f'{Fore.RED} {message} {Style.RESET_ALL}')
	print_to_log_file(message, 'error')


def print_notification(message):
	print(f'\n{Fore.CYAN} {message} {Style.RESET_ALL}\n')
	print_to_log_file(message, 'notification')


def print_success(message):
	print(f'\n{Fore.LIGHTGREEN_EX} {message} {Style.RESET_ALL}\n')
	print_to_log_file(message, 'success')



conn = sqlite3.connect('../../DotaAIDB/dota_ai_od.db')
cursor = conn.cursor()

query = "SELECT match_id FROM public_matches WHERE avg_rank_tier < 60 AND avg_rank_tier >= 32 AND start_time >= strftime('%s', 'now', '-6 months') ORDER BY avg_rank_tier ASC"
cursor.execute(query)
all_matches_to_add = cursor.fetchall()

limit = len(all_matches_to_add)
counter = 0

for match in all_matches_to_add:
	counter += 1

	match_id = match[0]

	query = f"INSERT INTO match_queue (match_id, is_assigned, agent, is_processed) VALUES ({match_id}, FALSE, NULL, FALSE)"

	try:
		cursor.execute(query)
		conn.commit()

		print_success(f'Added match_id: {match_id}. Progress: {counter}/{limit}')
	except sqlite3.Error as e:
		print_error(e)
		_ = input('........')
		sys.exit()
