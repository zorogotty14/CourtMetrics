from flask import Flask, render_template, jsonify, abort, url_for, request, redirect, flash
import yt_dlp as youtube_dl
import os
import uuid
import requests,json
from PVP import get_player_stats_with_visuals
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_migrate import Migrate
from models import db  # Import SQLAlchemy instance
from models.user import User  # Import the User model
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)

# Flask Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:Test1234!@localhost:5434/capstone_project'
app.config['SECRET_KEY'] = 'capstone-project'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Initialize Flask-Migrate for database migrations
migrate = Migrate(app, db)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

with app.app_context():
    # Access `current_user` or interact with `login_manager`
    db.create_all()

# Define user loader
@login_manager.user_loader
def load_user(user_id):
    from models.user import User
    return User.query.get(int(user_id))

# Define your Azure OpenAI endpoint and API key
ENDPOINT = "https://capstone-project.cognitiveservices.azure.com/openai/deployments/gpt-4o/chat/completions?api-version=2024-08-01-preview"
API_KEY = "1BMz0wKtTR35QAuocSJmZGR6nSut2OFfq9gOUOPbNtcr3vTmnupWJQQJ99ALAC4f1cMXJ3w3AAAAACOGqweh"  # Replace with your actual API key



# Directories to save uploaded videos and YouTube downloads
UPLOAD_FOLDER = "static/uploads"
YOUTUBE_FOLDER = "static/videos"
OUTPUT_FOLDER = "static/output_videos"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
if not os.path.exists(YOUTUBE_FOLDER):
    os.makedirs(YOUTUBE_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER

def fetch_gpt_player_data(player1_name, player2_name):
    # Headers for the request
    headers = {
        "Content-Type": "application/json",
        "api-key": API_KEY,
    }

    payload = {
    "messages": [
        {
        "role": "system",
        "content": (
            f"I am building a tennis analytics website. I need a detailed report comparing two players: {player1_name} and {player2_name}. "
            "\n\nPlease provide the following details in **strict JSON format**. Ensure all fields conform to proper JSON standards (e.g., use double quotes for keys and values, avoid comments, and provide `null` for missing data)."
            "\n\n### Required Sections"
            "\n1. **Player Overview**: Include the following details for each player:"
            "\n   - Full name"
            "\n   - Nationality"
            "\n   - Date of birth (in `YYYY-MM-DD` format)"
            "\n   - Height (in cm)"
            "\n   - Weight (in kg)"
            "\n   - Playing hand (e.g., Right-handed or Left-handed)"
            "\n   - Playing style (brief description)"
            "\n   - Turned pro year"
            "\n\n2. **Career Highlights**:"
            "\n   - Total career titles"
            "\n   - Grand Slam wins"
            "\n   - Olympic medals (as a nested object with `total` and `details`)"
            "\n   - Career prize money (in USD)"
            "\n   - Career-high ranking"
            "\n   - Current ranking"
            "\n   - Year-end No. 1 rankings (as an array of years)"
            "\n\n3. **Head-to-Head Records**:"
            "\n   - Total matches played"
            "\n   - Wins by each player"
            "\n   - Wins by surface (as a nested object: Hard, Clay, Grass)"
            "\n   - Historical trends (brief summary)"
            "\n\n4. **Performance Statistics**:"
            "\n   - Overall win percentage"
            "\n   - Service stats (nested object with `aces`, `doubleFaults`, `firstServePercentage`, `firstServePointsWon`, and `secondServePointsWon`)"
            "\n   - Return stats (nested object with `firstServeReturnPointsWon` and `secondServeReturnPointsWon`)"
            "\n   - Tiebreak record"
            "\n\n5. **Tournament History**:"
            "\n   - Grand Slam performances (as a nested object with `AustralianOpen`, `FrenchOpen`, `Wimbledon`, `USOpen`)"
            "\n   - ATP Finals titles"
            "\n   - Masters titles"
            "\n\n6. **Ranking Progression**:"
            "\n   - Timeline of ranking changes for each player (as an array of objects with `year` and `ranking`)"
            "\n\n7. **Historical Trends**:"
            "\n   - Match-win streaks (longest streak for each player)"
            "\n   - Performance against top-10 players (win percentage)"
            "\n   - Notable upsets (brief description)"
            "\n\n### Formatting Requirements"
            "\n- Provide the response in valid JSON format."
            "\n- If any data is missing or unavailable, use `null` or an empty array as appropriate."
            "\n- Use camelCase for all keys (e.g., `fullName`, `totalCareerTitles`)."
        )
        }
    ],
    "temperature": 0.7,
    "top_p": 0.95,
    "max_tokens": 2000
    }

    # Make the POST request to the Azure OpenAI endpoint
    try:
        response = requests.post(ENDPOINT, headers=headers, json=payload)
        response.raise_for_status()  # Will raise an HTTPError for bad responses (4xx or 5xx)
        
        # Parse the content field from the response
        response_json = response.json()
        response_content = response_json['choices'][0]['message']['content']
        # print(response_content)
        # Clean and parse the JSON content
        cleaned_content = response_content.strip("```json\n").strip("```")
        # print(cleaned_content)
        # Decode bytes to string and write the JSON response to a file
        with open("player_data.json", "w") as file:
            file.write(cleaned_content)
    except requests.RequestException as e:
        print(f"Failed to make the request. Error: {e}")
    
    return jsonify(cleaned_content)

# Convert player names to the expected key format (e.g., "Rafael Nadal" -> "rafaelNadal")
def format_player_key(player_name):
    return player_name.replace(" ", "")

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Invalid email or password', 'error')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return redirect(url_for('register'))
        new_user = User(name=name, email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    try:
        # Fetch upcoming matches
        response = requests.get(EVENTS_URL, headers=HEADERS)
        response.raise_for_status()
        events_data = response.json()

        # Extract top 10 upcoming matches
        upcoming_matches = events_data['events'][:10]

        # Fetch ATP rankings
        rankings_response = requests.get(RANKINGS_URL, headers=HEADERS)
        rankings_response.raise_for_status()
        rankings_data = rankings_response.json()

        # Extract top 10 players from rankings
        top_10_players = rankings_data['rankings'][:10]

        # Pass both upcoming matches and rankings to the template
        return render_template('index.html', upcoming_matches=upcoming_matches, top_10_players=top_10_players)
    except requests.exceptions.RequestException as e:
        # Log the error and show an appropriate message
        print(f"Error fetching data: {e}")
        return render_template('error.html', message="Error fetching upcoming matches or player rankings.")


@app.route('/upload', methods=['POST'])
@login_required
def upload_video():
    # Get Player 1 and Player 2 names
    player1_name = request.form.get('player1')
    player2_name = request.form.get('player2')
    def to_camel_case(input_string):
        words = input_string.split()
        return words[0].lower() + ''.join(word.capitalize() for word in words[1:])

    player1_camel_case = to_camel_case(player1_name)
    player2_camel_case = to_camel_case(player2_name)

    # Check if both players are provided
    if not player1_name or not player2_name:
        return render_template('error.html', message="Both Player 1 and Player 2 names are required.")
    try:
        response = fetch_gpt_player_data(player1_name,player2_name)
        # Read the JSON data from the file
        with open("player_data.json", "r") as file:
            player_data = json.load(file)  # Load the JSON content into a Python dictionary
        
        players = player_data.get("players", {})
        # Check if players is a list or dictionary
        if isinstance(players, dict):
            # Dictionary-based structure
            player1_data = players.get(player1_camel_case) or players.get(player1_name)
            player2_data = players.get(player2_camel_case) or players.get(player2_name)
        elif isinstance(players, list):
            # List-based structure: Find players by matching their names
            player1_data = next((p for p in players if p["fullName"] == player1_name), None)
            player2_data = next((p for p in players if p["fullName"] == player2_name), None)
        else:
            raise ValueError("Unknown players structure in JSON.")

        if not player1_data or not player2_data:
            raise ValueError("Player data not found in the JSON file.")

        print("Player 1 Data:", player1_data)
        print("Player 2 Data:", player2_data)

    except KeyError as e:
        print(f"Error fetching GPT data: Missing key {e}")
        return render_template('error.html', message="Player data not found in GPT response.")
    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON. Error: {e}")
        return render_template('error.html', message="Failed to parse player stats.")
    except Exception as e:
        print(f"Error fetching GPT data: {e}")
        return render_template('error.html', message="An error occurred while fetching player stats.")

    # Generate player stats and graphs
    try:
        stats, graph_paths = get_player_stats_with_visuals(player1_name, player2_name)
    except Exception as e:
        print(f"Error generating player stats: {e}")
        return render_template('error.html', message="An error occurred while generating player stats.")
    
    # Check if the form is a YouTube link submission
    if 'video_url' in request.form and request.form['video_url']:
        url = request.form['video_url']
        unique_id = str(uuid.uuid4())
        ydl_opts = {
            'format': 'bestvideo+bestaudio/best',
            'outtmpl': os.path.join(YOUTUBE_FOLDER, f'{unique_id}.%(ext)s'),  # Use the correct YOUTUBE_FOLDER here
            'merge_output_format': 'mp4',
            'ffmpeg_location': r'C:\Program Files\ffmpeg-master-latest-win64-gpl-shared\bin'  # Provide the ffmpeg path if necessary
        }

        try:
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(url, download=True)
                file_name = f"{unique_id}.mp4"
                video_path = os.path.join(YOUTUBE_FOLDER, file_name)
                # Return the player names and video file
                # Return video and player stats to the play.html template
                return render_template(
                    'play.html', 
                    video_url=video_path, 
                    player1=player1_name, 
                    player2=player2_name, 
                    player1_data=player1_data,
                    player2_data=player2_data,
                    stats=stats, 
                    graph_paths=graph_paths
                )

        except Exception as e:
            return f"Error: {str(e)}. Please check the YouTube URL or try again later."

    # If a file is uploaded
    elif 'file' in request.files and request.files['file']:
        file = request.files['file']
        if file.filename == '':
            return 'No selected file'

        unique_id = str(uuid.uuid4())
        filename = f"{unique_id}.mp4"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        filename1 = f"input_video1.mp4"
        output_file_path = os.path.join(app.config['OUTPUT_FOLDER'], filename1)
        # Return the player names and uploaded video file
        return render_template(
            'play.html', 
            video_url=file_path, 
            output_video_url=output_file_path,
            player1=player1_name, 
            player2=player2_name, 
            player1_data=player1_data,
            player2_data=player2_data,
            stats=stats, 
            graph_paths=graph_paths
        )

    return render_template('error.html', message="No video uploaded or URL provided.")


@app.route('/play/<video_file>')
@login_required
def play_video(video_file):
    # Determine the folder the video is in (uploads or YouTube downloads)
    if os.path.exists(os.path.join(UPLOAD_FOLDER, video_file)):
        video_url = url_for('static', filename=f'uploads/{video_file}')
    else:
        video_url = url_for('static', filename=f'videos/{video_file}')

    return render_template('play.html', video_url=video_url)

# API keys and headers for Tennis API
# RAPIDAPI_KEY = 'd53a40c9bdmsh245afa9648bf057p1162f9jsn3339b9778f0a'
RAPIDAPI_KEY = 'a4194f971amsh34f35d4813b3dc0p18c3dfjsn85c4d9ddd8a0'
HEADERS = {
    'x-rapidapi-key': RAPIDAPI_KEY,
    'x-rapidapi-host': 'tennisapi1.p.rapidapi.com'
}

# Base URLs for the APIs
RANKINGS_URL = "https://tennisapi1.p.rapidapi.com/api/tennis/rankings/atp/live"
PLAYER_URL = "https://tennisapi1.p.rapidapi.com/api/tennis/search/{}"  # player_id will be inserted
EVENTS_URL = "https://tennisapi1.p.rapidapi.com/api/tennis/events/19/10/2024"  # Static date for now, consider dynamic

# Rankings Page - Rankings API
@app.route('/')
@app.route('/rankings')
@login_required
def rankings():
    try:
        # Requesting the ATP live rankings
        response = requests.get(RANKINGS_URL, headers=HEADERS)
        response.raise_for_status()  # Raise an exception for bad status codes
        rankings_data = response.json()

        # Pass the rankings data to the template
        return render_template('rankings.html', rankings=rankings_data['rankings'])
    except requests.exceptions.RequestException as e:
        # Log the error and show an appropriate message
        print(f"Error fetching rankings: {e}")
        return render_template('error.html', message="Error fetching rankings data.")

# Tennis Events Page - Tennis Events API
@app.route('/schedule')
@login_required
def tennis_events():
    try:
        # Requesting tennis events for a fixed date (can make this dynamic later)
        response = requests.get(EVENTS_URL, headers=HEADERS)
        response.raise_for_status()  # Raise an exception for bad status codes
        events_data = response.json()

        # Pass the events data to the template
        return render_template('schedule.html', events=events_data['events'])
    except requests.exceptions.RequestException as e:
        # Log the error and show an appropriate message
        print(f"Error fetching events: {e}")
        return render_template('error.html', message="Error fetching events data.")


@app.route('/player_search', methods=['GET'])
@login_required
def player_search():
    query = request.args.get('query')
    if not query:
        return render_template('error.html', message="Player query not provided.")

    try:
        # Perform API request to search for the player
        url = PLAYER_URL.format(query)
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()  # Raise error if the request fails

        # Parse response JSON
        player_data = response.json()

        # Check if results are found
        results = player_data.get('results', [])
        if not results:
            return render_template('error.html', message="No player found for the query.")

        # Extract player details from the first result
        player_info = results[0]['entity']

        # Render the player template with the player data
        return render_template('player.html', player=player_info, full_data=player_info)

    except requests.exceptions.RequestException as e:
        print(f"Error fetching player info: {e}")
        return render_template('error.html', message="Error fetching player data.")
    except KeyError as e:
        print(f"Key error: {e}")
        return render_template('error.html', message="Invalid player data format.")

@app.route('/about')
def about():
    return render_template('about.html')
    
if __name__ == '__main__':
    app.run(debug=True)
