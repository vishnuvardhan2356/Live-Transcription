# azure_service.py

import os
import time
import azure.cognitiveservices.speech as speechsdk
from queue import Queue
import threading
import numpy as np
import sounddevice as sd
import wave
from datetime import datetime


# Audio recording parameters
CHUNK = 1024
FORMAT = np.int16    
CHANNELS = 1
RATE = 44100

class AudioRecorder:
    def __init__(self):
        self.frames = []
        self.is_recording = False
        self.stream = None
        self.thread = None

    def start_recording(self):
        if not self.is_recording:
            self.is_recording = True
            self.frames = []
            self.thread = threading.Thread(target=self._record)
            self.thread.start()

    def stop_recording(self):
        self.is_recording = False
        if self.thread:
            self.thread.join()

    def _record(self):
        def callback(indata, frames, time, status):
            if status:
                print(status)
            self.frames.append(indata.copy())

        with sd.InputStream(samplerate=RATE, channels=CHANNELS, dtype=FORMAT, callback=callback):
            while self.is_recording:
                sd.sleep(100)  # Sleep for small intervals and allow callback to collect data

    def save_recording(self, filename):
        if not self.frames:
            return False

        # Flatten the list of frames into a single numpy array
        audio_data = np.concatenate(self.frames, axis=0)

        # Save the recorded frames as a wave file
        wf = wave.open(filename, 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)  # 2 bytes for Format np.int16
        wf.setframerate(RATE)
        wf.writeframes(audio_data.astype(np.int16).tobytes())
        wf.close()
        return True

class AzureTranscriptionService:
    def __init__(self, speech_key, speech_region):
        self.speech_key = speech_key
        self.speech_region = speech_region

    def recognize_from_file(self, audio_file):
        message_queue = Queue()
        speech_config = speechsdk.SpeechConfig(
            subscription=self.speech_key, 
            region=self.speech_region
        )
        speech_config.speech_recognition_language = "en-IN"
        speech_config.enable_dictation()
        
        audio_config = speechsdk.audio.AudioConfig(filename=audio_file)
        speech_recognizer = speechsdk.SpeechRecognizer(
            speech_config=speech_config, 
            audio_config=audio_config
        )

        initial_response_time = None

        def update_metrics(evt):
            nonlocal initial_response_time
            if initial_response_time is None:
                initial_response_time = time.time() - start_time
                print(f"Initial Response Time: {initial_response_time:.2f} seconds")

        start_time = time.time()
        done = False

        def stop_cb(evt):
            nonlocal done
            done = True
        

        speech_recognizer.recognizing.connect(
            lambda evt: message_queue.put(('recognizing', evt.result.text))
        )
        speech_recognizer.recognized.connect(
            lambda evt: message_queue.put(('recognized', evt.result.text))
        )

        speech_recognizer.session_stopped.connect(stop_cb)
        speech_recognizer.canceled.connect(stop_cb)

        speech_recognizer.start_continuous_recognition()
        return message_queue, speech_recognizer

    def recognize_from_microphone(self):
        message_queue = Queue()
        speech_config = speechsdk.SpeechConfig(
            subscription=self.speech_key, 
            region=self.speech_region
        )
        speech_config.speech_recognition_language = "en-IN"
        speech_config.enable_dictation()
        
        audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True)
        speech_recognizer = speechsdk.SpeechRecognizer(
            speech_config=speech_config, 
            audio_config=audio_config
        )

        initial_response_time = None

        def update_metrics(evt):
            nonlocal initial_response_time
            if initial_response_time is None:
                initial_response_time = time.time() - start_time
                print(f"Initial Response Time: {initial_response_time:.2f} seconds")
        

        start_time = time.time()
        done = False
        
        def stop_cb(evt):
            print("Recognition stopped.")

        speech_recognizer.recognizing.connect(
            lambda evt: message_queue.put(('recognizing', evt.result.text))
        )
        speech_recognizer.recognized.connect(
            lambda evt: message_queue.put(('recognized', evt.result.text))
        )

        speech_recognizer.session_stopped.connect(stop_cb)
        speech_recognizer.canceled.connect(stop_cb)

        speech_recognizer.start_continuous_recognition()
        return message_queue, speech_recognizer


