import pandas
from sklearn.model_selection import TimeSeriesSplit
from sklearn.feature_selection import SequentialFeatureSelector
from sklearn.linear_model import RidgeClassifier
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import accuracy_score

rr = RidgeClassifier(alpha=1)
split = TimeSeriesSplit(n_splits=3)
sfs = SequentialFeatureSelector(rr, n_features_to_select=30, direction="forward", cv=split)
scaler = MinMaxScaler()

############################################################################

def back_test(data, model, predictors, start=1, step=1): #2 start
    all_predicts = []
    seasons = sorted(data["season"].unique())
    
    for i in range(start, len(seasons), step):
        season = seasons[i]
        
        train = data[data["season"] < season]
        test = data[data["season"] == season]
        
        model.fit(train[predictors], train["target"])
        preds = model.predict(test[predictors])
        preds = pandas.Series(preds, index=test.index)
        
        combined = pandas.concat([test["target"], preds], axis=1)
        combined.columns = ["actual", "prediction"]
        
        all_predicts.append(combined)
    return pandas.concat(all_predicts)

def target_add(team):
    team["target"] = team["won"].shift(-1) #Checks whether the team win the next game
    return team

def find_averages(team):
    numeric_cols = team.select_dtypes(include=[float, int]).columns
    rolling = team[numeric_cols].rolling(5).mean() #Finding the average performance of the team by looking its previous "5" matches
    return rolling

############################################################################

df = pandas.read_csv("nba_games.csv", index_col=0)
df = df.sort_values("date")
df = df.reset_index(drop=True)

del df["mp.1"]
del df["mp_opp.1"]
del df["index_opp"]

df = df.groupby("team", group_keys=False).apply(target_add)
df["target"][pandas.isnull(df["target"])] = 2 #Some values in thee "target" is null as teams play the fianl game in the season so we find these final matches and change the values of the "target" values to 2
df["target"] = df["target"].astype(int, errors="ignore")

future_games = df[df["target"] == 2]
df = df[df["target"] != 2]

nulls = pandas.isnull(df)
nulls = nulls.sum()
nulls = nulls[nulls > 0]
valid_cols = df.columns[~df.columns.isin(nulls.index)]
df = df[valid_cols].copy()

removed_cols = ["season", "date", "won", "target", "team", "team_opp"]
selected_cols = df.columns[~df.columns.isin(removed_cols)]

future_games_roll = future_games[list(selected_cols) + ["team", "season"]]
future_games_roll = future_games_roll.groupby(["team", "season"], group_keys=False).apply(find_averages)

df_roll = df[list(selected_cols) + ["won", "team", "season"]]
df_roll = df_roll.groupby(["team", "season"], group_keys=False).apply(find_averages)

rolling_cols = [f"{col}_5" for col in df_roll.columns]

df_roll.columns = rolling_cols
df = pandas.concat([df, df_roll], axis=1)
df = df.dropna()

# Directly shift columns and assign them
df["home_next"] = df.groupby("team")["home"].shift(-1)
df["team_opp_next"] = df.groupby("team")["team_opp"].shift(-1)
df["date_next"] = df.groupby("team")["date"].shift(-1)

full_df = df.merge(df[rolling_cols + ["team_opp_next", "date_next", "team"]], left_on=["team", "date_next"], right_on=["team_opp_next", "date_next"])

future_games_roll.columns = rolling_cols
future_games = pandas.concat([future_games, future_games_roll], axis=1)
future_games = future_games.dropna()

# Directly shift columns and assign them
future_games["home_next"] = future_games.groupby("team")["home"].shift(-1)
future_games["team_opp_next"] = future_games.groupby("team")["team_opp"].shift(-1)
future_games["date_next"] = future_games.groupby("team")["date"].shift(-1)


print(future_games["home_next"])

print("BEFORE MERGE")
print(future_games.head())

# Check unique values before merge
print("Unique values in `team` before merge:")
print(future_games["team"].unique())
print("Unique values in `team_opp_next` before merge:")
print(future_games["team_opp_next"].unique())

full_future_games = future_games.merge(future_games[rolling_cols + ["team_opp_next", "date_next", "team"]], left_on=["team", "date_next"], right_on=["team_opp_next", "date_next"])

print("AFTER MERGE")
print(full_future_games.head())
print(full_future_games.shape)

# Check unique values after merge
print("Unique values in `team` after merge:")
print(full_future_games["team"].unique())
print("Unique values in `team_opp_next` after merge:")
print(full_future_games["team_opp_next"].unique())

removed_cols = list(full_df.columns[full_df.dtypes == "object"]) + removed_cols
selected_cols = full_df.columns[~full_df.columns.isin(removed_cols)]

sfs.fit(full_df[selected_cols], full_df["target"])
predictors = list(selected_cols[sfs.get_support()])

predictions = back_test(full_df, rr, predictors)
predictions = predictions[predictions["actual"] != 2]

acc = accuracy_score(predictions["actual"], predictions["prediction"])
print("Accuracy Score: " + str(acc))

###############################################
            #### FUTURE GAMES ####

future_games = pandas.concat([future_games, future_games_roll], axis=1)
future_games = future_games.dropna()

print("Full future games before prediction:")
print(full_future_games.head())
print(full_future_games.shape)

if not full_future_games.empty:
    future_predicts = rr.predict(full_future_games[predictors])
    full_future_games["prediction"] = future_predicts
    print(full_future_games[["team", "team_opp_next", "date", "prediction"]])
else:
    print("No future games available for prediction.")
