#Fetching the data from API's
import requests
import pandas as pd
url='https://fantasy.premierleague.com/api/bootstrap-static/'
r = requests.get(url)
json_data = r.json()
players_df = pd.DataFrame(json_data['elements'])
print("Loading the data of first 5 players:")
print(players_df.head())
for column in players_df.columns:
    print(column)

#Cleanging the Data
selected_columns = ['web_name','team','element_type','now_cost','total_points','minutes','goals_scored','assists','form','influence','creativity','threat']
fpl_df=players_df[selected_columns].copy()
print("Load the newly created dataframe:")
print(fpl_df.head())

#Figuring out what element_type meant
print(fpl_df[fpl_df['web_name']=='A.Becker'])
print(fpl_df[fpl_df['web_name']=='M.Salah'])
print(fpl_df[fpl_df['web_name']=='Frimpong'])
print(fpl_df[fpl_df['web_name']=='Haaland'])

#Mapping the Positions to Names
position_mapping = {1:'GK',2:'DEF',3:'MID',4:'FWD'}
fpl_df['position'] = fpl_df['element_type'].map(position_mapping)
print(fpl_df[['web_name','position']].head())

#Actual value for the money
fpl_df['points_per_million'] = fpl_df['total_points'] / (fpl_df['now_cost']/10)
fpl_df_played = fpl_df[fpl_df['minutes']>90]
print("The Top 10 players:")
print(fpl_df_played.sort_values(by='points_per_million', ascending=False).head(10))

#Creating Temas Strength Scores
teams_df = pd.DataFrame(json_data['teams'])
teams_df = teams_df[['id','name','strength_overall_home','strength_overall_away']]
teams_df['strength'] = (teams_df['strength_overall_home']+teams_df['strength_overall_away']) / 2
print("Team Strength Rankings:")
print(teams_df.sort_values(by='strength', ascending=False))

#Merging Team strength with players
team_strength = teams_df[['id','name','strength']]
fpl_df = pd.merge(fpl_df,team_strength,left_on='team',right_on='id',how='left')
fpl_df.rename(columns={'name':'team_name'}, inplace=True)
fpl_df.drop(columns=['id'], inplace=True)
print("Merged Dataframes with team strength:")
print(fpl_df.head())

#Fixtures Data Fetching
fixtures_url = "https://fantasy.premierleague.com/api/fixtures/"
r = requests.get(fixtures_url)
if r.status_code == 200:
    try:
        # Only try to decode JSON if the request was successful
        fixtures_df = pd.DataFrame(r.json())
        print("Fixtures loaded successfully!")

        # --- Your existing code to process the fixtures would go here ---
        upcoming_fixtures = fixtures_df.loc[
            fixtures_df['finished'] == False,
            ['event', 'team_h', 'team_a', 'team_h_difficulty', 'team_a_difficulty']
        ]
        next_gameweek = upcoming_fixtures['event'].min()
        print(f"Fixtures for Gameweek {next_gameweek}:")
        print(upcoming_fixtures[upcoming_fixtures['event'] == next_gameweek])

    except requests.exceptions.JSONDecodeError:
        print("Error: Could not decode JSON. The FPL API might be updating or temporarily down.")
else:
    print(f"Error: API request failed with status code {r.status_code}")

#Merging Fixture difficulty
next_gameweek = upcoming_fixtures['event'].min()
next_gameweek_fixtures = upcoming_fixtures[upcoming_fixtures['event'] == next_gameweek]

opponent_map = {}
for index, row in next_gameweek_fixtures.iterrows():
    home_team_id = row['team_h']
    away_team_id = row['team_a']
    home_difficulty = row['team_h_difficulty']
    away_difficulty = row['team_a_difficulty']

    opponent_map[home_team_id] = {'opponent_team': away_team_id, 'difficulty':home_difficulty}
    opponent_map[away_team_id] = {'opponent_team': home_team_id, 'difficulty':away_difficulty}

fpl_df['opponent_team'] = fpl_df['team'].map(lambda team_id: opponent_map.get(team_id,{}).get('opponent_team'))
fpl_df['difficulty'] = fpl_df['team'].map(lambda team_id: opponent_map.get(team_id,{}).get('difficulty'))

print("Dataframe with all the features:")
print(fpl_df[['web_name','team_name','opponent_team','difficulty','points_per_million']].head())

# First, let's handle any potential missing values, just in case
fpl_df.fillna(0, inplace=True)

# The 'difficulty' score is inverted: 5 is hard, 1 is easy.
# We want a high score to be good, so let's create an 'easiness' score.
# A difficulty of 1 becomes 5, 2 becomes 4, etc.
fpl_df['easiness'] = 6 - fpl_df['difficulty']

# Now, we create our final recommendation score.
# We will give different weights to each feature based on importance.
# Form and fixture easiness are the most important for short-term decisions.
fpl_df['score'] = (
    fpl_df['form'].astype(float) * 0.3 +                      # 30% weight on current form
    fpl_df['points_per_million'].astype(float) * 0.2 +       # 20% weight on value
    (fpl_df['influence'].astype(float) +
     fpl_df['creativity'].astype(float) +
     fpl_df['threat'].astype(float)) * 0.2 +                 # 20% weight on underlying stats (ICT Index)
    fpl_df['easiness'].astype(float) * 0.3                      # 30% weight on fixture easiness
)

# Let's filter for players who are likely to play (more than 180 mins) and are not injured.
# (We don't have injury data, so we'll just filter by minutes for now)
recommendations = fpl_df[fpl_df['minutes'] > 150]

# --- GET YOUR RECOMMENDATIONS! ---

# Top 5 recommended Forwards (FWD)
print("Top 5 Recommended Forwards:")
print(recommendations[recommendations['position'] == 'FWD'].sort_values(by='score', ascending=False).head(5)[['web_name', 'team_name', 'score']])


# Top 5 recommended Midfielders (MID)
print("Top 5 Recommended Midfielders:")
print(recommendations[recommendations['position'] == 'MID'].sort_values(by='score', ascending=False).head(5)[['web_name', 'team_name', 'score']])


# Top 5 recommended Defenders (DEF)
print("Top 5 Recommended Defenders:")
print(recommendations[recommendations['position'] == 'DEF'].sort_values(by='score', ascending=False).head(5)[['web_name', 'team_name', 'score']])


#Top 3 recommended Goalkeepers (GK)
print("Top 3 Recommended GoalKeepers:")
print(recommendations[recommendations['position'] == 'GK'].sort_values(by='score',ascending=False).head(3)[['web_name','team_name','score']])