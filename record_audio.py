import sounddevice as sd
import soundfile as sf
import sys
import numpy as np
import queue

# Configuración
samplerate = 44100  # Frecuencia de muestreo

# Seleccionar dispositivo de grabación según el sistema
if sys.platform.startswith('win'):
    output_device = 1  # Reemplaza este número con el índice WASAPI adecuado
else:
    # En Linux, buscar automáticamente un dispositivo de monitor (entrada) en PulseAudio.
    devices = sd.query_devices()
    monitor_device = None
    for idx, dev in enumerate(devices):
        if dev['max_input_channels'] > 0 and "monitor" in dev['name'].lower():
            monitor_device = idx
            break
    if monitor_device is None:
        # Intentar buscar dispositivos con 'monitor' en el nombre.
        monitor_candidates = [(idx, dev) for idx, dev in enumerate(devices)
                              if dev['max_input_channels'] > 0 and "monitor" in dev['name'].lower()]
        if not monitor_candidates:
            print("No se encontraron dispositivos cuyo nombre contenga 'monitor'.")
            print("Advertencia: Es probable que el dispositivo seleccionado sea el micrófono.")
            # Fallback: listar todos los dispositivos de entrada con canales disponibles.
            fallback_candidates = [(idx, dev) for idx, dev in enumerate(devices) if dev['max_input_channels'] > 0]
            print("Seleccione de la siguiente lista un dispositivo de entrada:")
            for idx, dev in fallback_candidates:
                print(f"{idx}: {dev['name']} – Canales de entrada: {dev['max_input_channels']}")
            output_device = int(input("Introduzca el índice del dispositivo que desea usar: "))
        else:
            print("Seleccione de la siguiente lista un dispositivo monitor:")
            for idx, dev in monitor_candidates:
                print(f"{idx}: {dev['name']} – Canales de entrada: {dev['max_input_channels']}")
            output_device = int(input("Introduzca el índice del dispositivo monitor que desea usar: "))
    else:
        output_device = monitor_device

# Imprimir dispositivos disponibles para ayudar en la selección
print("\nDispositivos de audio disponibles:")
print(sd.query_devices())
print()

# Seleccionar dispositivo para el micrófono que NO sea un dispositivo monitor.
mic_candidates = [(idx, dev) for idx, dev in enumerate(devices)
                  if dev['max_input_channels'] > 0 and "monitor" not in dev['name'].lower()]
if not mic_candidates:
    raise ValueError("No se encontró ningún dispositivo de micrófono que no sea monitor.")
# Seleccionamos el primer candidato; alternativamente, se puede pedir la elección al usuario.
mic_device = mic_candidates[0][0]
mic_device_info = sd.query_devices(mic_device, 'input')
mic_channels = mic_device_info['max_input_channels']
if mic_channels < 1:
    raise ValueError("El dispositivo del micrófono no soporta canales de entrada.")
print(f"El dispositivo del micrófono soporta {mic_channels} canal(es).")
# Opcional: para la grabación, usamos 1 canal (mono) para el micrófono.  
mic_channels_to_use = 1

if output_device == mic_device:
    valid_candidates = [(idx, dev) for idx, dev in enumerate(devices)
                        if dev['max_input_channels'] > 0 and idx != mic_device and "monitor" in dev['name'].lower()]
    if valid_candidates:
        output_device = valid_candidates[0][0]
        print(f"Se seleccionó automáticamente el dispositivo monitor: {output_device} - {valid_candidates[0][1]['name']}")
    else:
        raise ValueError("No hay dispositivo monitor distinto al micrófono. Configure un dispositivo monitor en PulseAudio.")

# Obtener información del dispositivo de acuerdo al sistema operativo
if sys.platform.startswith('win'):
    device_info = sd.query_devices(output_device, 'input')
    supported_channels = device_info['max_input_channels']
else:
    # En Linux/Mac, para dispositivos monitor en PulseAudio, se debe usar el dispositivo que aparece como entrada
    device_info = sd.query_devices(output_device, 'input')
    supported_channels = device_info['max_input_channels']
