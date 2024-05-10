from enum import Enum
import colorama
from colorama import Fore, Style
import os
from datetime import datetime
import sys


colorama.init(convert=False)


def global_await_exit_action():
	print()
	_ = input('Press Enter to exit')
	print()

	sys.exit()


def safe_divide(a, b):
	try:
		result = a / b
	except ZeroDivisionError:
		result = -1
	return result


rank_tiers_to_ranks = {
	"10": "Herald IW",
	"11": "Herald I",
	"12": "Herald II",
	"13": "Herald III",
	"14": "Herald IV",
	"15": "Herald V",
	"20": "Guardian IW",
	"21": "Guardian I",
	"22": "Guardian II",
	"23": "Guardian III",
	"24": "Guardian IV",
	"25": "Guardian V",
	"30": "Crusader IW",
	"31": "Crusader I",
	"32": "Crusader II",
	"33": "Crusader III",
	"34": "Crusader IV",
	"35": "Crusader V",
	"40": "Archon IW",
	"41": "Archon I",
	"42": "Archon II",
	"43": "Archon III",
	"44": "Archon IV",
	"45": "Archon V",
	"50": "Legend IW",
	"51": "Legend I",
	"52": "Legend II",
	"53": "Legend III",
	"54": "Legend IV",
	"55": "Legend V",
	"60": "Ancient IW",
	"61": "Ancient I",
	"62": "Ancient II",
	"63": "Ancient III",
	"64": "Ancient IV",
	"65": "Ancient V",
	"70": "Divine IW",
	"71": "Divine I",
	"72": "Divine II",
	"73": "Divine III",
	"74": "Divine IV",
	"75": "Divine V",
	"80": "Immortal IW",
	"81": "Immortal I",
	"82": "Immortal II",
	"83": "Immortal III",
	"84": "Immortal IV",
	"85": "Immortal V"
}

ranks_to_mmr = {
  "Herald IW": [1, 1],
  "Herald I": [1, 154],
  "Herald II": [154, 308],
  "Herald III": [308, 462],
  "Herald IV": [462, 616],
  "Herald V": [616, 769],
  "Guardian IW": [770, 770],
  "Guardian I": [770, 924],
  "Guardian II": [924, 1078],
  "Guardian III": [1078, 1232],
  "Guardian IV": [1232, 1386],
  "Guardian V": [1386, 1540],
  "Crusader IW": [1540, 1540],
  "Crusader I": [1540, 1694],
  "Crusader II": [1694, 1848],
  "Crusader III": [1848, 2002],
  "Crusader IV": [2002, 2156],
  "Crusader V": [2156, 2310],
  "Archon IW": [2310, 2310],
  "Archon I": [2310, 2464],
  "Archon II": [2464, 2618],
  "Archon III": [2618, 2772],
  "Archon IV": [2772, 2926],
  "Archon V": [2926, 3080],
  "Legend IW": [3080, 3080],
  "Legend I": [3080, 3234],
  "Legend II": [3234, 3388],
  "Legend III": [3388, 3542],
  "Legend IV": [3542, 3696],
  "Legend V": [3696, 3850],
  "Ancient IW": [3850, 3850],
  "Ancient I": [3850, 4004],
  "Ancient II": [4004, 4158],
  "Ancient III": [4158, 4312],
  "Ancient IV": [4312, 4466],
  "Ancient V": [4466, 4620],
  "Divine IW": [4620, 4620],
  "Divine I": [4620, 4820],
  "Divine II": [4820, 5020],
  "Divine III": [5020, 5220],
  "Divine IV": [5220, 5420],
  "Divine V": [5420, 5620],
  "Immortal IW": [5621, 5621],
  "Immortal I": [5622, 5820],
  "Immortal II": [5820, 6020],
  "Immortal III": [6020, 6320],
  "Immortal IV": [6320, 6620]
}


class MessageType(Enum):
	ERROR = 'Error'
	WARNING = 'Warning'
	NOTIFICATION = 'Notification'
	SUCCESS = 'Success'
	INFO = 'Info'


class PrintHelper:
	def __init__(self, write_to_log, write_to_console = True):
		self._write_log = write_to_log
		self._write_to_console = write_to_console

	def print_message(self, message_type, message):
		if not self._write_to_console:
			return

		message_type = MessageType(message_type)

		if message_type == MessageType.ERROR:
			self.__print_error(message)
		elif message_type == MessageType.WARNING:
			self.__print_warning(message)
		elif message_type == MessageType.NOTIFICATION:
			self.__print_notification(message)
		elif message_type == MessageType.SUCCESS:
			self.__print_success(message)
		elif message_type == MessageType.INFO:
			self.__print_info(message)

		if self._write_log:
			self.print_to_log_file(message, message_type.value)

	@staticmethod
	def __print_warning(message):
		print(f'{Fore.YELLOW} {message} {Style.RESET_ALL}')

	@staticmethod
	def __print_error(message):
		print(f'{Fore.RED} {message} {Style.RESET_ALL}')

	@staticmethod
	def __print_notification(message):
		print(f'\n{Fore.CYAN} {message} {Style.RESET_ALL}\n')

	@staticmethod
	def __print_success(message):
		print(f'\n{Fore.LIGHTGREEN_EX} {message} {Style.RESET_ALL}\n')

	@staticmethod
	def __print_info(message):
		print(message)

	@staticmethod
	def print_to_log_file(message, message_type):
		now = datetime.now()
		timestamp = now.strftime('[%Y-%m-%d %H:%M:%S]')
		process_id = os.getpid()
		with open(f'parser_logs_{process_id}.txt', 'a') as f:
			f.write(f'{timestamp}:{message_type.upper()}: {message}' + '\n')