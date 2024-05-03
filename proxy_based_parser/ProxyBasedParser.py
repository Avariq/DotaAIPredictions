import subprocess
import time
import psutil


def run_parse_with_proxy():
	proxies = ['35.185.196.38:3128', '195.154.184.80:8080']

	main_parser_path = 'D:/DotaPredictionsAI/dist/OpenDotaParser.exe'

	command = f'cmd.exe /K {main_parser_path} --proxy_server {proxies[0]}'

	subprocess.Popen(command, creationflags=subprocess.CREATE_NEW_CONSOLE)

	time.sleep(60 * 60 * 2)  # 2 hours

	with open('process_to_terminate.txt', 'r') as file:
		pid = int(file.readline())

	proc = psutil.Process(pid)
	proc.terminate()

	time.sleep(10)

	run_parse_with_proxy()

time.sleep(60 * 20)
run_parse_with_proxy()