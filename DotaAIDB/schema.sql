PRAGMA foreign_keys = ON;

-- -----------------------------------------------------
-- Schema dota_ai
-- -----------------------------------------------------

-- -----------------------------------------------------
-- Schema dota_ai
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS matches (
  id TEXT NOT NULL PRIMARY KEY,
  match_link TEXT NOT NULL,
  match_datetime DATETIME NOT NULL,
  match_outcome TEXT NOT NULL,
  match_duration TEXT,
  match_radiant_score INTEGER,
  match_dire_score INTEGER,
  UNIQUE (id),
  UNIQUE (match_link)
);

CREATE TABLE IF NOT EXISTS match_queue (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  match_link TEXT NOT NULL UNIQUE,
  is_assigned BOOLEAN NOT NULL,
  agent TEXT
);

CREATE TABLE IF NOT EXISTS players (
  id TEXT NOT NULL PRIMARY KEY,
  player_link TEXT NOT NULL,
  player_visible INTEGER NOT NULL,
  UNIQUE (id),
  UNIQUE (player_link)
);

CREATE TABLE IF NOT EXISTS heroes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  hero_name TEXT NOT NULL,
  hero_link TEXT NOT NULL,
  UNIQUE (hero_name),
  UNIQUE (hero_link)
);

CREATE TABLE IF NOT EXISTS match_stats (
  match_id TEXT NOT NULL,
  player_id TEXT NOT NULL,
  hero_id TEXT NOT NULL,
  hero_winrate_overall REAL NOT NULL,
  hero_pickrate_overall REAL NOT NULL,
  hero_winrate_for_rank REAL,
  hero_pickrate_for_rank REAL,
  player_q_predicted_mmr INTEGER,
  player_hero_kda_ratio_overall REAL,
  player_hero_winrate_overall REAL,
  player_hero_total_matches_played INTEGER,
  dire_time_played TEXT,
  dire_winrate_all_time REAL,
  dire_games_played_all_time INTEGER,
  radiant_time_played TEXT,
  radiant_winrate_all_time REAL,
  radiant_games_played_all_time INTEGER,
  player_time_played_all_matches INTEGER,
  player_winrate_over_time_stats_page REAL,
  player_winrate_over_time_main_page REAL NOT NULL,
  player_all_matches_played_number INTEGER,
  player_nickname TEXT,
  player_matches_abandoned INTEGER,
  player_matches_lost INTEGER,
  player_matches_won INTEGER,
  player_match_rank_initial TEXT,
  player_sentries TEXT,
  player_observers TEXT,
  player_building_dmg_dealt TEXT,
  player_heal TEXT,
  player_damage_dealt TEXT,
  player_xpm INTEGER,
  player_gpm INTEGER,
  player_denies TEXT,
  player_lasthits TEXT,
  player_net INTEGER,
  player_assists_number INTEGER,
  player_deaths_number INTEGER,
  player_kills_number INTEGER,
  player_lane_result TEXT,
  player_lane_option2 TEXT,
  player_lane TEXT,
  player_role TEXT,
  hero_lvl INTEGER,
  player_side TEXT,
  week_matches_played INTEGER,
  week_matches_won INTEGER,
  week_winrate REAL,
  week_days_active INTEGER,
  week_activity_coef REAL,
  month_matches_played INTEGER,
  month_matches_won INTEGER,
  month_winrate REAL,
  month_days_active INTEGER,
  month_activity_coef REAL,
  PRIMARY KEY (match_id, player_id, hero_id),
  FOREIGN KEY (match_id) REFERENCES matches(id) ON DELETE NO ACTION ON UPDATE NO ACTION,
  FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE NO ACTION ON UPDATE NO ACTION,
  FOREIGN KEY (hero_id) REFERENCES heroes(id) ON DELETE NO ACTION ON UPDATE NO ACTION
);
