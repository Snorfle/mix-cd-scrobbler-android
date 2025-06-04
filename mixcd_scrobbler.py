import hashlib
import requests
import webbrowser
import time
import json
import os
from datetime import datetime, timedelta
from urllib.parse import urlencode
import random

class LastFMScrobbler:
    def __init__(self):
        self.api_key = None
        self.api_secret = None
        self.session_key = None
        self.credentials_file = "lastfm_credentials.json"
        
        # Load existing credentials if they exist
        self.load_credentials()
    
    def load_credentials(self):
        """Load saved credentials from file"""
        try:
            if os.path.exists(self.credentials_file):
                with open(self.credentials_file, 'r') as f:
                    creds = json.load(f)
                    self.api_key = creds.get('api_key')
                    self.api_secret = creds.get('api_secret')
                    self.session_key = creds.get('session_key')
                    print("✓ Loaded saved credentials")
                    return True
        except Exception as e:
            print(f"Could not load credentials: {e}")
        return False
    
    def save_credentials(self):
        """Save credentials to file"""
        try:
            creds = {
                'api_key': self.api_key,
                'api_secret': self.api_secret,
                'session_key': self.session_key
            }
            with open(self.credentials_file, 'w') as f:
                json.dump(creds, f, indent=2)
            print("✓ Credentials saved")
        except Exception as e:
            print(f"Could not save credentials: {e}")
    
    def setup_api_credentials(self):
        """Get API key and secret from user"""
        print("\n" + "="*50)
        print("LAST.FM API SETUP")
        print("="*50)
        print("1. Go to: https://www.last.fm/api/account/create")
        print("2. Sign in with your Last.fm account")
        print("3. Create an application with these details:")
        print("   - Name: Mix CD Scrobbler")
        print("   - Description: Personal script for scrobbling mix CDs")
        print("   - Callback URL: http://localhost")
        print("4. Copy your API Key and Shared Secret")
        print()
        
        self.api_key = input("Enter your API Key: ").strip()
        self.api_secret = input("Enter your Shared Secret: ").strip()
        
        if self.api_key and self.api_secret:
            print("✓ API credentials entered")
            return True
        else:
            print("✗ Invalid credentials")
            return False
    
    def generate_api_signature(self, params):
        """Generate the API signature required by Last.fm"""
        # Create a copy to avoid modifying the original
        sig_params = params.copy()
        
        # Remove format and api_sig if they exist (they shouldn't be in signature)
        sig_params.pop('format', None)
        sig_params.pop('api_sig', None)
        
        # Sort parameters and concatenate key+value pairs
        sorted_params = sorted(sig_params.items())
        param_string = ''.join([f"{k}{v}" for k, v in sorted_params])
        
        # Add secret and hash
        to_hash = param_string + self.api_secret
        return hashlib.md5(to_hash.encode('utf-8')).hexdigest()
    
    def get_session_key(self):
        """Walk through the authentication process"""
        print("\n" + "="*50)
        print("AUTHENTICATION")
        print("="*50)
        
        # Step 1: Get a request token
        print("\n1. Getting request token...")
        token_params = {
            'method': 'auth.getToken',
            'api_key': self.api_key,
            'format': 'json'
        }
        token_params['api_sig'] = self.generate_api_signature(token_params)
        
        try:
            response = requests.get('http://ws.audioscrobbler.com/2.0/', params=token_params)
            if response.status_code != 200:
                print(f"✗ Failed to get token: {response.text}")
                return False
            
            data = response.json()
            if 'token' not in data:
                print(f"✗ No token in response: {data}")
                return False
            
            token = data['token']
            print(f"✓ Got token: {token}")
            
        except Exception as e:
            print(f"✗ Token request failed: {e}")
            return False
        
        # Step 2: Get authorization URL with token
        auth_url = f"http://www.last.fm/api/auth/?api_key={self.api_key}&token={token}"
        print(f"\n2. Please visit this URL to authorize the application:")
        print(auth_url)
        print("\nOpening in your browser...")
        
        try:
            webbrowser.open(auth_url)
        except:
            print("Could not open browser. Please copy the URL above.")
        
        print("\n3. Click 'Yes, allow access' on the Last.fm page")
        print("4. After authorizing, press Enter to continue...")
        input()
        
        # Step 3: Get session key using the token
        print("\n5. Getting session key...")
        
        session_params = {
            'method': 'auth.getSession',
            'api_key': self.api_key,
            'token': token,
            'format': 'json'
        }
        
        session_params['api_sig'] = self.generate_api_signature(session_params)
        
        try:
            response = requests.get('http://ws.audioscrobbler.com/2.0/', params=session_params)
            
            if response.status_code == 200:
                data = response.json()
                if 'session' in data:
                    self.session_key = data['session']['key']
                    username = data['session']['name']
                    print(f"✓ Success! Authenticated as: {username}")
                    return True
                else:
                    print(f"✗ Error in response: {data}")
            else:
                print(f"✗ HTTP Error: {response.status_code}")
                print(response.text)
        except Exception as e:
            print(f"✗ Authentication failed: {e}")
        
        return False
    
    def test_authentication(self):
        """Test if authentication is working"""
        print("\n5. Testing authentication...")
        
        params = {
            'method': 'user.getInfo',
            'api_key': self.api_key,
            'sk': self.session_key,
            'format': 'json'
        }
        
        params['api_sig'] = self.generate_api_signature(params)
        
        try:
            response = requests.get('http://ws.audioscrobbler.com/2.0/', params=params)
            
            if response.status_code == 200:
                data = response.json()
                if 'user' in data:
                    print(f"✓ Ready to scrobble as: {data['user']['name']}")
                    return True
            
            print(f"✗ Authentication test failed: {response.text}")
        except Exception as e:
            print(f"✗ Test failed: {e}")
        
        return False
    
    def ensure_authenticated(self):
        """Make sure we have valid authentication"""
        # Check if we have all credentials
        if not all([self.api_key, self.api_secret, self.session_key]):
            print("Missing credentials. Setting up authentication...")
            
            # Get API credentials if needed
            if not self.api_key or not self.api_secret:
                if not self.setup_api_credentials():
                    return False
            
            # Get session key
            if not self.get_session_key():
                return False
            
            # Save credentials
            self.save_credentials()
        
        # Test authentication
        return self.test_authentication()
    
    def scrobble_track(self, artist, track, album, timestamp):
        """Scrobble a single track to Last.fm"""
        params = {
            'method': 'track.scrobble',
            'api_key': self.api_key,
            'sk': self.session_key,
            'artist': artist,
            'track': track,
            'timestamp': int(timestamp.timestamp()),
            'format': 'json'
        }
        
        # Add album if provided
        if album:
            params['album'] = album
        
        # Generate signature
        params['api_sig'] = self.generate_api_signature(params)
        
        try:
            response = requests.post('http://ws.audioscrobbler.com/2.0/', data=params)
            
            if response.status_code == 200:
                data = response.json()
                if 'scrobbles' in data:
                    # Check if scrobble was accepted
                    attr = data['scrobbles'].get('@attr', {})
                    accepted = int(attr.get('accepted', 0))
                    ignored = int(attr.get('ignored', 0))
                    
                    if accepted > 0:
                        return True
                    elif ignored > 0:
                        print(f"  ⚠ Scrobble ignored (probably duplicate)")
                        return True  # Still count as success
                    else:
                        print(f"  ✗ Scrobble not accepted: {data}")
                        return False
                else:
                    print(f"  ✗ Unexpected response format: {data}")
                    return False
            else:
                print(f"  ✗ HTTP Error {response.status_code}: {response.text}")
        except Exception as e:
            print(f"  ✗ Error: {e}")
        
        return False
    
    def scrobble_mix_cd(self, tracklist, start_time=None, avg_track_length=4, track_range=None):
        """Scrobble an entire mix CD or selected tracks"""
        if not self.ensure_authenticated():
            print("✗ Authentication failed. Cannot scrobble.")
            return
        
        if start_time is None:
            start_time = datetime.now()
        
        # Handle track selection
        if track_range:
            start_track, end_track = track_range
            selected_tracks = tracklist[start_track-1:end_track]  # Convert to 0-based indexing
            track_offset = start_track - 1
        else:
            selected_tracks = tracklist
            track_offset = 0
        
        print(f"\n" + "="*50)
        print("SCROBBLING MIX CD")
        print("="*50)
        print(f"Start time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        if track_range:
            print(f"Tracks: {track_range[0]}-{track_range[1]} of {len(tracklist)} (scrobbling {len(selected_tracks)} tracks)")
        else:
            print(f"Tracks: {len(selected_tracks)} (all tracks)")
        print(f"Estimated duration: {len(selected_tracks) * avg_track_length} minutes")
        print()
        
        current_time = start_time
        successful_scrobbles = 0
        
        for i, track_info in enumerate(selected_tracks, 1):
            actual_track_num = i + track_offset
            artist = track_info['artist']
            track = track_info['track']
            album = track_info.get('album', '')
            
            if track_range:
                print(f"Track {actual_track_num:2d}: {artist} - {track}")
            else:
                print(f"Track {i:2d}/{len(selected_tracks)}: {artist} - {track}")
            
            # Scrobble the track
            success = self.scrobble_track(artist, track, album, current_time)
            
            if success:
                print(f"  ✓ Scrobbled at {current_time.strftime('%H:%M:%S')}")
                successful_scrobbles += 1
            else:
                print(f"  ✗ Failed to scrobble")
            
            # Add realistic track duration with some variation
            track_duration = random.uniform(avg_track_length * 0.75, avg_track_length * 1.25)
            current_time += timedelta(minutes=track_duration)
            
            # Small delay to be nice to Last.fm's servers
            time.sleep(0.5)
        
        print(f"\n" + "="*50)
        print(f"SCROBBLING COMPLETE")
        print("="*50)
        print(f"Successfully scrobbled: {successful_scrobbles}/{len(selected_tracks)} tracks")
        print(f"Finished at: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    def select_tracks(self, tracklist):
        """Interactive track selection"""
        print(f"\nAvailable tracks:")
        for i, track in enumerate(tracklist, 1):
            print(f"{i:2d}. {track['artist']} - {track['track']}")
        
        print(f"\nTrack selection options:")
        print("1. All tracks")
        print("2. Single track")
        print("3. Range of tracks")
        print("4. Multiple individual tracks")
        
        choice = input("Select option (1-4): ").strip()
        
        if choice == "1":
            return None  # All tracks
        
        elif choice == "2":
            track_num = int(input(f"Enter track number (1-{len(tracklist)}): "))
            if 1 <= track_num <= len(tracklist):
                return (track_num, track_num)
            else:
                print("Invalid track number")
                return None
        
        elif choice == "3":
            start = int(input(f"Start track (1-{len(tracklist)}): "))
            end = int(input(f"End track (1-{len(tracklist)}): "))
            if 1 <= start <= end <= len(tracklist):
                return (start, end)
            else:
                print("Invalid range")
                return None
        
        elif choice == "4":
            tracks_input = input("Enter track numbers separated by commas (e.g., 1,3,5,7): ")
            try:
                track_nums = [int(x.strip()) for x in tracks_input.split(',')]
                # Create a new tracklist with only selected tracks
                selected = []
                for num in track_nums:
                    if 1 <= num <= len(tracklist):
                        selected.append(tracklist[num-1])
                    else:
                        print(f"Warning: Track {num} is out of range, skipping")
                return selected if selected else None
            except ValueError:
                print("Invalid format")
                return None
        
        else:
            print("Invalid choice")
            return None

class MixCDDatabase:
    def __init__(self):
        self.db_file = "mix_cds.json"
        self.load_database()
    
    def load_database(self):
        """Load mix CD database from file"""
        try:
            if os.path.exists(self.db_file):
                with open(self.db_file, 'r', encoding='utf-8') as f:
                    self.cds = json.load(f)
                print(f"✓ Loaded {len(self.cds)} mix CDs from database")
            else:
                # Initialize with the Replacements CD
                self.cds = {
                    "replacements_best": {
                        "title": "Left of the Dial: Best of the Replacements 1981-1990",
                        "tracks": [
                            {"artist": "The Replacements", "track": "If Only You Were Lonely", "album": "I'm in Trouble"},
                            {"artist": "The Replacements", "track": "Shiftless When Idle", "album": "Sorry Ma, I Forgot to Take Out The Trash"},
                            {"artist": "The Replacements", "track": "Kids Don't Follow", "album": "The Replacements Stink EP"},
                            {"artist": "The Replacements", "track": "Color Me Impressed", "album": "Hootenanny"},
                            {"artist": "The Replacements", "track": "I Will Dare", "album": "Let it Be"},
                            {"artist": "The Replacements", "track": "Kiss Me on the Bus", "album": "Tim"},
                            {"artist": "The Replacements", "track": "Alex Chilton", "album": "Pleased to Meet Me"},
                            {"artist": "The Replacements", "track": "Androgynous", "album": "Let it Be"},
                            {"artist": "The Replacements", "track": "Swingin' Party", "album": "Tim"},
                            {"artist": "The Replacements", "track": "Waitress in the Sky", "album": "Tim"},
                            {"artist": "The Replacements", "track": "Favorite Thing", "album": "Let it Be"},
                            {"artist": "The Replacements", "track": "Bastards of Young", "album": "Tim"},
                            {"artist": "The Replacements", "track": "Skyway", "album": "Pleased to Meet Me"},
                            {"artist": "The Replacements", "track": "Nobody", "album": "All Shook Down"},
                            {"artist": "The Replacements", "track": "Unsatisfied", "album": "Let it Be"},
                            {"artist": "The Replacements", "track": "Sadly Beautiful", "album": "All Shook Down"},
                            {"artist": "The Replacements", "track": "I'll Be You", "album": "Don't Tell A Soul"},
                            {"artist": "The Replacements", "track": "Within Your Reach", "album": "Hootenanny"},
                            {"artist": "The Replacements", "track": "Sixteen Blue", "album": "Let it Be"},
                            {"artist": "The Replacements", "track": "Can't Hardly Wait", "album": "Pleased to Meet Me"},
                            {"artist": "The Replacements", "track": "All Shook Down", "album": "All Shook Down"},
                            {"artist": "The Replacements", "track": "Treatment Bound", "album": "Hootenanny"},
                            {"artist": "The Replacements", "track": "Here Comes the Regular", "album": "Tim"},
                            {"artist": "The Replacements", "track": "Answering Machine", "album": "Let It Be"},
                            {"artist": "The Replacements", "track": "Left of the Dial", "album": "Tim"}
                        ]
                    }
                }
                self.save_database()
                print("✓ Created new mix CD database")
        except Exception as e:
            print(f"Error loading database: {e}")
            self.cds = {}
    
    def save_database(self):
        """Save mix CD database to file"""
        try:
            with open(self.db_file, 'w', encoding='utf-8') as f:
                json.dump(self.cds, f, indent=2, ensure_ascii=False)
            print("✓ Database saved")
        except Exception as e:
            print(f"Error saving database: {e}")
    
    def list_cds(self):
        """List all mix CDs in database"""
        if not self.cds:
            print("No mix CDs in database")
            return
        
        print("\nAvailable Mix CDs:")
        print("=" * 40)
        for i, (cd_id, cd_info) in enumerate(self.cds.items(), 1):
            print(f"{i}. {cd_info['title']} ({len(cd_info['tracks'])} tracks)")
    
    def get_cd(self, cd_id):
        """Get a specific mix CD"""
        return self.cds.get(cd_id)
    
    def add_cd_interactive(self):
        """Interactive CD addition"""
        print("\n" + "="*50)
        print("ADD NEW MIX CD")
        print("="*50)
        
        # Get CD info
        title = input("Enter CD title: ").strip()
        if not title:
            print("Title required")
            return
        
        # Generate ID from title
        cd_id = title.lower().replace(" ", "_").replace(":", "").replace("-", "_")
        cd_id = ''.join(c for c in cd_id if c.isalnum() or c == '_')
        
        print(f"\nAdding tracks for '{title}'")
        print("Choose input method:")
        print("1. Enter tracks one by one")
        print("2. Bulk paste (multiple lines at once)")
        
        method = input("Select method (1-2): ").strip()
        
        tracks = []
        
        if method == "1":
            # Original one-by-one method
            print("\nEnter tracks one by one. Press Enter on empty line when done.")
            print("Format: Artist - Track [Album] (album is optional)")
            print("Example: Bob Dylan - Like a Rolling Stone [Highway 61 Revisited]")
            
            track_num = 1
            while True:
                track_input = input(f"Track {track_num}: ").strip()
                
                if not track_input:
                    break
                
                parsed_track = self.parse_track_line(track_input)
                if parsed_track:
                    tracks.append(parsed_track)
                    artist, track, album = parsed_track['artist'], parsed_track['track'], parsed_track['album']
                    print(f"  ✓ Added: {artist} - {track}" + (f" [{album}]" if album else ""))
                    track_num += 1
                else:
                    print("Invalid format. Use: Artist - Track [Album]")
        
        elif method == "2":
            # Bulk paste method
            print("\nPaste all tracks at once (one per line). Press Enter twice when done.")
            print("Format: Artist - Track [Album] (album is optional)")
            print("Example:")
            print("Bob Dylan - Like a Rolling Stone [Highway 61 Revisited]")
            print("The Beatles - A Day in the Life [Sgt. Pepper's]")
            print()
            
            lines = []
            print("Paste tracks here:")
            while True:
                line = input().strip()
                if not line:
                    if lines:  # If we have lines and get empty input, we're done
                        break
                    else:  # If no lines yet, keep waiting
                        continue
                lines.append(line)
            
            # Parse all lines
            for i, line in enumerate(lines, 1):
                parsed_track = self.parse_track_line(line)
                if parsed_track:
                    tracks.append(parsed_track)
                    artist, track, album = parsed_track['artist'], parsed_track['track'], parsed_track['album']
                    print(f"  ✓ Track {i}: {artist} - {track}" + (f" [{album}]" if album else ""))
                else:
                    print(f"  ✗ Track {i}: Invalid format - {line}")
        
        else:
            print("Invalid choice")
            return
        
        if tracks:
            self.cds[cd_id] = {
                "title": title,
                "tracks": tracks
            }
            self.save_database()
            print(f"\n✓ Added '{title}' with {len(tracks)} tracks")
        else:
            print("No tracks added")
    
    def parse_track_line(self, track_input):
        """Parse a track line and clean up album names"""
        if ' - ' not in track_input:
            return None
        
        artist, rest = track_input.split(' - ', 1)
        artist = artist.strip()
        
        # Check for album in brackets
        if '[' in rest and ']' in rest:
            track = rest[:rest.find('[')].strip()
            album = rest[rest.find('[')+1:rest.find(']')].strip()
            
            # Clean up album names - remove "single", "EP", etc.
            album_cleanups = [
                ' single', ' EP', ' soundtrack', ' compilation',
                'single #1', 'single #2', 'single #3'
            ]
            
            # Remove these terms but keep the main album name
            for cleanup in album_cleanups:
                if cleanup in album:
                    album = album.replace(cleanup, '').strip()
            
            # Remove trailing commas and extra spaces
            album = album.rstrip(',').strip()
            
            # If album becomes empty or just punctuation, clear it
            if not album or album in [',', '.', '-', ':']:
                album = ""
        else:
            track = rest.strip()
            album = ""
        
        return {
            "artist": artist,
            "track": track,
            "album": album
        }
    
    def select_cd(self):
        """Interactive CD selection"""
        if not self.cds:
            print("No mix CDs available. Add one first!")
            return None, None
        
        self.list_cds()
        
        try:
            choice = int(input(f"\nSelect CD (1-{len(self.cds)}): ")) - 1
            cd_items = list(self.cds.items())
            if 0 <= choice < len(cd_items):
                cd_id, cd_info = cd_items[choice]
                return cd_id, cd_info
        except (ValueError, IndexError):
            print("Invalid selection")
        
        return None, None

def main():
    print("🎵 Mix CD Scrobbler 🎵")
    print("The perfect tool for xennial music lovers!")
    
    scrobbler = LastFMScrobbler()
    cd_db = MixCDDatabase()
    
    while True:
        print("\n" + "="*40)
        print("MAIN MENU")
        print("="*40)
        print("1. Scrobble a mix CD")
        print("2. Add new mix CD")
        print("3. List all mix CDs")
        print("4. Test authentication")
        print("5. Reset credentials")
        print("6. Exit")
        
        choice = input("\nSelect option (1-6): ").strip()
        
        if choice == "1":
            # Select CD
            cd_id, cd_info = cd_db.select_cd()
            if not cd_info:
                continue
            
            print(f"\nSelected: {cd_info['title']}")
            
            # Track selection
            print("\nTrack selection:")
            track_selection = scrobbler.select_tracks(cd_info['tracks'])
            
            print("\nWhen did you listen to this CD?")
            print("1. Just now")
            print("2. Earlier today")
            print("3. Custom date/time")
            
            time_choice = input("Select (1-3): ").strip()
            
            if time_choice == "1":
                # Calculate start time based on selected tracks
                if isinstance(track_selection, tuple):
                    # Range selection
                    num_tracks = track_selection[1] - track_selection[0] + 1
                elif isinstance(track_selection, list):
                    # Individual tracks
                    num_tracks = len(track_selection)
                else:
                    # All tracks
                    num_tracks = len(cd_info['tracks'])
                start_time = datetime.now() - timedelta(minutes=num_tracks * 4)
            elif time_choice == "2":
                hour = int(input("What hour (0-23)? "))
                start_time = datetime.now().replace(hour=hour, minute=0, second=0)
            elif time_choice == "3":
                date_str = input("Enter date (YYYY-MM-DD): ")
                time_str = input("Enter time (HH:MM): ")
                datetime_str = f"{date_str} {time_str}"
                start_time = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")
            else:
                continue
            
            # Handle different selection types
            if isinstance(track_selection, tuple):
                # Range selection (start, end)
                scrobbler.scrobble_mix_cd(cd_info['tracks'], start_time, track_range=track_selection)
            elif isinstance(track_selection, list):
                # Individual tracks - create a custom tracklist
                scrobbler.scrobble_mix_cd(track_selection, start_time)
            else:
                # All tracks
                scrobbler.scrobble_mix_cd(cd_info['tracks'], start_time)
        
        elif choice == "2":
            cd_db.add_cd_interactive()
        
        elif choice == "3":
            cd_db.list_cds()
        
        elif choice == "4":
            scrobbler.ensure_authenticated()
            
        elif choice == "5":
            if os.path.exists(scrobbler.credentials_file):
                os.remove(scrobbler.credentials_file)
                print("✓ Credentials reset")
            scrobbler.api_key = None
            scrobbler.api_secret = None
            scrobbler.session_key = None
            
        elif choice == "6":
            print("Happy scrobbling! 🎵")
            break
        
        else:
            print("Invalid choice")

if __name__ == "__main__":
    main()