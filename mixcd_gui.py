import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from tkinter import font
import threading
from datetime import datetime, timedelta
import sys
import io

# Import your existing classes
from mixcd_scrobbler import LastFMScrobbler, MixCDDatabase

class MixCDGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🎵 Mix CD Scrobbler")
        self.root.geometry("800x700")
        
        # Initialize your existing classes
        self.scrobbler = LastFMScrobbler()
        self.cd_db = MixCDDatabase()
        
        # Variables
        self.selected_cd = tk.StringVar()
        self.track_selection_var = tk.StringVar(value="all")
        self.time_option_var = tk.StringVar(value="now")
        
        self.setup_ui()
        self.refresh_cd_list()
    
    def setup_ui(self):
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Title
        title_font = font.Font(size=16, weight="bold")
        title_label = ttk.Label(main_frame, text="🎵 Mix CD Scrobbler", font=title_font)
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # CD Selection Section
        cd_frame = ttk.LabelFrame(main_frame, text="Select Mix CD", padding="10")
        cd_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        cd_frame.columnconfigure(1, weight=1)
        
        ttk.Label(cd_frame, text="CD:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.cd_combo = ttk.Combobox(cd_frame, textvariable=self.selected_cd, state="readonly", width=50)
        self.cd_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        
        ttk.Button(cd_frame, text="Refresh", command=self.refresh_cd_list).grid(row=0, column=2)
        
        # Track Selection Section
        track_frame = ttk.LabelFrame(main_frame, text="Track Selection", padding="10")
        track_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Radiobutton(track_frame, text="All tracks", variable=self.track_selection_var, value="all").grid(row=0, column=0, sticky=tk.W)
        
        ttk.Radiobutton(track_frame, text="Range:", variable=self.track_selection_var, value="range").grid(row=1, column=0, sticky=tk.W)
        ttk.Label(track_frame, text="From:").grid(row=1, column=1, sticky=tk.W, padx=(10, 5))
        self.range_start = ttk.Entry(track_frame, width=5)
        self.range_start.grid(row=1, column=2, padx=(0, 5))
        ttk.Label(track_frame, text="To:").grid(row=1, column=3, sticky=tk.W, padx=(5, 5))
        self.range_end = ttk.Entry(track_frame, width=5)
        self.range_end.grid(row=1, column=4, padx=(0, 5))
        
        ttk.Radiobutton(track_frame, text="Individual tracks (comma-separated):", variable=self.track_selection_var, value="individual").grid(row=2, column=0, sticky=tk.W, pady=(5, 0))
        self.individual_tracks = ttk.Entry(track_frame, width=30)
        self.individual_tracks.grid(row=2, column=1, columnspan=4, sticky=(tk.W, tk.E), padx=(10, 0), pady=(5, 0))
        
        # Timing Section
        time_frame = ttk.LabelFrame(main_frame, text="When did you listen?", padding="10")
        time_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Radiobutton(time_frame, text="Just finished listening", variable=self.time_option_var, value="now").grid(row=0, column=0, sticky=tk.W)
        
        ttk.Radiobutton(time_frame, text="Earlier today at:", variable=self.time_option_var, value="today").grid(row=1, column=0, sticky=tk.W)
        self.hour_spin = tk.Spinbox(time_frame, from_=0, to=23, width=5, format="%02.0f")
        self.hour_spin.grid(row=1, column=1, padx=(10, 5))
        ttk.Label(time_frame, text=":00").grid(row=1, column=2, sticky=tk.W)
        
        ttk.Radiobutton(time_frame, text="Custom date/time:", variable=self.time_option_var, value="custom").grid(row=2, column=0, sticky=tk.W, pady=(5, 0))
        self.custom_date = ttk.Entry(time_frame, width=12)
        self.custom_date.grid(row=2, column=1, padx=(10, 5), pady=(5, 0))
        self.custom_date.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.custom_time = ttk.Entry(time_frame, width=8)
        self.custom_time.grid(row=2, column=2, padx=(5, 0), pady=(5, 0))
        self.custom_time.insert(0, "20:00")
        
        # Action Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=3, pady=(0, 10))
        
        ttk.Button(button_frame, text="Test Authentication", command=self.test_auth).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Add New CD", command=self.show_add_cd_window).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Scrobble CD", command=self.scrobble_cd, style="Accent.TButton").pack(side=tk.LEFT)
        
        # Status/Output Section
        status_frame = ttk.LabelFrame(main_frame, text="Status", padding="10")
        status_frame.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        status_frame.columnconfigure(0, weight=1)
        status_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(5, weight=1)
        
        self.status_text = scrolledtext.ScrolledText(status_frame, height=15, width=80)
        self.status_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Redirect print statements to status text
        self.redirect_output()
    
    def redirect_output(self):
        """Redirect print statements to the status text widget"""
        class TextRedirector:
            def __init__(self, widget):
                self.widget = widget
            
            def write(self, string):
                self.widget.insert(tk.END, string)
                self.widget.see(tk.END)
                self.widget.update()
            
            def flush(self):
                pass
        
        sys.stdout = TextRedirector(self.status_text)
    
    def refresh_cd_list(self):
        """Refresh the CD dropdown list"""
        cd_items = []
        for cd_id, cd_info in self.cd_db.cds.items():
            cd_items.append(f"{cd_info['title']} ({len(cd_info['tracks'])} tracks)")
        
        self.cd_combo['values'] = cd_items
        if cd_items:
            self.cd_combo.set(cd_items[0])
    
    def get_selected_cd_info(self):
        """Get the currently selected CD info"""
        selection = self.selected_cd.get()
        if not selection:
            return None, None
        
        # Extract CD index from the dropdown selection
        cd_index = self.cd_combo.current()
        if cd_index >= 0:
            cd_items = list(self.cd_db.cds.items())
            cd_id, cd_info = cd_items[cd_index]
            return cd_id, cd_info
        return None, None
    
    def get_track_selection(self, cd_info):
        """Get the track selection based on user input"""
        selection_type = self.track_selection_var.get()
        
        if selection_type == "all":
            return None
        elif selection_type == "range":
            try:
                start = int(self.range_start.get())
                end = int(self.range_end.get())
                if 1 <= start <= end <= len(cd_info['tracks']):
                    return (start, end)
                else:
                    messagebox.showerror("Invalid Range", f"Range must be between 1 and {len(cd_info['tracks'])}")
                    return False
            except ValueError:
                messagebox.showerror("Invalid Input", "Please enter valid numbers for track range")
                return False
        elif selection_type == "individual":
            try:
                track_nums = [int(x.strip()) for x in self.individual_tracks.get().split(',') if x.strip()]
                selected = []
                for num in track_nums:
                    if 1 <= num <= len(cd_info['tracks']):
                        selected.append(cd_info['tracks'][num-1])
                    else:
                        messagebox.showwarning("Invalid Track", f"Track {num} is out of range, skipping")
                return selected if selected else False
            except ValueError:
                messagebox.showerror("Invalid Input", "Please enter comma-separated track numbers")
                return False
    
    def get_start_time(self, cd_info, track_selection):
        """Get the start time based on user selection"""
        time_option = self.time_option_var.get()
        
        if time_option == "now":
            # Calculate backwards from now
            if isinstance(track_selection, tuple):
                num_tracks = track_selection[1] - track_selection[0] + 1
            elif isinstance(track_selection, list):
                num_tracks = len(track_selection)
            else:
                num_tracks = len(cd_info['tracks'])
            return datetime.now() - timedelta(minutes=num_tracks * 4)
        
        elif time_option == "today":
            try:
                hour = int(self.hour_spin.get())
                return datetime.now().replace(hour=hour, minute=0, second=0, microsecond=0)
            except ValueError:
                messagebox.showerror("Invalid Time", "Please enter a valid hour")
                return None
        
        elif time_option == "custom":
            try:
                date_str = self.custom_date.get()
                time_str = self.custom_time.get()
                datetime_str = f"{date_str} {time_str}"
                return datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")
            except ValueError:
                messagebox.showerror("Invalid DateTime", "Please enter valid date (YYYY-MM-DD) and time (HH:MM)")
                return None
    
    def test_auth(self):
        """Test Last.fm authentication"""
        def run_test():
            print("Testing Last.fm authentication...")
            if self.scrobbler.ensure_authenticated():
                print("✓ Authentication successful!")
            else:
                print("✗ Authentication failed. Please check your credentials.")
        
        threading.Thread(target=run_test, daemon=True).start()
    
    def scrobble_cd(self):
        """Scrobble the selected CD"""
        cd_id, cd_info = self.get_selected_cd_info()
        if not cd_info:
            messagebox.showerror("No CD Selected", "Please select a CD to scrobble")
            return
        
        track_selection = self.get_track_selection(cd_info)
        if track_selection is False:
            return
        
        start_time = self.get_start_time(cd_info, track_selection)
        if start_time is None:
            return
        
        def run_scrobble():
            print(f"\nStarting scrobble for: {cd_info['title']}")
            
            if isinstance(track_selection, tuple):
                self.scrobbler.scrobble_mix_cd(cd_info['tracks'], start_time, track_range=track_selection)
            elif isinstance(track_selection, list):
                self.scrobbler.scrobble_mix_cd(track_selection, start_time)
            else:
                self.scrobbler.scrobble_mix_cd(cd_info['tracks'], start_time)
        
        # Run scrobbling in a separate thread to prevent GUI freezing
        threading.Thread(target=run_scrobble, daemon=True).start()
    
    def show_add_cd_window(self):
        """Show the Add CD window"""
        AddCDWindow(self.root, self.cd_db, self.refresh_cd_list)

