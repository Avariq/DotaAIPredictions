PRAGMA foreign_keys = ON;

-- -----------------------------------------------------
-- Schema dota_ai
-- -----------------------------------------------------

-- -----------------------------------------------------
-- Schema dota_ai
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS matches (
  id TEXT NOT NULL PRIMARY KEY,
  datetime DATETIME NOT NULL,
  radiant_win BOOLEAN NOT NULL,
  duration INTEGER,
  radiant_score INTEGER,
  dire_score INTEGER,
  UNIQUE (id)
);

CREATE TABLE IF NOT EXISTS match_queue (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  match_id INTEGER NOT NULL UNIQUE,
  is_assigned BOOLEAN NOT NULL,
  agent TEXT,
  is_processed BOOLEAN NOT NULL
);

CREATE TABLE IF NOT EXISTS players (
  id TEXT NOT NULL PRIMARY KEY,
  UNIQUE (id)
);

CREATE TABLE IF NOT EXISTS heroes (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  name_local TEXT NOT NULL,
  hero_pickrate_average REAL,
  hero_winrate_average REAL,
  hero_pickrate_up_to_crusader REAL,
  hero_winrate_up_to_crusader REAL,
  hero_pickrate_archon REAL,
  hero_winrate_archon REAL,
  hero_pickrate_legend REAL,
  hero_winrate_legend REAL,
  hero_pickrate_ancient REAL,
  hero_winrate_ancient REAL,
  hero_pickrate_divine_immortal REAL,
  hero_winrate_divine_immortal REAL,
  UNIQUE (name)
);

CREATE TABLE IF NOT EXISTS public_matches (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  match_id INTEGER NOT NULL,
  start_time INTEGER NOT NULL,
  duration INTEGER NOT NULL,
  lobby_type INTEGER NOT NULL,
  game_mode INTEGER NOT NULL,
  avg_rank_tier INTEGER NOT NULL,
  num_rank_tier INTEGER NOT NULL,
  UNIQUE (match_id)
);

CREATE TABLE IF NOT EXISTS match_stats (
  match_id TEXT NOT NULL,
  player_id TEXT NOT NULL,
  hero_id TEXT NOT NULL,
  player_q_mmr_diff INTEGER,
  player_hero_winrate_overall REAL,
  player_hero_total_matches_played INTEGER,
  dire_winrate_all_time REAL,
  dire_games_played_all_time INTEGER,
  radiant_winrate_all_time REAL,
  radiant_games_played_all_time INTEGER,
  player_has_won BOOLEAN,
  player_heroes_pick_confidence_score INTEGER,
  player_time_played_all_matches INTEGER,
  player_winrate_over_time REAL NOT NULL,
  player_all_matches_played_number INTEGER,
  player_nickname TEXT,
  player_matches_abandoned INTEGER,
  player_matches_lost INTEGER,
  player_matches_won INTEGER,
  player_match_rank_initial TEXT,
  player_xpm INTEGER,
  player_gpm INTEGER,
  player_denies TEXT,
  player_lasthits TEXT,
  player_net INTEGER,
  player_assists_number INTEGER,
  player_deaths_number INTEGER,
  player_kills_number INTEGER,
  hero_lvl INTEGER,
  player_side TEXT,
  player_kills_average_all_matches REAL,
  player_deaths_average_all_matches REAL,
  player_assists_average_all_matches REAL,
  player_kda_average_all_matches REAL,
  player_gold_per_min_average_all_matches REAL,
  player_xp_per_min_average_all_matches REAL,
  player_last_hits_average_all_matches REAL,
  player_denies_average_all_matches REAL,
  player_lane_efficiency_pct_average_all_matches REAL,
  player_level_average_all_matches REAL,
  player_hero_damage_average_all_matches REAL,
  player_tower_damage_average_all_matches REAL,
  player_hero_healing_average_all_matches REAL,
  PRIMARY KEY (match_id, player_id, hero_id),
  FOREIGN KEY (match_id) REFERENCES matches(id) ON DELETE NO ACTION ON UPDATE NO ACTION,
  FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE NO ACTION ON UPDATE NO ACTION,
  FOREIGN KEY (hero_id) REFERENCES heroes(id) ON DELETE NO ACTION ON UPDATE NO ACTION
);
