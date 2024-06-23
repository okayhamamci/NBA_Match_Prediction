import os
import pandas as pd
from bs4 import BeautifulSoup
from io import StringIO

SCORE_DIR = "data/scores"
box_scores = os.listdir(SCORE_DIR)
box_scores = [os.path.join(SCORE_DIR, f) for f in box_scores if f.endswith(".html")]

def parse_html(box_score):
    with open(box_score, encoding="utf-8") as f:  
        html = f.read()
    soup = BeautifulSoup(html, features="html.parser")
    [s.decompose() for s in soup.select("tr.over_header")]
    [s.decompose() for s in soup.select("tr.thead")]
    return soup

def read_line_score(soup):
    line_score_html = str(soup.find(id="line_score"))
    line_score = pd.read_html(StringIO(line_score_html))[0]

    cols = list(line_score.columns)
    if len(cols) > 1:
        cols[0] = "team"
        cols[-1] = "total"
        line_score.columns = cols
        line_score = line_score[["team", "total"]]
    else:
        raise ValueError("Unexpected structure in line score table.")
    return line_score

def read_stats(soup, team, stat):
    stat_html = str(soup.find(id=f"box-{team}-game-{stat}"))
    df = pd.read_html(StringIO(stat_html), index_col=0)[0]
    df = df.apply(pd.to_numeric, errors="coerce")
    return df

def read_season_info(soup):
    nav = soup.select("#bottom_nav_container")[0]
    hrefs = [a["href"] for a in nav.find_all("a")]
    season = os.path.basename(hrefs[1]).split("_")[0]
    return season

base_cols = None
games = []

for box_score in box_scores:
    try:
        soup = parse_html(box_score)
    except UnicodeDecodeError as e:
        print(f"Error reading file {box_score}: {e}")
        continue

    try:
        line_score = read_line_score(soup)
    except ValueError as e:
        print(f"Error reading line score for {box_score}: {e}")
        continue

    if 'team' not in line_score.columns:
        print(f"'team' column not found in {box_score}")
        continue
    
    teams = list(line_score["team"])

    summaries = []
    for team in teams:
        basic = read_stats(soup, team, "basic")
        advanced = read_stats(soup, team, "advanced")

        totals = pd.concat([basic.iloc[-1, :], advanced.iloc[-1, :]])
        totals.index = totals.index.str.lower()

        max_values = pd.concat([basic.iloc[:-1, :].max(), advanced.iloc[:-1, :].max()])
        max_values.index = max_values.index.astype(str).str.lower() + "_max"  

        summary = pd.concat([totals, max_values])

        if base_cols is None:
            base_cols = list(summary.index.drop_duplicates(keep="first"))
            base_cols = [b for b in base_cols if "bpm" not in b]

        summary = summary[base_cols]

        summaries.append(summary)
    summary = pd.concat(summaries, axis=1).T

    game = pd.concat([summary, line_score], axis=1)

    game["home"] = [0, 1]
    game_opponent = game.iloc[::-1].reset_index()
    game_opponent.columns += "_opp"

    full_game = pd.concat([game, game_opponent], axis=1)

    full_game["season"] = read_season_info(soup)
    full_game["date"] = os.path.basename(box_score)[:8]
    full_game["date"] = pd.to_datetime(full_game["date"], format="%Y%m%d")

    full_game["won"] = full_game["total"] > full_game["total_opp"]
    games.append(full_game)

    if len(games) % 100 == 0:
        print(str(len(games)) + "  " + str(len(box_scores)))

games_df = pd.concat(games, ignore_index=True)
games_df.to_csv("nba_games.csv")
