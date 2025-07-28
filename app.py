import streamlit as st
import os
from PIL import Image
import pytesseract
import cv2
import numpy as np
import re
from streamlit_webrtc import webrtc_streamer, VideoProcessorBase, RTCConfiguration
import av
from deep_translator import GoogleTranslator
import base64
import tempfile
from gtts import gTTS

# --- Setup ---
FOLDER_DIR = "folders"
os.makedirs(FOLDER_DIR, exist_ok=True)


# --- Streamlit Config ---
st.set_page_config(page_title="WriteRight.ai", layout="wide")

# --- Styling ---
st.markdown("""
    <style>
    html, body, .stApp {
        background-color: #222;
        color: #f1f1f1;
        font-family: 'Segoe UI';
    }
    .main-title {
        font-size: 42px;
        font-weight: 900;
        text-align: center;
        margin-top: 0.5em;
        color: #ffffff;
    }
    .sub-title {
        font-size: 18px;
        color: #cccccc;
        text-align: center;
        margin-bottom: 2em;
    }
    .stButton > button {
        background-color: #444;
        color: white;
        font-weight: 600;
        border-radius: 8px;
    }
    </style>
""", unsafe_allow_html=True)



# --- Header ---
st.markdown("<div class='main-title'>WriteRight.ai</div>", unsafe_allow_html=True)
st.markdown("<div class='sub-title'>Upload handwritten notes → Clean, Translate, Organize, Export ✨</div>", unsafe_allow_html=True)

# --- Sidebar: Folder + Notes ---
st.sidebar.header("📁 Folder Management")

with st.sidebar.expander("➕ Create New Folder"):
    folder_input = st.text_input("Folder Name", key="new_folder")
    if st.button("Create Folder"):
        if folder_input:
            os.makedirs(os.path.join(FOLDER_DIR, folder_input), exist_ok=True)
            st.success(f"Folder '{folder_input}' created!")

folders = [f for f in os.listdir(FOLDER_DIR) if os.path.isdir(os.path.join(FOLDER_DIR, f))]

if folders:
    selected_folder = st.sidebar.selectbox("📂 Select Folder to View Notes", folders)
    note_files = os.listdir(os.path.join(FOLDER_DIR, selected_folder))

    if note_files:
        selected_note = st.sidebar.selectbox("📖 Open Note", note_files)
        with open(os.path.join(FOLDER_DIR, selected_folder, selected_note), 'r', encoding='utf-8') as f:
            note_content = f.read()
        st.sidebar.text_area("✏️ Edit Note", value=note_content, height=200, key="note_edit")
        if st.sidebar.button("💾 Save Changes"):
            with open(os.path.join(FOLDER_DIR, selected_folder, selected_note), 'w', encoding='utf-8') as f:
                f.write(st.session_state.note_edit)
            st.sidebar.success("Note updated!")
        st.sidebar.download_button("📅 Download Note", note_content, file_name=selected_note)
        if st.sidebar.button("🗑️ Delete Note"):
            os.remove(os.path.join(FOLDER_DIR, selected_folder, selected_note))
            st.sidebar.warning("Note deleted. Refresh app.")

if 'selected_folder' in locals() and 'selected_note' in locals():
    st.markdown(f"### 📂 {selected_note}")
    st.code(note_content, language='text')

# --- OCR Helpers ---
def clean_text(text):
    text = re.sub(r'[^\w\s\.,;:\'"!?-]', '', text)
    text = re.sub(r'\n+', '\n', text)
    text = re.sub(r'\s{2,}', ' ', text)
    sentences = re.split(r'(?<=[.!?])\s+', text)
    text = ' '.join(s.capitalize() for s in sentences)
    return text.strip()

class VideoProcessor(VideoProcessorBase):
    def __init__(self):
        self.frame = None
    def recv(self, frame):
        img = frame.to_ndarray(format="bgr24")
        self.frame = img
        return av.VideoFrame.from_ndarray(img, format="bgr24")

