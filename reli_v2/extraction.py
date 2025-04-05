import os
import re
import json
import shutil
import time
from functools import lru_cache
import instaloader
import moviepy.editor as mp
import speech_recognition as sr

class InstagramExtractor:
    """Enhanced Instagram content extractor with audio extraction capabilities."""
    
    def __init__(self, download_dir="downloads", speech_engine="google"):
        """Initialize the Instagram extractor."""
        self.loader = instaloader.Instaloader()
        self.download_dir = os.path.abspath(download_dir)
        self.speech_engine = speech_engine
        self.recognizer = sr.Recognizer()
        
        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)
    
    @staticmethod
    def normalize_path(path):
        """Normalize file path to ensure compatibility across systems."""
        if not path:
            return path
        # Replace any weird Unicode backslashes with standard ones
        path = path.replace('﹨', '\\')
        # Use os.path.normpath to standardize the path format
        return os.path.normpath(path)
            
    @staticmethod
    @lru_cache(maxsize=128)  # Cache results for efficiency
    def extract_shortcode(url):
        """Extract shortcode from Instagram URL using regex for efficiency."""
        # Remove query parameters and trailing slashes
        clean_url = url.split('?')[0].rstrip('/')
        
        # Try to extract using regex patterns
        patterns = [
            r'instagram\.com/p/([^/]+)',
            r'instagram\.com/reel/([^/]+)',
            r'instagram\.com/tv/([^/]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, clean_url)
            if match:
                return match.group(1)
        
        # Fallback to splitting the URL
        parts = clean_url.split('/')
        if len(parts) > 1:
            return parts[-1]
        
        raise ValueError(f"Could not extract shortcode from URL: {url}")

    def extract_metadata(self, url):
        """Extract basic metadata from an Instagram post or reel."""
        try:
            # Extract shortcode from URL
            shortcode = self.extract_shortcode(url)
            
            # Get post by shortcode
            post = instaloader.Post.from_shortcode(self.loader.context, shortcode)
            
            # Extract basic metadata
            metadata = {
                'url': url,
                'shortcode': shortcode,
                'title': post.title if hasattr(post, 'title') else '',
                'description': post.caption if post.caption else '',
                'timestamp': post.date.isoformat() if post.date else '',
                'account_name': post.owner_username,
                'account_followers': 0,
                'account_category': '',
                'is_video': post.is_video,
                'has_audio': False,  # Will be updated if audio is extracted
            }
            
            # Try to get more profile information if possible
            try:
                profile = post.owner_profile
                metadata['account_followers'] = profile.followers if hasattr(profile, 'followers') else 0
                metadata['account_category'] = profile.business_category_name if hasattr(profile, 'business_category_name') else ''
            except:
                # Silently continue if profile details aren't available
                pass
                
            return metadata
            
        except Exception as e:
            print(f"Error extracting metadata: {e}")
            import traceback
            traceback.print_exc()
            return None

    def download_media(self, url):
        """Download media files from an Instagram post or reel."""
        try:
            # Extract shortcode from URL
            shortcode = self.extract_shortcode(url)
            
            # Create a unique directory for this download
            download_path = os.path.join(self.download_dir, shortcode)
            download_path = self.normalize_path(download_path)
            
            # Clear existing directory if it exists
            if os.path.exists(download_path):
                shutil.rmtree(download_path)
            
            os.makedirs(download_path)
            
            # Get post by shortcode
            post = instaloader.Post.from_shortcode(self.loader.context, shortcode)
            
            # Download the post (change directory for cleaner downloads)
            print(f"Downloading to: {download_path}")
            original_dir = os.getcwd()
            os.chdir(download_path)
            self.loader.download_post(post, target='.')
            os.chdir(original_dir)
            
            # Wait for files to be completely written
            time.sleep(1)
            
            # Find all downloaded files
            files = []
            for root, _, filenames in os.walk(download_path):
                for filename in filenames:
                    file_path = os.path.join(root, filename)
                    file_path = self.normalize_path(file_path)
                    file_type = None
                    
                    if filename.lower().endswith(('.mp4', '.mov')):
                        file_type = 'video'
                    elif filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                        file_type = 'image'
                    elif filename.lower().endswith('.txt'):
                        file_type = 'text'
                        
                    if file_type:
                        files.append({
                            'path': file_path,
                            'type': file_type,
                            'name': filename
                        })
            
            return {
                'download_path': download_path,
                'files': files
            }
            
        except Exception as e:
            print(f"Error downloading media: {e}")
            import traceback
            traceback.print_exc()
            return None
            
    def _find_video_file(self, download_info):
        """Find a video file in the downloaded files."""
        if not download_info or 'files' not in download_info:
            return None
            
        for file_info in download_info['files']:
            if file_info['type'] == 'video' and os.path.exists(file_info['path']):
                return file_info['path']
                
        return None
    
    def extract_audio(self, video_path):
        """
        Extract audio from a video file.
        Returns: (success, audio_path)
        """
        try:
            print("\n----- Extracting Audio -----")
            video_path = self.normalize_path(video_path)
            print(f"Processing video: {video_path}")
            
            # Check if file exists
            if not os.path.exists(video_path):
                print(f"Video file does not exist: {video_path}")
                return False, None
            
            # Set audio path
            video_dir = os.path.dirname(video_path)
            audio_path = os.path.join(video_dir, "audio.wav")
            audio_path = self.normalize_path(audio_path)
            
            # Extract audio
            with mp.VideoFileClip(video_path) as video:
                if video.audio:
                    print(f"Extracting audio to: {audio_path}")
                    video.audio.write_audiofile(audio_path, verbose=False)
                    print(f"Audio extracted to: {audio_path}")
                    return True, audio_path
                else:
                    print("No audio track found in video")
                    return False, None
                
        except Exception as e:
            print(f"Error extracting audio: {e}")
            import traceback
            traceback.print_exc()
            return False, None
    
    def transcribe_audio(self, audio_path):
        """
        Transcribe audio using speech recognition.
        Returns: (success, transcription)
        """
        try:
            print("\n----- Transcribing Audio -----")
            audio_path = self.normalize_path(audio_path)
            
            # Check if file exists
            if not os.path.exists(audio_path):
                print(f"Audio file does not exist: {audio_path}")
                return False, None
            
            # Load the audio file and transcribe
            print(f"Loading audio file: {audio_path}")
            with sr.AudioFile(audio_path) as source:
                # Adjust for ambient noise
                print("Adjusting for ambient noise...")
                self.recognizer.adjust_for_ambient_noise(source)
                
                # Record the audio
                print("Recording audio...")
                audio = self.recognizer.record(source)
            
            # Select the appropriate recognition engine
            print(f"Recognizing speech using {self.speech_engine}...")
            if self.speech_engine == "google":
                transcription = self.recognizer.recognize_google(audio)
            elif self.speech_engine == "sphinx":
                transcription = self.recognizer.recognize_sphinx(audio)
            elif self.speech_engine == "wit":
                # This requires a Wit.ai API key
                transcription = self.recognizer.recognize_wit(audio, key="YOUR_WIT_AI_KEY")
            elif self.speech_engine == "ibm":
                # This requires IBM credentials
                transcription = self.recognizer.recognize_ibm(audio, username="YOUR_USERNAME", password="YOUR_PASSWORD")
            else:
                # Default to Google
                transcription = self.recognizer.recognize_google(audio)
            
            print(f"Transcription completed successfully")
            return True, transcription
            
        except sr.UnknownValueError:
            print("Could not understand audio")
            return False, None
        except sr.RequestError as e:
            print(f"Could not request results; {e}")
            return False, None
        except Exception as e:
            print(f"Error in transcription: {e}")
            import traceback
            traceback.print_exc()
            return False, None
    
    def process_audio(self, url):
        """
        Process Instagram post: download, extract audio, and transcribe.
        Returns: (success, transcription, has_audio)
        """
        # Download the media
        download_info = self.download_media(url)
        if not download_info:
            print("Failed to download media from the URL")
            return False, None, False
        
        # Find video file
        video_path = self._find_video_file(download_info)
        if not video_path:
            print("No video file found in downloaded content")
            return False, None, False
        
        # Extract audio
        extract_success, audio_path = self.extract_audio(video_path)
        if not extract_success:
            print("Failed to extract audio from video")
            return False, None, False
        
        # Transcribe audio
        transcribe_success, transcription = self.transcribe_audio(audio_path)
        if not transcribe_success:
            print("Failed to transcribe audio")
            return False, None, True  # Has audio but couldn't transcribe
        
        return True, transcription, True