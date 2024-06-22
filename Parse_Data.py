import os
import pandas
from bs4 import BeautifulSoup

SCORE_DIR = "data/scores"
box_scores = os.listdir(SCORE_DIR)

box_scores = [os.path.join(SCORE_DIR, f) for f in box_scores if f.endswith(".html")]

def parse_html(box_score):
    with open(box_score) as f:
        html = f.read()
    
    soup = BeautifulSoup(html, features="html.parser")
    [s.decompose() for s in soup.select("tr.over_header")]
    [s.decompose() for s in soup.select("tr.thead")]
    return soup

def read_line_score(soup):
    line_score = pandas.read_html(str(soup), attrs={"id": "line_score"})
    cols = list(line_score.columns)
    cols[0] = "team"
    cols[-1] = "total"
    line_score.columns = cols
    
    line_score = line_score[["team", "total"]]
    return line_score
    
def read_stats(soup, team, stat):
    df = pandas.read_html(str(soup), attrs={"id": f"box-{team}-game-{stat}"}, index_col=0)[0]
    df = df.apply(pandas.to_numeric, errors="coerce")
    return df

def read_season_info(soup):
    nav = soup.select("#bottom_nav_container")[0]
    hrefs = [a["href"] for a in nav.find_all("a")]
    season = os.path.basename(hrefs[1]).split("_")[0]
    return season
    
base_cols = None  
games = []

for box_score in box_scores:
    soup = parse_html(box_score)
    line_score = pandas.read_html(str(soup), attrs={"id": "line_score"})[0]
    teams = list(line_score["team"])

    summaries = []
    for team in teams:
        basic = read_stats(soup, team, "basic")
        advanced = read_stats(soup, team, "advanced")
        
        totals = pandas.concat([basic.iloc[-1,:], advanced.iloc[-1,:]])
        totals.index = totals.index.str.lower()
        
        max_values = pandas.concat([basic.iloc[:-1,:].max(), advanced.iloc[:-1,:].max()])
        max_values.index = max_values.str.lower() + "_max"

        summary = pandas.concat([totals, max_values])
        
        if base_cols is None:
            base_cols = list(summary.index.drop_duplicates(keep="first"))
            base_cols = [b for b in base_cols if "bpm" not in b]
            
        summary = summary[base_cols]
        
        summaries.append(summary)
    summary = pandas.concat(summaries, axis=1).T

    game = pandas.concat([summary, line_score], axis=1)

    game["home"] = [0, 1]
    game_opponent = game.iloc[::-1].reset_index()
    game_opponent.columns += "_opp"

    full_game = pandas.concat([game, game_opponent], axis=1)

    full_game["season"] = read_season_info(soup)
    full_game["date"] = os.path.basename(box_score)[:8]
    full_game["date"] = pandas.to_datetime(full_game["date"], format="%Y%m%d")

    full_game["won"] = full_game["total"] > full_game["total_opp"]
    games.append(full_game)
    
    if len(games) % 100 == 0:
        print(str(len(games)) + "  " + str(len(box_scores)))

games_df = pandas.concat(games, ignore_index=True)