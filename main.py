# main.py
import streamlit as st
import os
import time
from azure_service import AudioRecorder, AzureTranscriptionService
import threading
from datetime import datetime

# Initialize Azure service
SPEECH_KEY = st.secrets["AZURE_SPEECH_KEY"]
SPEECH_REGION = st.secrets["AZURE_REGION"]


def main():
    st.set_page_config(page_title="Live Transcription", layout="wide")

    # Custom CSS with reduced top margins
    st.markdown("""
        <style>
        .stTabs [data-baseweb="tab-list"] {
            gap: 24px;
        }
        .stTabs [data-baseweb="tab"] {
            padding: 10px 20px;
        }
        .transcription-box {
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 15px;
            margin: 10px 0;
            background-color: rgb(82, 83, 84);
            height: 300px;
            overflow-y: auto;
            white-space: pre-wrap;
            word-wrap: break-word;
        }
        .stTextArea textarea {
            height: 300px;
        }
        /* Reduce top margin of the main container */
        .main .block-container {
            padding-top: 2rem;
            padding-bottom: 0rem;
            margin-top: -60px;
        }
        /* Adjust header spacing */
        h1 {
            margin-top: -20px;
            margin-bottom: 20px;
            padding-bottom: 10px;
        }
        /* Adjust tab spacing */
        .stTabs {
            margin-top: -20px;
        }
        /* Adjust upload section spacing */
        .upload-section {
            margin-top: -15px;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("""
        <h1 style='text-align: left; color:rgb(231, 235, 239);'>
        Live Transcription
        </h1>
    """, unsafe_allow_html=True)

    # Initialize session state
    if 'azure_service' not in st.session_state:
        st.session_state.azure_service = AzureTranscriptionService(SPEECH_KEY, SPEECH_REGION)
    if 'recorder' not in st.session_state:
        st.session_state.recorder = AudioRecorder()
    if 'recording' not in st.session_state:
        st.session_state.recording = False
    if 'azure_transcript' not in st.session_state:
        st.session_state.azure_transcript = ""
    if 'interim_transcript' not in st.session_state:
        st.session_state.interim_transcript = ""

    # Create tabs
    tab1, tab2 = st.tabs(["Upload File", "Record"])

    # Tab 1: Upload File
    with tab1:
        st.header("Upload Audio File")
        uploaded_file = st.file_uploader("Choose an audio file", type=['wav', 'mp3', 'm4a'])
        
        if uploaded_file is not None:
            st.audio(uploaded_file)
            
            if st.button("Transcribe", key="transcribe_upload"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("### Azure Transcript")
                    azure_placeholder = st.empty()
                    
                    # Process uploaded file
                    temp_filename = f"temp_{uploaded_file.name}"
                    with open(temp_filename, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    
                    message_queue, recognizer = st.session_state.azure_service.recognize_from_file(temp_filename)
                    
                    complete_transcript = ""
                    interim_transcript = ""
                    
                    while True:
                        if not message_queue.empty():
                            msg_type, text = message_queue.get()
                            if text.strip():
                                if msg_type == 'recognizing':
                                    interim_transcript = text
                                    display_text = complete_transcript + "\n" + interim_transcript if complete_transcript else interim_transcript
                                    azure_placeholder.markdown(
                                        f'<div class="transcription-box">{display_text}</div>', 
                                        unsafe_allow_html=True
                                    )
                                elif msg_type == 'recognized':
                                    complete_transcript = complete_transcript + "\n" + text if complete_transcript else text
                                    azure_placeholder.markdown(
                                        f'<div class="transcription-box">{complete_transcript}</div>', 
                                        unsafe_allow_html=True
                                    )
                        time.sleep(0.1)
                
                with col2:
                    st.markdown("### Deepgram Transcript")
                    st.markdown('<div class="transcription-box">Deepgram transcription will appear here...</div>', 
                              unsafe_allow_html=True)
            else:
                # Display empty boxes before transcription
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("### Azure Transcript")
                    st.markdown('<div class="transcription-box">Click Transcribe to start...</div>', 
                              unsafe_allow_html=True)
                with col2:
                    st.markdown("### Deepgram Transcript")
                    st.markdown('<div class="transcription-box">Deepgram transcription will appear here...</div>', 
                              unsafe_allow_html=True)

    # Tab 2: Record
    with tab2:
        st.header("Record Audio")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Start Recording", disabled=st.session_state.recording):
                st.session_state.recording = True
                st.session_state.azure_transcript = ""  # Clear previous transcript
                st.session_state.recorder.start_recording()
                st.rerun()
        
        with col2:
            if st.button("Stop Recording", disabled=not st.session_state.recording):
                st.session_state.recording = False
                st.session_state.recorder.stop_recording()
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"recording_{timestamp}.wav"
                if st.session_state.recorder.save_recording(filename):
                    st.success("Recording saved successfully!")
                st.rerun()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### Azure Transcript")
            azure_placeholder = st.empty()
            
            if st.session_state.recording:
                message_queue, recognizer = st.session_state.azure_service.recognize_from_microphone()
                
                while st.session_state.recording:
                    if not message_queue.empty():
                        msg_type, text = message_queue.get()
                        if text.strip():
                            if msg_type == 'recognizing':
                                st.session_state.interim_transcript = text
                                display_text = st.session_state.azure_transcript + "\n" + st.session_state.interim_transcript if st.session_state.azure_transcript else st.session_state.interim_transcript
                            elif msg_type == 'recognized':
                                st.session_state.azure_transcript = st.session_state.azure_transcript + "\n" + text if st.session_state.azure_transcript else text
                                display_text = st.session_state.azure_transcript
                            
                            azure_placeholder.markdown(
                                f'<div class="transcription-box">{display_text}</div>', 
                                unsafe_allow_html=True
                            )
                    time.sleep(0.1)
            
            # Display the stored transcript even when not recording
            display_text = st.session_state.azure_transcript if st.session_state.azure_transcript else "Start recording to see transcription..."
            azure_placeholder.markdown(
                f'<div class="transcription-box">{display_text}</div>', 
                unsafe_allow_html=True
            )
        
        with col2:
            st.markdown("### Deepgram Transcript")
            st.markdown('<div class="transcription-box">Deepgram transcription will appear here...</div>', 
                      unsafe_allow_html=True)

if __name__ == "__main__":
    main()