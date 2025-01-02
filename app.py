from flask import Flask, render_template, request, jsonify
import requests
import pandas as pd
import math
from itertools import combinations, permutations
from collections import defaultdict
import time
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import logging


app = Flask(__name__)

DEBUG = True  # Set this to True to enable debug logging
debug_messages = []  # List to store debug messages

# Cache variables
odds_data_cache = None
cache_timestamp = None
CACHE_EXPIRATION_TIME = 300  # Cache expiration time in seconds (5 minutes)



def log_debug(message):
    if DEBUG:
        debug_messages.append(message)
        print(message)

# Function to fetch and process odds data from HTML
def fetch_odds_data():
    url = 'https://www.sportytrader.com/en/odds/football/england/premier-league-49/'
    headers = {
        "Accept-Language": "en-GB,en;q=0.9",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise Exception(f"Error fetching the URL: {e}")

    soup = BeautifulSoup(response.content, 'html.parser')
    match_info = soup.select('div.cursor-pointer.border.rounded-md.mb-4.px-1.py-2.flex.flex-col.lg\\:flex-row.relative')

    rows = []
    current_date = datetime.now()

    for match in match_info:
        date_time = match.find('span', class_='text-sm text-gray-600 w-full lg:w-1/2 text-center dark:text-white').text.strip()
        log_debug(f"Raw date_time string: {date_time}")

        try:
            date_part, time_part = date_time.split(' - ')
            day, month_str = date_part.split()
            day = int(day)

            month_map = {
                'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
                'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
            }
            month = month_map[month_str[:3]]
            hour, minute = map(int, time_part.split(':'))
            year = current_date.year

            if month < current_date.month or (month == current_date.month and day < current_date.day):
                year += 1

            commence_time_uae = datetime(year, month, day, hour, minute, tzinfo=ZoneInfo('Asia/Dubai'))
            commence_time_gmt = commence_time_uae.astimezone(ZoneInfo('UTC'))
            commence_time = commence_time_gmt
            log_debug(f"Parsed date components - Day: {day}, Month: {month}, Year: {year}, Hour: {hour}, Minute: {minute}")
            log_debug(f"Created commence_time: {commence_time}")

        except Exception as e:
            log_debug(f"Error parsing date: {e}")
            continue

        teams = match.find('a').text.strip()
        home_team, away_team = teams.split(' - ')

        # Enhanced odds extraction with individual checks
        odds_spans = match.find_all('span', class_='px-1 h-booklogosm font-bold bg-primary-yellow text-white leading-8 rounded-r-md w-14 md:w-18 flex justify-center items-center text-base')
        odds = []

        # Find the preceding "1", "X", or "2" for each odd
        preceding_elements = match.find_all('span', class_='rounded-l-md px-1.5 bg-gray-100 h-booklogosm leading-8 font-medium')

        odds_dict = {}

        for i, el in enumerate(preceding_elements):
          if el.text.strip() in ('1','X','2'):
            try:
              odds_dict[el.text.strip()] = float(odds_spans[i].text.strip())
            except (IndexError, ValueError):
              odds_dict[el.text.strip()] = 99

        home_odds = odds_dict.get('1', 99)
        draw_odds = odds_dict.get('X', 99)
        away_odds = odds_dict.get('2', 99)
        
        avg_home_odds = home_odds
        avg_away_odds = away_odds

        if avg_home_odds < avg_away_odds:
            max_odd_type = "Home"
            max_home_away_odds = avg_home_odds
        else:
            max_odd_type = "Away"
            max_home_away_odds = avg_away_odds

        formatted_date = commence_time.strftime('%d/%m/%Y %H:%M')
        log_debug(f"Teams: {home_team} vs {away_team}, Raw date: {date_time}, Formatted date: {formatted_date}")

        rows.append({
            'home_team': home_team,
            'away_team': away_team,
            'commence_time': formatted_date,
            'commence_datetime': commence_time,
            'avg_home_odds': round(avg_home_odds, 2) if avg_home_odds is not None else None,
            'avg_away_odds': round(avg_away_odds, 2) if avg_away_odds is not None else None,
            'max_home_away_odds': round(max_home_away_odds, 2) if max_home_away_odds is not None else None,
            'max_odd_type': max_odd_type
        })

    rows.sort(key=lambda x: x['commence_datetime'])
    return rows

def fetch_and_process_odds():
    global odds_data_cache, cache_timestamp

    # Check if the cache is still valid
    if odds_data_cache is not None and (time.time() - cache_timestamp) < CACHE_EXPIRATION_TIME:
        log_debug("Using cached odds data.")
        return odds_data_cache

    # Fetch and parse odds data
    matches = fetch_odds_data()

    # Group matches by team repetition
    weekends = group_matches_by_team_repetition(matches)

    # Convert weekends to a dictionary with date ranges as keys
    weekends_dict = {}
    for i, weekend in enumerate(weekends):
        from_date = min(match['commence_datetime'] for match in weekend).date()
        to_date = max(match['commence_datetime'] for match in weekend).date()
        weekends_dict[(from_date, to_date)] = weekend

    log_debug(f"Weekend groups created: {weekends_dict.keys()}")
    log_debug(f"Number of unique weekend groups: {len(weekends_dict)}")

    odds_data_cache = weekends_dict
    cache_timestamp = time.time()

    return weekends_dict

def group_matches_by_team_repetition(matches):
    """
    Groups matches into weekends such that no team plays more than once in a single weekend.
    Additionally, moves any match to a future weekend group if its date is part of that group's dates.

    :param matches: List of match dictionaries with 'home_team', 'away_team', and 'commence_datetime'.
    :return: List of grouped weekends.
    """
    # Print the raw data supplied to the function
    print("Raw data supplied to the function:")
    for match in matches:
        print(match)

    # Initialize variables
    weekends = []  # List to store grouped weekends
    current_weekend = []  # List to store matches for the current weekend
    teams_played = set()  # Set to track teams that have played in the current weekend

    # Process matches to group them
    for match in matches:
        home_team = match['home_team']
        away_team = match['away_team']

        # Check if either team has already played in the current weekend
        if home_team in teams_played or away_team in teams_played:
            # Finalize the current weekend and start a new one
            weekends.append(current_weekend)
            current_weekend = []
            teams_played = set()

        # Add the current match to the current weekend
        current_weekend.append(match)
        teams_played.add(home_team)
        teams_played.add(away_team)

    # Add the last weekend group if it has any matches
    if current_weekend:
        weekends.append(current_weekend)

    # Adjust matches to ensure they are in the correct weekend group by date
    for i in range(len(weekends) - 1):
        current_group = weekends[i]
        future_groups = weekends[i + 1:]

        for match in current_group[:]:  # Copy the list to avoid modifying it during iteration
            match_date = match['commence_datetime']

            # Check future groups
            for future_group in future_groups:
                future_dates = [future_match['commence_datetime'] for future_match in future_group]
                if any(match_date == future_date for future_date in future_dates):
                    # Move the match to the future group
                    future_group.append(match)
                    current_group.remove(match)
                    print(f"Moved match {match} to a future group.")
                    break

    # Print the adjusted grouped data
    print("\nAdjusted data produced by the function:")
    for i, weekend in enumerate(weekends):
        print(f"Weekend {i + 1}:")
        for match in weekend:
            print(match)

    return weekends




@app.route('/')
def index():
    return render_template('index.html')

@app.route('/strategise', methods=['POST'])
def strategise():
    global debug_messages
    debug_messages = []  # Clear previous debug messages
    log_debug("Strategise endpoint triggered.")  # Log when the endpoint is hit

    data = request.get_json()
    log_debug(f"Received data: {data}")  # Log the incoming data

    num_people = data.get('num_people')
    used_teams_dict = data.get('used_teams_dict', {})
    previous_picks = data.get('previous_picks', [[] for _ in range(num_people)])
    selected_weekends = data.get('selected_weekends', [])

    log_debug(f"Number of people: {num_people}, Used teams: {used_teams_dict}, Previous picks: {previous_picks}")

    # Fetch and filter weekends based on selected_weekends
    all_weekends = fetch_and_process_odds()
    filtered_weekends = {k: v for k, v in all_weekends.items() if f"{k[0]} to {k[1]}" in selected_weekends}
    log_debug(f"Filtered weekends: {filtered_weekends.keys()}")

    best_paths, stats = find_best_consortium_paths(num_people, used_teams_dict, previous_picks, filtered_weekends)

    if best_paths is None:
        log_debug("No valid paths found.")
        return jsonify({'error': 'No valid paths found', 'stats': stats, 'debug_messages': debug_messages})

    log_debug("Best paths successfully found.")
    return jsonify({'best_paths': best_paths, 'stats': stats, 'debug_messages': debug_messages})

def find_best_consortium_paths(num_people, used_teams_dict=None, previous_picks=None, weekends=None):
    log_debug(f"Entering find_best_consortium_paths with used teams: {used_teams_dict} and previous picks: {previous_picks}")

    if weekends is None:
        weekends = fetch_and_process_odds()
    log_debug(f"Number of weekends detected: {len(weekends)}")

    all_paths = []
    best_total_odds = [float('inf')]
    path_counter = 0  # Initialize the path counter

    # Initialize paths and selected teams
    initial_paths, initial_selected_teams, initial_cumulative_log_odds = initialize_paths_and_teams(num_people, previous_picks, used_teams_dict)

    # Start the DFS with initial values including previous picks
    dfs_consortium(weekends, num_people, initial_selected_teams, initial_cumulative_log_odds, initial_paths, all_paths, best_total_odds, path_counter, used_teams_dict)

    if not all_paths:
        return None, {'total_paths_explored': 0, 'best_total_odds': None}

    best_paths, best_odds = min(all_paths, key=lambda x: x[1])
    return best_paths, {'total_paths_explored': len(all_paths), 'best_total_odds': best_odds}

def initialize_paths_and_teams(num_people, previous_picks, used_teams_dict):
    # Robust initialization with error checking
    initial_paths = []
    initial_selected_teams = []
    initial_cumulative_log_odds = 0

    for player_picks in previous_picks or [[] for _ in range(num_people)]:
        # Validate each pick
        validated_picks = []
        player_teams = set()
        player_log_odds = 0

        for pick in player_picks:
            if len(pick) != 2 or not isinstance(pick[1], (int, float)) or pick[1] <= 0:
                raise ValueError(f"Invalid pick: {pick}")
            
            team, odds = pick
            if team in player_teams:
                raise ValueError(f"Duplicate team for player: {team}")
            
            validated_picks.append(pick)
            player_teams.add(team)
            player_log_odds += math.log(odds)

        initial_paths.append(validated_picks)
        initial_selected_teams.append(player_teams)
        initial_cumulative_log_odds += player_log_odds

    return initial_paths, initial_selected_teams, initial_cumulative_log_odds

def dfs_consortium(weekends, num_people, selected_teams, cumulative_log_odds, paths, all_paths, best_total_odds, path_counter, used_teams_dict):
    start_time = time.time()  # Start the timer

    def dfs(week_index, selected_teams, cumulative_log_odds, paths):
        nonlocal path_counter

        # Base case: all weekends processed
        if week_index >= len(weekends):
            total_odds = math.exp(cumulative_log_odds)
            if total_odds < best_total_odds[0]:
                best_total_odds[0] = total_odds
                all_paths.clear()
                all_paths.append((paths, total_odds))
                elapsed_time = time.time() - start_time
                log_debug(f"New best total odds found: {total_odds}")
                log_debug(f"Team picks for minimized odds: {paths}")
                log_debug(f"Paths tried: {path_counter}")
                log_debug(f"Elapsed time for this best path: {elapsed_time:.2f} seconds")

            elif total_odds == best_total_odds[0]:
                all_paths.append((paths, total_odds))
            return

        # Early termination if current path is already worse than the best found
        if cumulative_log_odds > math.log(best_total_odds[0]):
            return

        # Get the weekend key based on the index
        weekend_key = list(weekends.keys())[week_index]
        matches = weekends[weekend_key]

        # Sort matches by the best (lowest) odds
        matches.sort(key=lambda match: min(match['avg_home_odds'], match['avg_away_odds']))

        picks_for_week = [{'team': match['home_team'], 'odds': match['avg_home_odds']} for match in matches]
        picks_for_week += [{'team': match['away_team'], 'odds': match['avg_away_odds']} for match in matches]

        if len(picks_for_week) >= num_people:
            for picks_combination in combinations(picks_for_week, num_people):
                teams = [pick['team'] for pick in picks_combination]

                # Check for duplicate teams within the current week's picks
                if len(set(teams)) < num_people:
                    continue

                # Strict check against used teams for each player
                valid = True
                for i, team in enumerate(teams):
                    # Check against used teams for this specific player
                    player_used_teams = used_teams_dict.get(str(i), [])
                    if (team in player_used_teams or 
                        team in selected_teams[i] or 
                        any(team == pick[0] for pick in paths[i])):
                        valid = False
                        break

                if not valid:
                    continue

                for picks in permutations(picks_combination, num_people):
                    # Additional comprehensive validation
                    valid = True
                    for i in range(num_people):
                        # Ensure no team is repeated for a player in any week
                        player_used_teams = used_teams_dict.get(str(i), [])
                        if (picks[i]['team'] in player_used_teams or 
                            picks[i]['team'] in selected_teams[i] or 
                            picks[i]['team'] in [pick[0] for pick in paths[i]]):
                            valid = False
                            break

                    if not valid:
                        continue

                    new_selected_teams = [set(selected_teams[i]) for i in range(num_people)]
                    new_paths = [list(paths[i]) for i in range(num_people)]
                    for i in range(num_people):
                        new_selected_teams[i].add(picks[i]['team'])
                        new_paths[i].append((picks[i]['team'], picks[i]['odds']))

                    new_cumulative_log_odds = cumulative_log_odds + sum(math.log(picks[i]['odds']) for i in range(num_people))
                    path_counter += 1

                    dfs(week_index + 1, new_selected_teams, new_cumulative_log_odds, new_paths)

    dfs(0, selected_teams, cumulative_log_odds, paths)

    total_elapsed_time = time.time() - start_time
    log_debug(f"Total paths tried: {path_counter}")
    log_debug(f"Total elapsed time: {total_elapsed_time:.2f} seconds")

@app.route('/fetch_odds', methods=['GET'])
def fetch_odds():
    # Call the function that fetches and processes the odds data
    weekends_data = fetch_and_process_odds()

    # Convert tuple keys (weekend ranges) to strings before returning the JSON response
    weekends_data_str_keys = {
        f"{k[0]} to {k[1]}": v for k, v in weekends_data.items()
    }

    # Return the modified dictionary as a JSON response
    return jsonify(weekends_data_str_keys)


if __name__ == '__main__':
    app.run(debug=True)