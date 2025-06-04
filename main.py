import kivy
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.checkbox import CheckBox
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
from kivy.logger import Logger
from datetime import datetime, timedelta
import threading
import json
import os

# Import your existing classes (these would need to be in the same APK)
try:
    from mixcd_scrobbler import LastFMScrobbler, MixCDDatabase
except ImportError:
    # Fallback for development
    Logger.warning("Could not import scrobbler classes - using mock for development")
    
    class LastFMScrobbler:
        def ensure_authenticated(self):
            return True
        def scrobble_mix_cd(self, tracks, start_time, track_range=None):
            Logger.info(f"Mock scrobble: {len(tracks)} tracks at {start_time}")
    
    class MixCDDatabase:
        def __init__(self):
            self.cds = {
                "test_cd": {
                    "title": "Test Mix CD",
                    "tracks": [
                        {"artist": "Test Artist", "track": "Test Track 1", "album": "Test Album"},
                        {"artist": "Test Artist", "track": "Test Track 2", "album": "Test Album"}
                    ]
                }
            }
        def save_database(self):
            pass
        def parse_track_line(self, line):
            if ' - ' in line:
                parts = line.split(' - ', 1)
                return {"artist": parts[0], "track": parts[1], "album": ""}
            return None

class StatusConsole(ScrollView):
    """Scrollable console for status messages"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.console_text = Label(
            text="🎵 Mix CD Scrobbler Ready\n",
            text_size=(None, None),
            valign='top',
            markup=True
        )
        self.add_widget(self.console_text)
    
    def add_message(self, message):
        """Add a message to the console"""
        current_text = self.console_text.text
        self.console_text.text = current_text + message + "\n"
        # Auto-scroll to bottom
        Clock.schedule_once(lambda dt: setattr(self, 'scroll_y', 0), 0.1)

class AddCDPopup(Popup):
    """Popup for adding new CDs"""
    def __init__(self, cd_db, refresh_callback, **kwargs):
        super().__init__(**kwargs)
        self.cd_db = cd_db
        self.refresh_callback = refresh_callback
        self.title = "Add New Mix CD"
        self.size_hint = (0.9, 0.8)
        
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # Title input
        layout.add_widget(Label(text="CD Title:", size_hint_y=None, height=30))
        self.title_input = TextInput(multiline=False, size_hint_y=None, height=40)
        layout.add_widget(self.title_input)
        
        # Instructions
        layout.add_widget(Label(
            text="Paste tracks here (Artist - Track [Album]):",
            size_hint_y=None,
            height=30
        ))
        
        # Tracks input
        self.tracks_input = TextInput(multiline=True, hint_text="Artist - Track [Album]\nArtist - Track [Album]")
        layout.add_widget(self.tracks_input)
        
        # Buttons
        button_layout = BoxLayout(size_hint_y=None, height=50, spacing=10)
        
        cancel_btn = Button(text="Cancel")
        cancel_btn.bind(on_press=self.dismiss)
        button_layout.add_widget(cancel_btn)
        
        add_btn = Button(text="Add CD")
        add_btn.bind(on_press=self.add_cd)
        button_layout.add_widget(add_btn)
        
        layout.add_widget(button_layout)
        self.content = layout
    
    def add_cd(self, instance):
        """Add the CD to database"""
        title = self.title_input.text.strip()
        tracks_text = self.tracks_input.text.strip()
        
        if not title or not tracks_text:
            return
        
        # Parse tracks
        tracks = []
        for line in tracks_text.split('\n'):
            line = line.strip()
            if line:
                parsed = self.cd_db.parse_track_line(line)
                if parsed:
                    tracks.append(parsed)
        
        if tracks:
            # Generate CD ID
            cd_id = title.lower().replace(" ", "_").replace(":", "").replace("-", "_")
            cd_id = ''.join(c for c in cd_id if c.isalnum() or c == '_')
            
            # Add to database
            self.cd_db.cds[cd_id] = {
                "title": title,
                "tracks": tracks
            }
            self.cd_db.save_database()
            
            # Refresh main app
            self.refresh_callback()
            self.dismiss()

class TrackSelectionLayout(GridLayout):
    """Widget for track selection options"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cols = 1
        self.size_hint_y = None
        self.height = 150
        self.spacing = 5
        
        # Selection type
        self.selection_type = "all"
        
        # All tracks option
        self.all_checkbox = CheckBox(active=True, size_hint_x=None, width=30)
        all_layout = BoxLayout(size_hint_y=None, height=30)
        all_layout.add_widget(self.all_checkbox)
        all_layout.add_widget(Label(text="All tracks"))
        self.add_widget(all_layout)
        
        # Range option
        range_layout = BoxLayout(size_hint_y=None, height=30)
        self.range_checkbox = CheckBox(size_hint_x=None, width=30)
        range_layout.add_widget(self.range_checkbox)
        range_layout.add_widget(Label(text="Range:"))
        self.range_start = TextInput(text="1", multiline=False, size_hint_x=None, width=50)
        self.range_end = TextInput(text="5", multiline=False, size_hint_x=None, width=50)
        range_layout.add_widget(self.range_start)
        range_layout.add_widget(Label(text="to", size_hint_x=None, width=30))
        range_layout.add_widget(self.range_end)
        self.add_widget(range_layout)
        
        # Individual tracks option
        individual_layout = BoxLayout(size_hint_y=None, height=30)
        self.individual_checkbox = CheckBox(size_hint_x=None, width=30)
        individual_layout.add_widget(self.individual_checkbox)
        individual_layout.add_widget(Label(text="Individual:"))
        self.individual_input = TextInput(hint_text="1,3,5", multiline=False)
        individual_layout.add_widget(self.individual_input)
        self.add_widget(individual_layout)
        
        # Bind checkbox events
        self.all_checkbox.bind(active=self.on_all_selected)
        self.range_checkbox.bind(active=self.on_range_selected)
        self.individual_checkbox.bind(active=self.on_individual_selected)
    
    def on_all_selected(self, checkbox, value):
        if value:
            self.selection_type = "all"
            self.range_checkbox.active = False
            self.individual_checkbox.active = False
    
    def on_range_selected(self, checkbox, value):
        if value:
            self.selection_type = "range"
            self.all_checkbox.active = False
            self.individual_checkbox.active = False
    
    def on_individual_selected(self, checkbox, value):
        if value:
            self.selection_type = "individual"
            self.all_checkbox.active = False
            self.range_checkbox.active = False
    
    def get_track_selection(self, cd_info):
        """Get track selection based on current settings"""
        if self.selection_type == "all":
            return None
        elif self.selection_type == "range":
            try:
                start = int(self.range_start.text)
                end = int(self.range_end.text)
                if 1 <= start <= end <= len(cd_info['tracks']):
                    return (start, end)
            except ValueError:
                pass
            return False
        elif self.selection_type == "individual":
            try:
                track_nums = [int(x.strip()) for x in self.individual_input.text.split(',') if x.strip()]
                selected = []
                for num in track_nums:
                    if 1 <= num <= len(cd_info['tracks']):
                        selected.append(cd_info['tracks'][num-1])
                return selected if selected else False
            except ValueError:
                return False