class AddCDWindow:
    def __init__(self, parent, cd_db, refresh_callback):
        self.cd_db = cd_db
        self.refresh_callback = refresh_callback
        
        # Create new window
        self.window = tk.Toplevel(parent)
        self.window.title("Add New Mix CD")
        self.window.geometry("600x500")
        self.window.transient(parent)
        self.window.grab_set()
        
        self.setup_ui()
    
    def setup_ui(self):
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # CD Title
        ttk.Label(main_frame, text="CD Title:").pack(anchor=tk.W)
        self.title_entry = ttk.Entry(main_frame, width=60)
        self.title_entry.pack(fill=tk.X, pady=(5, 10))
        
        # Instructions
        instructions = """Paste track listings here (one per line):
Format: Artist - Track [Album]
Example: The Beatles - Hey Jude [The Beatles 1967-1970]
Album name in brackets is optional."""
        
        ttk.Label(main_frame, text=instructions, foreground="gray").pack(anchor=tk.W, pady=(0, 5))
        
        # Large text area for tracks
        self.tracks_text = scrolledtext.ScrolledText(main_frame, height=20, width=70)
        self.tracks_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(button_frame, text="Cancel", command=self.window.destroy).pack(side=tk.RIGHT, padx=(10, 0))
        ttk.Button(button_frame, text="Add CD", command=self.add_cd).pack(side=tk.RIGHT)
        ttk.Button(button_frame, text="Preview", command=self.preview_tracks).pack(side=tk.LEFT)
    
    def preview_tracks(self):
        """Preview parsed tracks"""
        title = self.title_entry.get().strip()
        tracks_text = self.tracks_text.get("1.0", tk.END).strip()
        
        if not title:
            messagebox.showerror("Missing Title", "Please enter a CD title")
            return
        
        if not tracks_text:
            messagebox.showerror("Missing Tracks", "Please enter track listings")
            return
        
        # Parse tracks
        tracks = []
        lines = tracks_text.split('\n')
        
        preview_text = f"CD: {title}\n\nParsed tracks:\n" + "="*40 + "\n"
        
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue
            
            parsed_track = self.cd_db.parse_track_line(line)
            if parsed_track:
                tracks.append(parsed_track)
                artist, track, album = parsed_track['artist'], parsed_track['track'], parsed_track['album']
                preview_text += f"{i:2d}. {artist} - {track}"
                if album:
                    preview_text += f" [{album}]"
                preview_text += "\n"
            else:
                preview_text += f"{i:2d}. ✗ INVALID: {line}\n"
        
        preview_text += f"\n{len(tracks)} valid tracks found"
        
        # Show preview window
        preview_window = tk.Toplevel(self.window)
        preview_window.title("Track Preview")
        preview_window.geometry("500x400")
        
        preview_frame = ttk.Frame(preview_window, padding="10")
        preview_frame.pack(fill=tk.BOTH, expand=True)
        
        preview_display = scrolledtext.ScrolledText(preview_frame, height=20, width=60)
        preview_display.pack(fill=tk.BOTH, expand=True)
        preview_display.insert("1.0", preview_text)
        preview_display.config(state=tk.DISABLED)
        
        ttk.Button(preview_frame, text="Close", command=preview_window.destroy).pack(pady=(10, 0))
    
    def add_cd(self):
        """Add the CD to the database"""
        title = self.title_entry.get().strip()
        tracks_text = self.tracks_text.get("1.0", tk.END).strip()
        
        if not title:
            messagebox.showerror("Missing Title", "Please enter a CD title")
            return
        
        if not tracks_text:
            messagebox.showerror("Missing Tracks", "Please enter track listings")
            return
        
        # Parse tracks
        tracks = []
        lines = tracks_text.split('\n')
        invalid_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            parsed_track = self.cd_db.parse_track_line(line)
            if parsed_track:
                tracks.append(parsed_track)
            else:
                invalid_lines.append(line)
        
        if invalid_lines:
            error_msg = f"Found {len(invalid_lines)} invalid lines:\n\n"
            error_msg += "\n".join(invalid_lines[:5])  # Show first 5
            if len(invalid_lines) > 5:
                error_msg += f"\n... and {len(invalid_lines) - 5} more"
            error_msg += "\n\nContinue anyway with valid tracks only?"
            
            if not messagebox.askyesno("Invalid Tracks Found", error_msg):
                return
        
        if not tracks:
            messagebox.showerror("No Valid Tracks", "No valid tracks found")
            return
        
        # Generate CD ID
        cd_id = title.lower().replace(" ", "_").replace(":", "").replace("-", "_")
        cd_id = ''.join(c for c in cd_id if c.isalnum() or c == '_')
        
        # Add to database
        self.cd_db.cds[cd_id] = {
            "title": title,
            "tracks": tracks
        }
        
        self.cd_db.save_database()
        
        messagebox.showinfo("Success", f"Added '{title}' with {len(tracks)} tracks")
        
        # Refresh main window CD list
        self.refresh_callback()
        
        # Close window
        self.window.destroy()

def main():
    root = tk.Tk()
    app = MixCDGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()