# --- Input Options ---
st.header("📥 Upload handwritten image")
uploaded_file = st.file_uploader("🖼️ Upload handwritten image", type=["png", "jpg", "jpeg"])
image_data = None
if uploaded_file:
    image_data = Image.open(uploaded_file)

# --- OCR Output ---
if "cleaned_text" not in st.session_state:
    st.session_state.cleaned_text = ""

lang_options = {
    "English": "eng",
    "Hindi": "hin",
    "Tamil": "tam",
    "Kannada": "kan",
    "Telugu": "tel",
    "Urdu": "urd",
    "Bengali": "ben"
}
ocr_lang_name = st.selectbox("🌐 OCR Language", list(lang_options.keys()), index=0)
ocr_lang = lang_options[ocr_lang_name]

if image_data:
    if st.button("🧐 Convert to Text"):
        with st.spinner("Extracting and cleaning text..."):
            gray = cv2.cvtColor(np.array(image_data), cv2.COLOR_RGB2GRAY)
            raw_text = pytesseract.image_to_string(gray, lang=ocr_lang)
            st.session_state.cleaned_text = clean_text(raw_text)

if st.session_state.cleaned_text:
    st.subheader("📋 OCR Output")
    st.text_area("✏️ Cleaned Text", st.session_state.cleaned_text, height=300, key="cleaned_output")

    target_lang = st.selectbox("🌐 Translate To", ["None", "English", "Hindi", "Tamil", "French", "German", "Spanish", "Arabic", "Chinese"], index=0)
    translated_text = ""
    lang_map = {
        "English": "en",
        "Hindi": "hi",
        "Tamil": "ta",
        "French": "fr",
        "German": "de",
        "Spanish": "es",
        "Arabic": "ar",
        "Chinese": "zh-CN"
    }

    if target_lang != "None":
        try:
            translated_text = GoogleTranslator(source='auto', target=lang_map[target_lang]).translate(st.session_state.cleaned_text)
            st.text_area("🌍 Translated Text", translated_text, height=300)
        except Exception as e:
            st.warning(f"Translation failed: {e}")

    if st.button("🔊 Read Cleaned Text Aloud"):
        try:
            tts = gTTS(text=st.session_state.cleaned_text)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
                tts.save(fp.name)
                audio_file = open(fp.name, "rb")
                audio_bytes = audio_file.read()
                b64 = base64.b64encode(audio_bytes).decode()
                st.markdown(
                    f"""
                    <audio controls autoplay>
                        <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
                    </audio>
                    """,
                    unsafe_allow_html=True
                )
        except Exception as e:
            st.error(f"Text-to-speech failed: {e}")

    if st.button("🔊 Read Translated Text Aloud"):
        try:
            tts = gTTS(text=translated_text)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
                tts.save(fp.name)
                audio_file = open(fp.name, "rb")
                audio_bytes = audio_file.read()
                b64 = base64.b64encode(audio_bytes).decode()
                st.markdown(
                    f"""
                    <audio controls autoplay>
                        <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
                    </audio>
                    """,
                    unsafe_allow_html=True
                )
        except Exception as e:
            st.error(f"Text-to-speech failed: {e}")

    st.download_button("📅 Download as .txt", data=st.session_state.cleaned_text, file_name="note.txt")
    st.button("📋 Copy to Clipboard")

    if st.button("🔄 Upload Another Image"):
        st.session_state.cleaned_text = ""
        st.rerun()

    if folders:
        note_name = st.text_input("📝 Note Title")
        folder_choice = st.selectbox("📁 Save to Folder", folders)
        if st.button("💾 Save Note"):
            save_path = os.path.join(FOLDER_DIR, folder_choice, f"{note_name}.txt")
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(st.session_state.cleaned_text)
            st.success(f"Note saved to {folder_choice} folder.")
