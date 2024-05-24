import moviepy.editor as mp
import tkinter as tk
import os
import sys
import threading
from datetime import datetime
from tkinter import filedialog, messagebox


'''

SBS-Flipper
Flips side-by-side video to R+L for cross-eyed stereoscopic viewing

Author: thirdtype
https://github.com/thethirdtype

'''


def sanitize_file_name(file_name: str) -> str:
    return file_name.replace("/", "\\") if os.name == "nt" else file_name


def swap_sides(input_path: str, output_path: str) -> None:
    # Load the video
    video = mp.VideoFileClip(input_path)

    # Get video dimensions
    width, height = video.size

    # Ensure the video width is even
    if width % 2 != 0:
        raise ValueError("Video width must be even.")

    # Split the video into left and right parts
    left_clip = video.crop(x1=0, y1=0, x2=width // 2, y2=height)
    right_clip = video.crop(x1=width // 2, y1=0, x2=width, y2=height)

    # Concatenate the clips in swapped order
    final_clip = mp.clips_array([[right_clip, left_clip]])

    # Write the output video file
    final_clip.write_videofile(output_path, codec="libx264")


class TextRedirector:
    def __init__(self, text_widget, terminal):
        self.text_widget = text_widget
        self.terminal = terminal

    def write(self, string):
        self.text_widget.insert(tk.END, string)
        self.text_widget.see(tk.END)  # Scroll to the end
        self.terminal.write(string)  # Write to the normal console

    def flush(self):
        pass  # No action needed for flush


class SBSFlipperApp:
    def __init__(self, window: tk.Tk):
        self.root = window
        self.root.title("SBS-Flipper")

        self.width = 450
        self.height = 450
        self.root.geometry(f"{self.width}x{self.height}")

        screenwidth = self.root.winfo_screenwidth()
        screenheight = self.root.winfo_screenheight()
        alignment = "%dx%d+%d+%d" % \
                    (self.width, self.height, (screenwidth - self.width) / 2, (screenheight - self.height) / 2)
        self.root.geometry(alignment)

        self.input_file_path = tk.StringVar()
        self.output_file_path = tk.StringVar()
        self.time_date_format = "%Y-%m-%d %H:%M:%S"
        self.process = None

        tk.Label(self.root, text="Input Video File:", font=("Arial", 10, "bold")).pack(padx=20, pady=(10, 2))

        input_frame = tk.Frame(self.root)
        input_frame.pack(fill=tk.X, padx=20, pady=4)

        tk.Entry(input_frame, textvariable=self.input_file_path, width=1, font=("Arial", 10)) \
            .pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Button(input_frame, text="Browse", font=("Arial", 10), command=self.select_input_file) \
            .pack(side=tk.LEFT, padx=(10, 0))

        tk.Label(self.root, text="Output Video File:", font=("Arial", 10, "bold")).pack(padx=20, pady=(4, 2))

        output_frame = tk.Frame(self.root)
        output_frame.pack(fill=tk.X, padx=20, pady=4)

        tk.Entry(output_frame, textvariable=self.output_file_path, width=1, font=("Arial", 10)) \
            .pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Button(output_frame, text="Browse", font=("Arial", 10), command=self.select_output_file) \
            .pack(side=tk.LEFT, padx=(10, 0))

        self.start_stop_button = tk.Button(self.root, text="Start", font=("Arial", 14), command=self.start_stop_process)
        self.start_stop_button.pack(padx=20, pady=(10, 20))

        console_frame = tk.Frame(self.root)
        console_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))

        self.console_text = tk.Text(console_frame, width=1, height=12, wrap=tk.WORD, font=("Arial", 10))
        self.console_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(console_frame, command=self.console_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.console_text.config(yscrollcommand=scrollbar.set)

        # Redirect stdout and stderr
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        sys.stdout = TextRedirector(self.console_text, self.original_stdout)
        sys.stderr = TextRedirector(self.console_text, self.original_stderr)

    def console_log(self, output: str) -> None:
        print(f"[{datetime.now().strftime(self.time_date_format)}]: {output}")

    def select_input_file(self) -> None:
        file_name = filedialog.askopenfilename(filetypes=[("Video files", "*.mp4 *.avi *.mov *.mkv")])
        corrected_file_name = sanitize_file_name(file_name)

        file_root, file_ext = os.path.splitext(corrected_file_name)
        assumed_output_file_name = f"{file_root}_SBS-Flipper.mp4"

        self.input_file_path.set(corrected_file_name)
        self.output_file_path.set(assumed_output_file_name)

    def select_output_file(self) -> None:
        file_name = filedialog.asksaveasfilename(defaultextension=".mp4", filetypes=[("MP4 files", "*.mp4")])
        self.output_file_path.set(sanitize_file_name(file_name))

    def start_stop_process(self) -> None:
        if self.start_stop_button["text"] == "Start":
            self.start_process()
        else:
            self.stop_process()

    def start_process(self) -> None:
        input_path = self.input_file_path.get()
        output_path = self.output_file_path.get()

        if not input_path or not output_path:
            messagebox.showerror("Error", "Please select both input and output files.")
            return

        self.console_log(f"PROCESS STARTED, Input file: {input_path}, Output file: {output_path}")

        self.start_stop_button.config(text="Stop")
        self.process = threading.Thread(target=self.run_process, args=(input_path, output_path))
        self.process.start()

    def stop_process(self):
        if self.process and self.process.is_alive():
            self.process.join()
            self.console_log("PROCESS TERMINATED BY USER")
        self.start_stop_button.config(text="Start")

    def run_process(self, input_path: str, output_path: str) -> None:
        try:
            swap_sides(input_path, output_path)
            self.console_log("PROCESS ENDED, Video processing completed successfully!")
            messagebox.showinfo("Success", "Video processing completed successfully!")
        except Exception as e:
            self.console_log(f"PROCESS ENDED, Error: {e}")
            messagebox.showerror("Error", str(e))


if __name__ == "__main__":
    root = tk.Tk()
    app = SBSFlipperApp(root)
    root.mainloop()
