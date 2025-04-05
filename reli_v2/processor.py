import os
import json
from groq import Groq
from database import Database
from extraction import InstagramExtractor

class FoodReelProcessor:
    def __init__(self, groq_api_key="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", download_dir="downloads", speech_engine="google"):
        """Initialize the food reel processor."""
        self.database = Database()
        self.extractor = InstagramExtractor(download_dir=download_dir, speech_engine=speech_engine)
        self.groq_client = Groq(api_key=groq_api_key)
        self.download_dir = download_dir
    
    def process_url(self, url, force_refresh=False):
        """
        Process an Instagram URL, extract metadata, and save to database.
        
        Args:
            url (str): Instagram URL to process
            force_refresh (bool): Whether to force refresh even if URL exists in database
            
        Returns:
            dict: Metadata for the processed URL
        """
        # Check if URL already exists in database
        if not force_refresh and self.database.post_exists(url):
            print(f"URL {url} already exists in database, retrieving stored data.")
            return self.database.get_post(url)
        
        # Extract metadata
        print(f"Extracting metadata for {url}")
        metadata = self.extractor.extract_metadata(url)
        
        if not metadata:
            print(f"Failed to extract metadata for {url}")
            return None
        
        # Save basic metadata to database
        self.database.save_post(url, metadata)
        
        return metadata
    
    def process_audio(self, url, force_refresh=False):
        """
        Process audio from the Instagram post, extract and transcribe.
        
        Args:
            url (str): Instagram URL to process
            force_refresh (bool): Whether to force refresh even if audio already processed
            
        Returns:
            dict: Post data with transcription if successful
        """
        # Get existing data
        post_data = self.database.get_post(url)
        
        # Check if already processed and transcription exists
        if not force_refresh and post_data and post_data.get('transcription'):
            print(f"Audio for URL {url} already processed, retrieving stored transcription.")
            return post_data
        
        # Make sure we have metadata first
        if not post_data:
            post_data = self.process_url(url)
            
        if not post_data:
            print(f"No metadata available for {url}")
            return None
        
        # Only process if it's a video
        if not post_data.get('is_video', False):
            print(f"URL {url} is not a video, skipping audio processing.")
            return post_data
            
        # Extract and transcribe audio
        print(f"Processing audio for {url}")
        success, transcription, has_audio = self.extractor.process_audio(url)
        
        # Update database with transcription results
        if success and transcription:
            print(f"Successfully transcribed audio: {transcription[:100]}...")
            post_data['transcription'] = transcription
            post_data['has_audio'] = True
            self.database.update_transcription(url, transcription, has_audio=True)
        elif has_audio:
            print(f"Post has audio but transcription failed")
            post_data['has_audio'] = True
            self.database.update_transcription(url, None, has_audio=True)
        else:
            print(f"Post does not have audio or extraction failed")
            post_data['has_audio'] = False
            self.database.update_transcription(url, None, has_audio=False)
        
        return post_data
    
    def process_with_llm(self, url, force_refresh=False, include_transcription=True):
        """
        Process extracted data with LLM to identify food-related content and create cards.
        
        Args:
            url (str): Instagram URL to process
            force_refresh (bool): Whether to force refresh even if URL has already been processed
            include_transcription (bool): Whether to include transcription in LLM analysis
            
        Returns:
            dict: Processed data with food-related information
        """
        # Get existing data from database
        post_data = self.database.get_post(url)
        
        # Check if already processed and not forcing refresh
        if not force_refresh and post_data and post_data.get('processed_data'):
            print(f"URL {url} already processed with LLM, retrieving stored data.")
            return post_data['processed_data']
        
        # Get metadata if not available
        if not post_data:
            post_data = self.process_url(url)
            
        if not post_data:
            print(f"No metadata available for {url}")
            return None
        
        # Process audio if needed and include_transcription is True
        if include_transcription and post_data.get('is_video', False) and not post_data.get('transcription'):
            post_data = self.process_audio(url, force_refresh)
        
        # Prepare transcription content for prompt
        transcription_content = ""
        if include_transcription and post_data.get('transcription'):
            transcription_content = f"\nAudio Transcription: {post_data['transcription']}"
        
        # Prepare prompt for LLM
        prompt = f"""
        Analyze this Instagram content and determine if it's food-related:
        
        URL: {url}
        Title: {post_data.get('title', '')}
        Description: {post_data.get('description', '')}{transcription_content}
        Account: {post_data.get('account_name', '')}
        
        If it's food-related, extract the following information in JSON format:
        1. is_food_related (boolean)
        2. cards - an array of objects with:
           - type: "restaurant", "food", "offer", or "misc"
           - name: name of restaurant or food item
           - description: brief description
           - details: any other relevant details
        
        Return ONLY valid JSON with no other text.
        """
        
        # Call LLM API
        try:
            response = self.groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You analyze Instagram content and extract food-related information."},
                    {"role": "user", "content": prompt}
                ],
                model="llama-3.1-8b-instant",  # Or any other available model
                temperature=0.3
            )
            
            # Parse LLM response
            llm_output = response.choices[0].message.content.strip()
            try:
                processed_data = json.loads(llm_output)
                
                # Update database with processed data
                is_food_related = processed_data.get('is_food_related', False)
                self.database.save_post(
                    url, 
                    post_data, 
                    processed_data, 
                    is_food_related,
                    post_data.get('transcription')
                )
                
                return processed_data
            except json.JSONDecodeError:
                print(f"LLM response is not valid JSON: {llm_output}")
                return None
                
        except Exception as e:
            print(f"Error processing with LLM: {e}")
            import traceback
            traceback.print_exc()
            return None

    def download_media(self, url):
        """
        Download media files for a URL.
        
        Args:
            url (str): Instagram URL to download media for
            
        Returns:
            dict: Information about downloaded files
        """
        return self.extractor.download_media(url)

    def close(self):
        """Close database connection."""
        self.database.close()