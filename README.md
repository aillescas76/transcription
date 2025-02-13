# Audio Recorder Project

This project provides a Python-based solution to record audio simultaneously from two sources:

- **Microphone (non-monitor device):** Captures live audio from your microphone.
- **System Output (monitor device):** Captures the sound output from your system (e.g., audio from YouTube, music players, etc.).

Additionally, the project combines both recordings into a single stereo file.

---

## Folder Structure

Below is a suggested folder structure for the project, which separates the backend processing (recording, transcription, analysis) from the frontend user interface and other configuration files:

```
audio_project/
├── README.md                # Project overview and instructions.
├── requirements.txt         # Python dependencies for the backend.
├── recordings/              # Folder where all audio files are stored.
│
├── backend/                 # Backend components: recording, transcription, and analysis.
│   ├── __init__.py
│   ├── app.py               # Main backend API entry-point (e.g., using Flask or FastAPI).
│   ├── recorder.py          # Contains the recording logic.
│   ├── transcriber.py       # Module for transcribing audio files.
│   ├── analyzer.py          # Module for analyzing and improving transcriptions.
│   ├── models/              # Contains model implementation (e.g., for transcription refinement).
│   │   ├── __init__.py
│   │   └── transcription_model.py
│   └── utils.py             # Helper functions (file management, logging, etc.).
│
├── frontend/                # Frontend code (e.g., a React or Vue.js app).
│   ├── package.json         # NPM configuration and dependencies.
│   ├── public/
│   │   └── index.html
│   └── src/
│       ├── App.js           # Main application component.
│       ├── components/      # UI components for displaying transcription & analysis.
│       │   ├── TranscriptionDisplay.js
│       │   └── AnalysisSummary.js
│       └── styles/          # CSS or SASS files for styling.
│
├── config/                  # Configuration files.
│   ├── config.yaml          # Application-wide settings (API keys, model parameters, etc.).
│   └── logging.conf         # Logging configuration.
│
└── tests/                   # Automated tests for backend modules.
    ├── __init__.py
    ├── test_recorder.py     # Tests for the recording functionality.
    ├── test_transcriber.py  # Tests for the transcription pipeline.
    └── test_analyzer.py     # Tests for the analysis module.
```

Feel free to adjust this structure as your project evolves.

---

## Files

- **record_mic_and_system_audio.py:**  
  The main script that:
  - Automatically configures the monitor source on Linux via PulseAudio (`pactl`).
  - Selects both the microphone and system output devices.
  - Records audio concurrently from both sources.
  - Saves three output files (each with a timestamp):
    - `audio_input.wav` – Microphone-only recording.
    - `audio_output.wav` – System output-only recording.
    - `audio_combined.wav` – A mix of both audio sources (stereo).

*Note: Previous standalone scripts have been refactored and merged into this single script.*

---

## Prerequisites

- **Python 3.x**

- **Required Python Packages:**  
  Install the necessary packages using pip:
  ```bash
  pip install sounddevice soundfile numpy
  ```

- **PulseAudio (Linux only):**  
  The project uses PulseAudio commands (`pactl`) for configuring the monitor source automatically.  
  Ensure your system has monitor sources enabled for your audio sinks.

- **Platform Support:**  
  - **Linux:** Uses PulseAudio for monitor source configuration.
  - **Windows:** Uses WASAPI loopback mode to capture system output audio.

---

## Usage

1. **Prepare Your Audio Devices:**  
   Ensure that your microphone and system audio output are properly connected and configured.  
   If you run the script on Linux, the monitor source will be set automatically via `pactl`.

2. **Run the Script:**  
   Execute the following command in your terminal:
   ```bash
   python record_mic_and_system_audio.py
   ```
   The script will begin recording both the microphone and system audio concurrently.

3. **Stop Recording:**  
   When you wish to stop recording, simply press **Enter**.

4. **Output Files:**  
   After recording stops, check the `recordings/` folder. You will find:
   - `audio_input_<timestamp>.wav`
   - `audio_output_<timestamp>.wav`
   - `audio_combined_<timestamp>.wav`
   with `<timestamp>` representing the date and time the recording started.

---

## Customization

- The script is well-commented and organized into focused functions.  
- To adjust parameters (like sample rate, block size, or device selection), refer to the inline comments in `record_mic_and_system_audio.py`.

---

## Troubleshooting

- **No Monitor Source Found on Linux:**  
  Verify your PulseAudio configuration by running:
  ```bash
  pactl list sources short
  ```
  Ensure that monitor sources exist and are active. Use **pavucontrol** if necessary for manual adjustments.

- **Device Selection Issues:**  
  If the automatic device selection does not yield the expected microphone or monitor device, consider modifying the `select_devices` function to suit your configuration.

---

## License

This project is provided "as-is" without any warranty. Feel free to modify, improve, and redistribute as needed.