class TimeSelectionLayout(GridLayout):
    """Widget for time selection options"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cols = 1
        self.size_hint_y = None
        self.height = 120
        self.spacing = 5
        
        self.time_option = "now"
        
        # Just finished option
        self.now_checkbox = CheckBox(active=True, size_hint_x=None, width=30)
        now_layout = BoxLayout(size_hint_y=None, height=30)
        now_layout.add_widget(self.now_checkbox)
        now_layout.add_widget(Label(text="Just finished listening"))
        self.add_widget(now_layout)
        
        # Earlier today option
        today_layout = BoxLayout(size_hint_y=None, height=30)
        self.today_checkbox = CheckBox(size_hint_x=None, width=30)
        today_layout.add_widget(self.today_checkbox)
        today_layout.add_widget(Label(text="Earlier today at:"))
        self.hour_input = TextInput(text="20", multiline=False, size_hint_x=None, width=50)
        today_layout.add_widget(self.hour_input)
        today_layout.add_widget(Label(text=":00", size_hint_x=None, width=30))
        self.add_widget(today_layout)
        
        # Custom option
        custom_layout = BoxLayout(size_hint_y=None, height=30)
        self.custom_checkbox = CheckBox(size_hint_x=None, width=30)
        custom_layout.add_widget(self.custom_checkbox)
        custom_layout.add_widget(Label(text="Custom:"))
        self.date_input = TextInput(text=datetime.now().strftime("%Y-%m-%d"), multiline=False, size_hint_x=0.4)
        self.time_input = TextInput(text="20:00", multiline=False, size_hint_x=0.3)
        custom_layout.add_widget(self.date_input)
        custom_layout.add_widget(self.time_input)
        self.add_widget(custom_layout)
        
        # Bind events
        self.now_checkbox.bind(active=self.on_now_selected)
        self.today_checkbox.bind(active=self.on_today_selected)
        self.custom_checkbox.bind(active=self.on_custom_selected)
    
    def on_now_selected(self, checkbox, value):
        if value:
            self.time_option = "now"
            self.today_checkbox.active = False
            self.custom_checkbox.active = False
    
    def on_today_selected(self, checkbox, value):
        if value:
            self.time_option = "today"
            self.now_checkbox.active = False
            self.custom_checkbox.active = False
    
    def on_custom_selected(self, checkbox, value):
        if value:
            self.time_option = "custom"
            self.now_checkbox.active = False
            self.today_checkbox.active = False
    
    def get_start_time(self, cd_info, track_selection):
        """Get start time based on selection"""
        if self.time_option == "now":
            # Calculate backwards
            if isinstance(track_selection, tuple):
                num_tracks = track_selection[1] - track_selection[0] + 1
            elif isinstance(track_selection, list):
                num_tracks = len(track_selection)
            else:
                num_tracks = len(cd_info['tracks'])
            return datetime.now() - timedelta(minutes=num_tracks * 4)
        
        elif self.time_option == "today":
            try:
                hour = int(self.hour_input.text)
                return datetime.now().replace(hour=hour, minute=0, second=0, microsecond=0)
            except ValueError:
                return None
        
        elif self.time_option == "custom":
            try:
                date_str = self.date_input.text
                time_str = self.time_input.text
                datetime_str = f"{date_str} {time_str}"
                return datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")
            except ValueError:
                return None

class MixCDScrobblerApp(App):
    def build(self):
        # Initialize core components
        self.scrobbler = LastFMScrobbler()
        self.cd_db = MixCDDatabase()
        
        # Main layout
        main_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # Title
        title_label = Label(
            text="🎵 Mix CD Scrobbler",
            size_hint_y=None,
            height=50,
            font_size=20
        )
        main_layout.add_widget(title_label)
        
        # CD Selection
        cd_layout = BoxLayout(size_hint_y=None, height=50)
        cd_layout.add_widget(Label(text="CD:", size_hint_x=None, width=50))
        
        self.cd_spinner = Spinner(
            text="Select CD...",
            values=self.get_cd_list()
        )
        cd_layout.add_widget(self.cd_spinner)
        
        refresh_btn = Button(text="↻", size_hint_x=None, width=50)
        refresh_btn.bind(on_press=self.refresh_cd_list)
        cd_layout.add_widget(refresh_btn)
        
        main_layout.add_widget(cd_layout)
        
        # Track Selection
        track_label = Label(text="Track Selection:", size_hint_y=None, height=30)
        main_layout.add_widget(track_label)
        
        self.track_selection = TrackSelectionLayout()
        main_layout.add_widget(self.track_selection)
        
        # Time Selection
        time_label = Label(text="When did you listen?", size_hint_y=None, height=30)
        main_layout.add_widget(time_label)
        
        self.time_selection = TimeSelectionLayout()
        main_layout.add_widget(self.time_selection)
        
        # Action Buttons
        button_layout = BoxLayout(size_hint_y=None, height=60, spacing=10)
        
        auth_btn = Button(text="Test Auth")
        auth_btn.bind(on_press=self.test_auth)
        button_layout.add_widget(auth_btn)
        
        add_cd_btn = Button(text="Add CD")
        add_cd_btn.bind(on_press=self.show_add_cd)
        button_layout.add_widget(add_cd_btn)
        
        scrobble_btn = Button(text="Scrobble!")
        scrobble_btn.bind(on_press=self.scrobble_cd)
        button_layout.add_widget(scrobble_btn)
        
        main_layout.add_widget(button_layout)
        
        # Status Console
        console_label = Label(text="Status:", size_hint_y=None, height=30)
        main_layout.add_widget(console_label)
        
        self.console = StatusConsole()
        main_layout.add_widget(self.console)
        
        return main_layout
    
    def get_cd_list(self):
        """Get list of CDs for spinner"""
        cd_list = []
        for cd_id, cd_info in self.cd_db.cds.items():
            cd_list.append(f"{cd_info['title']} ({len(cd_info['tracks'])} tracks)")
        return cd_list or ["No CDs available"]
    
    def refresh_cd_list(self, instance=None):
        """Refresh the CD spinner"""
        self.cd_spinner.values = self.get_cd_list()
        if self.cd_spinner.values and self.cd_spinner.values[0] != "No CDs available":
            self.cd_spinner.text = self.cd_spinner.values[0]
    
    def get_selected_cd_info(self):
        """Get currently selected CD info"""
        if not self.cd_spinner.text or self.cd_spinner.text == "Select CD..." or self.cd_spinner.text == "No CDs available":
            return None, None
        
        # Find CD by title
        for cd_id, cd_info in self.cd_db.cds.items():
            cd_display = f"{cd_info['title']} ({len(cd_info['tracks'])} tracks)"
            if cd_display == self.cd_spinner.text:
                return cd_id, cd_info
        return None, None
    
    def test_auth(self, instance):
        """Test authentication"""
        def run_test():
            self.console.add_message("Testing Last.fm authentication...")
            if self.scrobbler.ensure_authenticated():
                self.console.add_message("✓ Authentication successful!")
            else:
                self.console.add_message("✗ Authentication failed")
        
        threading.Thread(target=run_test, daemon=True).start()
    
    def show_add_cd(self, instance):
        """Show add CD popup"""
        popup = AddCDPopup(self.cd_db, self.refresh_cd_list)
        popup.open()
    
    def scrobble_cd(self, instance):
        """Scrobble the selected CD"""
        cd_id, cd_info = self.get_selected_cd_info()
        if not cd_info:
            self.console.add_message("✗ Please select a CD first")
            return
        
        track_selection = self.track_selection.get_track_selection(cd_info)
        if track_selection is False:
            self.console.add_message("✗ Invalid track selection")
            return
        
        start_time = self.time_selection.get_start_time(cd_info, track_selection)
        if start_time is None:
            self.console.add_message("✗ Invalid time selection")
            return
        
        def run_scrobble():
            self.console.add_message(f"Starting scrobble: {cd_info['title']}")
            
            try:
                if isinstance(track_selection, tuple):
                    self.scrobbler.scrobble_mix_cd(cd_info['tracks'], start_time, track_range=track_selection)
                elif isinstance(track_selection, list):
                    self.scrobbler.scrobble_mix_cd(track_selection, start_time)
                else:
                    self.scrobbler.scrobble_mix_cd(cd_info['tracks'], start_time)
                
                self.console.add_message("✓ Scrobbling completed!")
            except Exception as e:
                self.console.add_message(f"✗ Scrobbling failed: {str(e)}")
        
        threading.Thread(target=run_scrobble, daemon=True).start()

if __name__ == "__main__":
    MixCDScrobblerApp().run()