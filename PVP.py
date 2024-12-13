import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
matplotlib.use('Agg')  # Use a non-GUI backend
import seaborn as sns
import os

# Set up data and static paths
DATA_FOLDER = "data/"
STATIC_FOLDER = os.path.join('static', 'graphs')
os.makedirs(STATIC_FOLDER, exist_ok=True)

# Load datasets
try:
    matches = pd.read_csv(os.path.join(DATA_FOLDER, 'atp_matches_till_2022.csv'))
    players = pd.read_csv(os.path.join(DATA_FOLDER, 'atp_players_till_2022.csv'))
    rankings = pd.read_csv(os.path.join(DATA_FOLDER, 'atp_rankings_till_2022.csv'))
except FileNotFoundError as e:
    raise FileNotFoundError(f"Error loading data files: {e}")

def save_graph(fig, player1_name, player2_name, graph_name):
    """
    Save the graph to the static folder with the correct file name.
    """
    sanitized_player1 = player1_name.replace(' ', '_').lower()
    sanitized_player2 = player2_name.replace(' ', '_').lower()
    graph_dir = os.path.join(STATIC_FOLDER, f"{sanitized_player1}_vs_{sanitized_player2}")
    os.makedirs(graph_dir, exist_ok=True)
    
    graph_path = os.path.join(graph_dir, f"{graph_name}.png")
    fig.savefig(graph_path)
    plt.close(fig)  # Close the figure to free memory
    return graph_path

# Function to sanitize filenames
def sanitize_filename(name):
    return name.replace(" ", "_").replace(".", "").lower()

