#!/usr/bin/env python3
"""
record_mic_and_system_audio.py

This script automatically records audio simultaneously from:
  - The microphone (non-monitor device)
  - The system's output (monitor device)

The recordings are saved as:
  - "audio_input.wav"     (microphone only)
  - "audio_output.wav"    (system output only)
  - "audio_combined.wav"  (a stereo mix of both signals)

On Linux, the monitor source is set automatically via pactl.
"""

import sys
import os
import subprocess
from datetime import datetime
import soundcard as sc
import soundfile as sf
import numpy as np
import sounddevice as sd


# ---------------------------------------------------------------------------
# PulseAudio Helpers (Linux only)
# ---------------------------------------------------------------------------
def get_monitor_source():
    """Return the first source name containing 'monitor' using pactl, or None."""
    try:
        output = subprocess.check_output(
            ['pactl', 'list', 'sources', 'short'], universal_newlines=True
        )
    except subprocess.CalledProcessError as err:
        print(f"Error running pactl: {err}")
        return None

    for line in output.strip().splitlines():
        parts = line.split('\t')
        if len(parts) >= 2 and "monitor" in parts[1].lower():
            return parts[1]
    return None


def set_default_source(source_name):
    """Set the default audio input source using pactl."""
    try:
        subprocess.check_call(['pactl', 'set-default-source', source_name])
        print(f"Default source set to: {source_name}")
    except subprocess.CalledProcessError as err:
        print(f"Error setting default source: {err}")


# ---------------------------------------------------------------------------
# Device Selection Helpers
# ---------------------------------------------------------------------------
def select_devices():
    """
    Lists available microphones and lets the user select:
      - A microphone device
      - A system output monitor device (if available)
    Returns a tuple: (mic_device, sys_device)
    """
    # List all available microphones.
    mics = sc.all_microphones()
    if not mics:
        print("No microphone devices found!")
        sys.exit(1)

    print("All detected recording devices:")
    for idx, dev in enumerate(mics):
        print(f"  {idx}: {dev.name}")

    print("\nAvailable microphone devices:")
    for idx, mic in enumerate(mics):
        print(f"  {idx}: {mic.name}")
    mic_index = int(input("Select the microphone device index: "))
    mic_device = mics[mic_index]

    # --- System (monitor) device selection using sounddevice ---
    sd_devices = sd.query_devices()
    monitor_source = get_monitor_source()
    sys_device_index = None
    if monitor_source:
        for i, dev in enumerate(sd_devices):
            if monitor_source in dev['name']:
                sys_device_index = i
                print(f"\nAuto-selected system monitor device (sounddevice): {dev['name']}")
                break
    if sys_device_index is None:
        print("\nNo auto-detected sounddevice monitor found. Available sounddevice input devices:")
        # Filter for input devices:
        for i, dev in enumerate(sd_devices):
            if dev['max_input_channels'] > 0:
                print(f"  {i}: {dev['name']}")
        choice = input("Enter the device index for system audio (or press Enter for default): ")
        if choice.strip() == "":
            sys_device_index = sd.default.device['input']
        else:
            sys_device_index = int(choice)

    return mic_device, sys_device_index


# ---------------------------------------------------------------------------
# Audio Recording & Combining Helpers
# ---------------------------------------------------------------------------
def record_audio(samplerate, mic_device, sys_device_index):
    """
    Records audio concurrently:
      - The microphone from soundcard
      - The system output (monitor) from sounddevice
    Recording runs until the user presses Enter.
    Returns a tuple (mic_data, sys_data) as NumPy arrays.
    """
    import threading

    stop_event = threading.Event()
    recordings = {"mic": [], "sys": []}
    blocksize = 1024  # frames per block

    def record_mic():
        with mic_device.recorder(samplerate=samplerate, blocksize=blocksize) as rec:
            while not stop_event.is_set():
                block = rec.record(numframes=blocksize)
                recordings["mic"].append(block)

    def record_sys():
        # Record system audio using sounddevice.
        # Adjust channels if needed (here, we assume 2-channel system audio).
        with sd.InputStream(samplerate=samplerate, blocksize=blocksize, device=sys_device_index, channels=2) as stream:
            while not stop_event.is_set():
                block, _ = stream.read(blocksize)
                recordings["sys"].append(block)

    mic_thread = threading.Thread(target=record_mic)
    sys_thread = threading.Thread(target=record_sys)

    print("Recording... Press Enter to stop.")
    mic_thread.start()
    sys_thread.start()

    input()  # wait for Enter key press
    stop_event.set()

    mic_thread.join()
    sys_thread.join()

    # Concatenate recorded blocks into single NumPy arrays.
    mic_data = np.concatenate(recordings["mic"], axis=0)
    sys_data = np.concatenate(recordings["sys"], axis=0)
    return mic_data, sys_data


def combine_audio(mic_data, sys_data):
    """
    Combines the microphone and system audio into a single NumPy array.
    The shorter recording is trimmed to ensure equal length and,
    if needed, the mic signal (mono) is duplicated to stereo.
    """
    min_len = min(len(mic_data), len(sys_data))
    mic_data = mic_data[:min_len]
    sys_data = sys_data[:min_len]

    if sys_data.ndim == 2 and sys_data.shape[1] == 2 and mic_data.ndim == 2 and mic_data.shape[1] == 1:
        mic_data = np.tile(mic_data, (1, 2))

    combined = 0.5 * (sys_data + mic_data)
    return combined


# ---------------------------------------------------------------------------
# Main Function
# ---------------------------------------------------------------------------
def main():
    # On Linux, automatically set the default monitor source using PulseAudio.
    if not sys.platform.startswith("win"):
        monitor_source = get_monitor_source()
        if monitor_source:
            set_default_source(monitor_source)
        else:
            print("No monitor source found with pactl. Continuing with manual selection...")

    mic_device, sys_device_index = select_devices()

    # Set fixed sample rate
    samplerate = 44100

    print(f"\nUsing sample rate: {samplerate}Hz")
    print("Recording from:")
    print(f"  Microphone: {mic_device.name}")
    print(f"  System: {sd.query_devices()[sys_device_index]['name']}\n")

    # Record audio from both sources
    mic_data, sys_data = record_audio(samplerate, mic_device, sys_device_index)

    # Create an output folder for recordings and generate a timestamp.
    output_folder = "recordings"
    os.makedirs(output_folder, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Build full file paths with timestamp.
    audio_input_filename = os.path.join(output_folder, f"audio_input_{timestamp}.wav")
    audio_output_filename = os.path.join(output_folder, f"audio_output_{timestamp}.wav")
    audio_combined_filename = os.path.join(output_folder, f"audio_combined_{timestamp}.wav")

    # Save individual recordings (optional).
    sf.write(audio_input_filename, mic_data, samplerate, subtype="PCM_16")
    sf.write(audio_output_filename, sys_data, samplerate, subtype="PCM_16")

    # Combine and save the recordings.
    combined = combine_audio(mic_data, sys_data)
    sf.write(audio_combined_filename, combined, samplerate, subtype="PCM_16")

    print(f"Recordings saved as:\n  {audio_input_filename}\n  {audio_output_filename}\n  {audio_combined_filename}")


if __name__ == "__main__":
    main()
