import socket
import pygame
import io
import threading

def handle_server_messages(client):
    """
    Listens for messages from the server and handles them.
    This includes control commands and music data.
    """
    music_data = io.BytesIO()
    
    buffer = b''
    try:
        while True:
            chunk = client.recv(4096)
            if not chunk:
                print("Server closed the connection.")
                break
            
            buffer += chunk
            
            # Process commands and data from the buffer
            while True:
                # Find the first newline, which separates commands or marks the end of a data chunk
                try:
                    line_end = buffer.index(b'\n')
                    line = buffer[:line_end].decode('utf-8').strip()
                    buffer = buffer[line_end+1:]

                    # --- Handle Commands ---
                    if line.startswith("SONG:"):
                        print("New song command received. Preparing to receive data.")
                        pygame.mixer.music.stop()
                        music_data = io.BytesIO() # Reset the stream for the new song
                    elif line == "PAUSE":
                        print("Pause command received.")
                        pygame.mixer.music.pause()
                    elif line == "RESUME":
                        print("Resume command received.")
                        pygame.mixer.music.unpause()
                    elif line == "STOP":
                        print("Stop command received.")
                        pygame.mixer.music.stop()
                    elif line == "END_STREAM":
                        print("End of stream received. Playing music.")
                        # The entire song is now in music_data.
                        # We can now safely load and play it.
                        music_data.seek(0)
                        pygame.mixer.music.load(music_data)
                        pygame.mixer.music.play()
                    
                    # Continue processing the buffer for more commands
                    continue

                except ValueError:
                    # No newline found, so the buffer contains partial music data.
                    # Write the current buffer to our in-memory file.
                    music_data.write(buffer)
                    buffer = b''
                    # Break from the inner loop to wait for more data
                    break

    except (socket.error, ConnectionResetError) as e:
        print(f"Connection error: {e}")
    finally:
        client.close()
        print("Connection closed")


def main():
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client.connect(('127.0.0.1', 12345))
        print("Connected to server")
    except ConnectionRefusedError:
        print("Connection refused. Is the server running?")
        return

    pygame.init()
    pygame.mixer.init()

    # Start a thread to handle all communication from the server
    thread = threading.Thread(target=handle_server_messages, args=(client,))
    thread.daemon = True
    thread.start()

    # Keep the main thread alive to allow pygame to run
    while thread.is_alive():
        pygame.time.wait(100)

    pygame.quit()
    print("Client shut down.")


if __name__ == '__main__':
    main()
