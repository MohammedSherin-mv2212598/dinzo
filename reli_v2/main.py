import os
import json
import argparse
from processor import FoodReelProcessor

def main():
    parser = argparse.ArgumentParser(
        description='Process Instagram reels and posts for food content with audio transcription.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument('url', help='Instagram URL to process')
    
    # Basic operation flags
    parser.add_argument('--download', action='store_true', help='Download media files')
    parser.add_argument('--process-llm', action='store_true', help='Process with LLM')
    parser.add_argument('--audio', action='store_true', help='Extract and transcribe audio')
    parser.add_argument('--full', action='store_true', help='Perform all processing steps')
    parser.add_argument('--force-refresh', action='store_true', help='Force refresh even if URL exists in database')
    
    # Configuration options
    parser.add_argument('--download-dir', default='downloads', help='Directory to save downloads')
    parser.add_argument('--api-key', help='Groq API key')
    parser.add_argument('--speech-engine', default='google', choices=['google', 'sphinx', 'wit', 'ibm'], 
                      help='Speech recognition engine to use')
    parser.add_argument('--json', action='store_true', help='Output results as JSON')
    parser.add_argument('--include-transcription', action='store_true', 
                      help='Include transcription in LLM analysis', default=True)
    
    args = parser.parse_args()
    
    # Get API key from arguments, environment, or use default
    api_key = args.api_key or os.environ.get('GROQ_API_KEY') or "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"
    
    # Initialize processor
    processor = FoodReelProcessor(
        groq_api_key=api_key,
        download_dir=args.download_dir,
        speech_engine=args.speech_engine
    )
    
    try:
        # Process URL for metadata
        metadata = processor.process_url(args.url, args.force_refresh)
        if metadata:
            if not args.json:
                print(f"\n✅ Metadata extracted for {args.url}")
                print(json.dumps(metadata, indent=2))
        else:
            print(f"\n❌ Failed to extract metadata for {args.url}")
            return
        
        # Process audio if requested or if full processing
        transcription_data = None
        if args.audio or args.full:
            print("\n----- Processing Audio -----")
            post_data = processor.process_audio(args.url, args.force_refresh)
            
            if post_data and 'transcription' in post_data and post_data['transcription']:
                transcription_data = post_data['transcription']
                if not args.json:
                    print("\n✅ Audio Processing Success")
                    print("\n----- Audio Transcription -----")
                    print(transcription_data)
            else:
                if not args.json:
                    print("\n❓ No transcription available - post may not have audio or transcription failed")
        
        # Download media if requested or if full processing
        if args.download or args.full:
            download_info = processor.download_media(args.url)
            if download_info:
                if not args.json:
                    print(f"\n✅ Media downloaded to {download_info['download_path']}")
                    print(f"Files downloaded:")
                    for file in download_info['files']:
                        print(f"  - {file['name']} ({file['type']})")
            else:
                if not args.json:
                    print("\n❌ Failed to download media.")
        
        # Process with LLM if requested or if full processing
        processed_data = None
        if args.process_llm or args.full:
            if not args.json:
                print("\n----- Processing with LLM -----")
            
            processed_data = processor.process_with_llm(
                args.url, 
                args.force_refresh,
                include_transcription=args.include_transcription
            )
            
            if processed_data:
                if not args.json:
                    print("\n✅ LLM Processing complete:")
                    print(json.dumps(processed_data, indent=2))
                    
                    if processed_data.get('is_food_related'):
                        print("\nThis content is identified as food-related! 🍔")
                        if 'cards' in processed_data:
                            print(f"Found {len(processed_data['cards'])} information cards.")
                    else:
                        print("\nThis content is not identified as food-related. 🚫")
            else:
                if not args.json:
                    print("\n❌ Failed to process with LLM.")
        
        # Output JSON if requested
        if args.json:
            output = {
                "metadata": metadata,
                "transcription": transcription_data,
                "processed_data": processed_data
            }
            print(json.dumps(output, indent=2))
    
    finally:
        processor.close()

if __name__ == "__main__":
    main()