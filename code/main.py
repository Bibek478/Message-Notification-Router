import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Ensure the parent directory is in the python path for importing code.* modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from code.io_utils import load_all_data
from code.profiles import load_or_build_all_profiles, validate_profile_coverage

def main() -> None:
    """Orchestrator entry point (runs loading, pre-computation, and inference loop)."""
    # Load environment variables
    load_dotenv()
    
    # Check GEMINI_API_KEY presence
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if gemini_api_key:
        print("[main] GEMINI_API_KEY environment variable is configured.")
    else:
        print("[main] Warning: GEMINI_API_KEY is not set in environment or .env file.")
    
    # Path setup
    root_dir = Path(__file__).resolve().parent.parent
    dataset_dir = root_dir / "dataset"
    
    print(f"[main] Loading dataset from {dataset_dir}...")
    try:
        data = load_all_data(dataset_dir)
        print("[main] Data loaded successfully:")
        print(f"  - Users: {len(data.users)}")
        print(f"  - Daily summaries: {len(data.daily_notification_summary)}")
        print(f"  - Groups: {len(data.groups)}")
        print(f"  - Group members: {len(data.group_members)}")
        print(f"  - Business accounts: {len(data.business_accounts)}")
        print(f"  - User business history: {len(data.user_business_history)}")
        print(f"  - Message history: {len(data.message_history)}")
        print(f"  - Message events: {len(data.message_events)}")
        print(f"  - Images: {len(data.images)}")
        print(f"  - Voice notes: {len(data.voice_notes)}")
        print(f"  - Messages to route: {len(data.messages)}")
        print(f"  - Sample messages: {len(data.sample_messages)}")
        
        # Validation
        message_count = len(data.messages)
        message_ids = [message.message_id for message in data.messages]
        if len(message_ids) == len(set(message_ids)):
            print(f"[main] VALIDATION SUCCESS: Loaded {message_count} unique message_id rows from messages.csv.")
        else:
            print(f"[main] VALIDATION FAILURE: Found duplicate message_id values in messages.csv ({message_count} rows loaded).")

        profiles_dir = root_dir / "profiles"
        profile_store = load_or_build_all_profiles(data, dataset_dir=dataset_dir, profiles_dir=profiles_dir)
        coverage_report = validate_profile_coverage(data, profile_store)
        print(f"[main] Profile cache ready: {len(profile_store.user_base_profiles)} base profiles, {sum(len(rows) for rows in profile_store.user_group_profiles.values())} group profiles, {sum(len(rows) for rows in profile_store.user_business_profiles.values())} business profiles.")
        if coverage_report.is_complete:
            print("[main] VALIDATION SUCCESS: Every message user_id has a base profile.")
        else:
            missing = ", ".join(coverage_report.missing_user_ids)
            print(f"[main] VALIDATION FAILURE: Missing base profiles for message users: {missing}")
            
    except Exception as e:
        print(f"[main] CRITICAL ERROR during dataset loading or validation: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
