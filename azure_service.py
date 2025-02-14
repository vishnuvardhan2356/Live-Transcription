# azure_service.py

import os
import time
import azure.cognitiveservices.speech as speechsdk
from queue import Queue
import threading
import pyaudio
import wave
from datetime import datetime

# Audio recording parameters
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100

class AudioRecorder:
    def __init__(self):
        self.audio = pyaudio.PyAudio()
        self.frames = []
        self.is_recording = False
        self.thread = None

    def start_recording(self):
        self.frames = []
        self.is_recording = True
        self.thread = threading.Thread(target=self._record)
        self.thread.start()

    def stop_recording(self):
        self.is_recording = False
        if self.thread:
            self.thread.join()

    def _record(self):
        stream = self.audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK
        )

        while self.is_recording:
            data = stream.read(CHUNK)
            self.frames.append(data)

        stream.stop_stream()
        stream.close()

    def save_recording(self, filename):
        if not self.frames:
            return False
        
        wf = wave.open(filename, 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(self.audio.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(self.frames))
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