if supported_channels < 2:
    print(f"Warning: The selected device only supports {supported_channels} channel(s). Stereo recording requires a device with at least 2 input channels.")
    channels_to_use = supported_channels  # or force the user to choose a different device
else:
    channels_to_use = 2
print(f"Selected device supports {supported_channels} channel(s). Using {channels_to_use} channels for recording.")

# Obtener la frecuencia de muestreo por defecto de ambos dispositivos.
mic_default_sr = float(mic_device_info.get('default_samplerate', 44100))
out_default_sr = float(device_info.get('default_samplerate', 44100))

# Primero, intentar usar la frecuencia del dispositivo de salida.
try:
    sd.check_input_settings(device=mic_device, samplerate=out_default_sr, channels=mic_channels_to_use)
    sd.check_input_settings(device=output_device, samplerate=out_default_sr, channels=channels_to_use)
    samplerate = out_default_sr
except Exception as e1:
    print(f"No se pudo usar la frecuencia {out_default_sr}Hz para ambos dispositivos: {e1}")
    # Intentar usar la frecuencia del micrófono
    try:
        sd.check_input_settings(device=mic_device, samplerate=mic_default_sr, channels=mic_channels_to_use)
        sd.check_input_settings(device=output_device, samplerate=mic_default_sr, channels=channels_to_use)
        samplerate = mic_default_sr
        print(f"Usando la frecuencia del micrófono: {mic_default_sr}Hz para ambas grabaciones.")
    except Exception as e2:
        raise ValueError("No se pudo encontrar una frecuencia de muestreo que ambos dispositivos soporten.")
        
samplerate = int(samplerate)
print(f"Using sample rate: {samplerate}")

# Grabación continua hasta que el usuario decida detenerla.

# Listas para almacenar bloques de audio de cada fuente
mic_frames = []
output_frames = []

def mic_callback(indata, frames, time, status):
    if status:
        print("Mic:", status, flush=True)
    mic_frames.append(indata.copy())

def output_callback(indata, frames, time, status):
    if status:
        print("Output:", status, flush=True)
    output_frames.append(indata.copy())

# Configurar parámetros para la grabación del micrófono
mic_stream_params = dict(
    samplerate=samplerate,
    device=mic_device,
    channels=mic_channels_to_use,
    callback=mic_callback,
    blocksize=1024
)

print("Grabando ambos audios (micrófono y salida)... Presione Enter para detener.")
if sys.platform.startswith('win'):
    output_stream_params = dict(
        samplerate=samplerate,
        device=output_device,
        channels=channels_to_use,
        callback=output_callback,
        blocksize=1024,
        loopback=True
    )
else:
    output_stream_params = dict(
        samplerate=samplerate,
        device=output_device,
        channels=channels_to_use,
        callback=output_callback,
        blocksize=1024
    )

with sd.InputStream(**mic_stream_params), sd.InputStream(**output_stream_params):
    input()  # Espera a que el usuario presione Enter para detener la grabación

# Concatenar los bloques de audio grabados para cada fuente
mic_data = np.concatenate(mic_frames, axis=0)
output_data = np.concatenate(output_frames, axis=0)

# Asegurarse de que ambas grabaciones tengan el mismo número de fotogramas
min_len = min(len(mic_data), len(output_data))
mic_data = mic_data[:min_len]
output_data = output_data[:min_len]

# Si la grabación del sistema es estéreo (2 canales) y el mic es mono (1 canal),
# se duplica la señal del micrófono para poder combinarla en ambos canales.
if output_data.ndim == 2 and output_data.shape[1] == 2 and mic_data.ndim == 2 and mic_data.shape[1] == 1:
    mic_stereo = np.tile(mic_data, (1, 2))
else:
    mic_stereo = mic_data

# Combinar las dos señales:
# Se suma la señal del sistema y la señal del micrófono (duplicada si es necesario) y se escala la suma.
combined_audio = 0.5 * (output_data + mic_stereo)

# Guardar archivo combinado
sf.write("audio_combined.wav", combined_audio, samplerate, subtype='PCM_16')
print("Audio combinado guardado en 'audio_combined.wav'")
