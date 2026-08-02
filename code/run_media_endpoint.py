import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Ensure the parent directory is in the python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from code.io_utils import load_all_data, resolve_media_path
from code.profiles import load_or_build_all_profiles
from code.prompt_builder import build_prompt
from code.model_client import RouterModelClient

def run_multimodal() -> None:
    load_dotenv()
    
    model_name = "gemini-3.5-flash-lite"
    print(f"Testing with model: {model_name}")
    
    root_dir = Path(__file__).resolve().parent.parent
    dataset_dir = root_dir / "dataset"
    profiles_dir = root_dir / "profiles"
    
    data = load_all_data(dataset_dir)
    profiles = load_or_build_all_profiles(data, dataset_dir=dataset_dir, profiles_dir=profiles_dir)
    
    # 1. Select 2 image messages
    image_msgs = [msg for msg in data.messages if msg.media_type == "image"][:2]
    # 2. Select 2 voice note messages
    voice_msgs = [msg for msg in data.messages if msg.media_type == "voice"][:2]
    
    test_msgs = image_msgs + voice_msgs
    print(f"Found {len(image_msgs)} image messages and {len(voice_msgs)} voice messages to test.")
    
    client = RouterModelClient(model_name=model_name)
    
    for msg in test_msgs:
        print("\n" + "="*50)
        print(f"Message ID: {msg.message_id}")
        print(f"Media Type: {msg.media_type}")
        print(f"Media ID: {msg.media_id}")
        print(f"Text Content: {repr(msg.message_text)}")
        
        # Build prompt
        prompt = build_prompt(msg, profiles, [], data)
        
        # Resolve media path
        media_path = resolve_media_path(msg.media_type, msg.media_id, data, dataset_dir)
        print(f"Resolved Media Path: {media_path} (exists: {media_path and media_path.exists()})")
        
        media_list = [media_path] if media_path else None
        
        try:
            print("Calling Gemini model...")
            output = client.call_model(prompt=prompt, media=media_list)
            print("Gemini returned structured output successfully:")
            print(f"  Action: {output.action}")
            print(f"  Type: {output.message_type}")
            print(f"  Reason: {output.reason}")
            print(f"  Confidence (notify/digest/mute): {output.notify_confidence:.2f} / {output.digest_confidence:.2f} / {output.mute_confidence:.2f}")
            print(f"  Evidence IDs: {output.evidence_message_ids}")
        except Exception as e:
            print(f"ERROR calling model for {msg.message_id}: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    run_multimodal()