# Function to get player stats and generate visualizations
def get_player_stats_with_visuals(player1_name, player2_name):
    players['full_name'] = players['name_first'] + ' ' + players['name_last']

    # Validate if players exist in the dataset
    if player1_name not in players['full_name'].values:
        raise ValueError(f"Player '{player1_name}' not found in the players dataset.")
    if player2_name not in players['full_name'].values:
        raise ValueError(f"Player '{player2_name}' not found in the players dataset.")

    # Fetch player details
    player1_info = players[players['full_name'] == player1_name].iloc[0]
    player2_info = players[players['full_name'] == player2_name].iloc[0]
    
    player1_id = player1_info['player_id']
    player2_id = player2_info['player_id']
    
    player1_nationality = player1_info['ioc']
    player2_nationality = player2_info['ioc']

    # Filter matches for players
    player1_matches = matches[(matches['winner_id'] == player1_id) | (matches['loser_id'] == player1_id)]
    player2_matches = matches[(matches['winner_id'] == player2_id) | (matches['loser_id'] == player2_id)]

    # Head-to-head record
    head_to_head = matches[((matches['winner_id'] == player1_id) & (matches['loser_id'] == player2_id)) |
                           ((matches['winner_id'] == player2_id) & (matches['loser_id'] == player1_id))]
    player1_wins = head_to_head[head_to_head['winner_id'] == player1_id].shape[0]
    player2_wins = head_to_head[head_to_head['winner_id'] == player2_id].shape[0]

    # Win percentage
    player1_total_wins = player1_matches[player1_matches['winner_id'] == player1_id].shape[0]
    player1_total_matches = player1_matches.shape[0]
    player1_win_percentage = (player1_total_wins / player1_total_matches) * 100 if player1_total_matches > 0 else 0

    player2_total_wins = player2_matches[player2_matches['winner_id'] == player2_id].shape[0]
    player2_total_matches = player2_matches.shape[0]
    player2_win_percentage = (player2_total_wins / player2_total_matches) * 100 if player2_total_matches > 0 else 0

    # Rankings and career-high
    player1_rank_history = rankings[rankings['player'] == player1_id].copy()
    player2_rank_history = rankings[rankings['player'] == player2_id].copy()

    player1_rank_history['date'] = pd.to_datetime(player1_rank_history['ranking_date'], format='%Y%m%d')
    player2_rank_history['date'] = pd.to_datetime(player2_rank_history['ranking_date'], format='%Y%m%d')

    player1_current_rank = player1_rank_history['rank'].iloc[-1] if not player1_rank_history.empty else 'N/A'
    player2_current_rank = player2_rank_history['rank'].iloc[-1] if not player2_rank_history.empty else 'N/A'
    
    player1_career_high_rank = player1_rank_history['rank'].min() if not player1_rank_history.empty else 'N/A'
    player2_career_high_rank = player2_rank_history['rank'].min() if not player2_rank_history.empty else 'N/A'

    # Wins by surface
    surfaces = ['Hard', 'Clay', 'Grass']
    player1_wins_by_surface = player1_matches[player1_matches['winner_id'] == player1_id]['surface'].value_counts()
    player2_wins_by_surface = player2_matches[player2_matches['winner_id'] == player2_id]['surface'].value_counts()

    # Unique folder for graphs
    folder_name = f"{sanitize_filename(player1_name)}_vs_{sanitize_filename(player2_name)}"
    graph_folder = os.path.join(STATIC_FOLDER, folder_name)
    os.makedirs(graph_folder, exist_ok=True)

    # Graphs
    graph_paths = {}

    # Head-to-Head Wins
    fig = plt.figure(figsize=(6, 4))
    sns.barplot(x=[player1_name, player2_name], y=[player1_wins, player2_wins])
    plt.title(f"Head-to-Head Wins: {player1_name} vs {player2_name}")
    graph_paths['head_to_head'] = save_graph(fig, player1_name, player2_name, "head_to_head")


    # Win Percentage
    fig = plt.figure(figsize=(6, 4))
    sns.barplot(x=[player1_name, player2_name], y=[player1_win_percentage, player2_win_percentage])
    plt.title("Win Percentage Comparison")
    graph_paths['win_percentage'] = save_graph(fig, player1_name, player2_name, "win_percentage")


    # Wins by Surface
    win_surface_df = pd.DataFrame({
        'Surface': surfaces,
        f'{player1_name} Wins': [player1_wins_by_surface.get(surface, 0) for surface in surfaces],
        f'{player2_name} Wins': [player2_wins_by_surface.get(surface, 0) for surface in surfaces]
    })

    # Set Surface as index for better plotting
    win_surface_df = win_surface_df.set_index('Surface')

    # Create a new figure for the plot
    fig, ax = plt.subplots(figsize=(8, 5))

    # Plot the bar chart
    win_surface_df.plot(kind='bar', ax=ax, stacked=False, colormap='viridis')

    # Add labels and title
    ax.set_title(f"Wins by Surface: {player1_name} vs {player2_name}")
    ax.set_ylabel("Number of Wins")
    ax.set_xlabel("Surface")

    # Save the graph
    graph_paths['wins_by_surface'] = save_graph(fig, player1_name, player2_name, "wins_by_surface")



    # Ranking Progression Over Time
    fig = plt.figure(figsize=(10, 6))
    plt.plot(player1_rank_history['date'], player1_rank_history['rank'], label=player1_name)
    plt.plot(player2_rank_history['date'], player2_rank_history['rank'], label=player2_name)
    plt.gca().invert_yaxis()
    plt.title("Ranking Progression Over Time")
    graph_paths['ranking_progression'] = save_graph(fig, player1_name, player2_name, "ranking_progression")

    # Compile stats
    comparison = {
        'Nationality': [player1_nationality, player2_nationality],
        'Total Matches Played': [player1_total_matches, player2_total_matches],
        'Total Wins': [player1_total_wins, player2_total_wins],
        'Win Percentage': [player1_win_percentage, player2_win_percentage],
        'Current Rank': [player1_current_rank, player2_current_rank],
        'Career-High Rank': [player1_career_high_rank, player2_career_high_rank],
        'Head-to-Head Wins': [player1_wins, player2_wins],
    }
    for key, path in graph_paths.items():
        graph_paths[key] = path.replace("\\", "/")

    return comparison, graph_paths
