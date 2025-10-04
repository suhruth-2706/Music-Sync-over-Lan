import os
import pygame
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

# --- Configuration ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MUSIC_FOLDER = os.path.join(BASE_DIR, 'music')

# --- Server State ---
connected_clients = 0

# --- Pygame Mixer for Local Playback ---
pygame.init()
pygame.mixer.init()

# --- Web Routes ---
@app.route('/')
def index():
    """Serves the main control page."""
    return render_template('index.html')

@app.route('/music', methods=['GET'])
def music_files():
    """Provides a list of available .mp3 files."""
    try:
        if not os.path.exists(MUSIC_FOLDER):
            os.makedirs(MUSIC_FOLDER)
        files = [f for f in os.listdir(MUSIC_FOLDER) if f.endswith('.mp3')]
        return jsonify({'files': files})
    except FileNotFoundError:
        return jsonify({'files': []})

# --- SocketIO Handlers ---
@socketio.on('connect')
def handle_connect():
    """A new browser has connected."""
    global connected_clients
    connected_clients += 1
    # Notify all clients of the new count
    emit('status', {'connected_clients': connected_clients}, broadcast=True)
    print(f"Browser connected. Total clients: {connected_clients}")

@socketio.on('disconnect')
def handle_disconnect():
    """A browser has disconnected."""
    global connected_clients
    connected_clients -= 1
    # Notify all clients of the new count
    emit('status', {'connected_clients': connected_clients}, broadcast=True)
    print(f"Browser disconnected. Total clients: {connected_clients}")

@socketio.on('get_status')
def handle_get_status(json):
    """Sends the current status to the client who asked."""
    emit('status', {'connected_clients': connected_clients})

@socketio.on('control_music')
def handle_control_music(json):
    """Handles commands from the web interface."""
    command = json.get('command')
    
    # --- Play Command ---
    if command == 'play':
        filename = json.get('filename')
        if not filename:
            return

        music_path = os.path.join(MUSIC_FOLDER, filename)
        if not os.path.exists(music_path):
            print(f"File not found: {music_path}")
            return

        print(f"Play command received for {filename}.")
        
        # 1. Play music locally on the server
        pygame.mixer.music.load(music_path)
        pygame.mixer.music.play()
        
        # 2. Notify all browsers to get ready for a new song
        emit('command', {'action': 'song', 'filename': filename}, broadcast=True)
        
        # 3. Stream the song data to all browsers
        with open(music_path, 'rb') as f:
            while True:
                chunk = f.read(4096)
                if not chunk:
                    break
                # Emit the raw binary chunk
                emit('audio_chunk', chunk, broadcast=True)
        
        # 4. Notify all browsers that the stream is finished
        emit('command', {'action': 'end_stream'}, broadcast=True)
        print(f"Finished streaming {filename}.")

    # --- Other Commands ---
    elif command == 'pause':
        pygame.mixer.music.pause()
        emit('command', {'action': 'pause'}, broadcast=True)
        print("Music paused.")
        
    elif command == 'resume':
        pygame.mixer.music.unpause()
        emit('command', {'action': 'resume'}, broadcast=True)
        print("Music resumed.")
        
    elif command == 'stop':
        pygame.mixer.music.stop()
        emit('command', {'action': 'stop'}, broadcast=True)
        print("Music stopped.")

if __name__ == '__main__':
    # Run the Flask-SocketIO server
    print("Starting server...")
    socketio.run(app, host='0.0.0.0', port=5000)
