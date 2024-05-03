import sqlite3
import json
from bs4 import BeautifulSoup


def get_player_heroes_meta_page_soup():
	with open('heroes_meta_page.htm', 'r', encoding='utf-8') as file:
		soup_str = file.read()

	return BeautifulSoup(soup_str, 'html.parser')


heroes_meta_page_soup = get_player_heroes_meta_page_soup()

heroes_stats_table_rows = heroes_meta_page_soup.find('tbody').find_all('tr')

conn = sqlite3.connect('DotaAIDB/dota_ai_od.db')
cursor = conn.cursor()

for hero_row in heroes_stats_table_rows:
	hero_stats = hero_row.find_all('td')
	hero_name = hero_stats[0].get('data-value')

	res_dict = {}

	res_dict['hero_pickrate_up_to_crusader'] = hero_stats[2].get('data-value')
	res_dict['hero_winrate_up_to_crusader'] = hero_stats[3].get('data-value')

	res_dict['hero_pickrate_archon'] = hero_stats[4].get('data-value')
	res_dict['hero_winrate_archon'] = hero_stats[5].get('data-value')

	res_dict['hero_pickrate_legend'] = hero_stats[6].get('data-value')
	res_dict['hero_winrate_legend'] = hero_stats[7].get('data-value')

	res_dict['hero_pickrate_ancient'] = hero_stats[8].get('data-value')
	res_dict['hero_winrate_ancient'] = hero_stats[9].get('data-value')

	res_dict['hero_pickrate_divine_immortal'] = hero_stats[10].get('data-value')
	res_dict['hero_winrate_divine_immortal'] = hero_stats[11].get('data-value')

	pickrates = [res_dict['hero_pickrate_up_to_crusader'], res_dict['hero_pickrate_archon'],
				 res_dict['hero_pickrate_legend'], res_dict['hero_pickrate_ancient'], res_dict['hero_pickrate_divine_immortal']]

	res_dict['hero_pickrate_average'] = sum([float(val) for val in pickrates]) / len(pickrates)

	winrates = [res_dict['hero_winrate_up_to_crusader'], res_dict['hero_winrate_archon'], res_dict['hero_winrate_legend'],
				res_dict['hero_winrate_ancient'], res_dict['hero_winrate_divine_immortal']]

	res_dict['hero_winrate_average'] = sum([float(val) for val in winrates]) / len(winrates)

	columns = ', '.join(f'{key} = ?' for key in res_dict.keys())
	query = f'UPDATE heroes SET {columns} WHERE name_local = ?'
	params = tuple(res_dict.values()) + (hero_name,)

	cursor.execute(query, params)
	conn.commit()

