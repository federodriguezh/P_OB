import os
import glob
import json
import subprocess
from datetime import datetime
from kaggle.api.kaggle_api_extended import KaggleApi

def upload_to_kaggle(dataset_name, files):
    """Upload files to Kaggle dataset after processing"""
    try:
        # Initialize and authenticate Kaggle API
        api = KaggleApi()
        api.authenticate()
        
        if not os.path.exists('data'):
            os.makedirs('data')
            
        if not os.path.exists('data/kaggle_data'):
            os.makedirs('data/kaggle_data')
        
        try:
            # Download existing dataset if it exists
            api.dataset_download_files(f"federodriguezh/{dataset_name}", path='data/existing', unzip=True)
            existing_file = 'data/existing/processed_data.json'
        except:
            existing_file = None

        # Read and combine all files
        combined_data = []
        
        # Check size of existing file
        if existing_file and os.path.exists(existing_file):
            if os.path.getsize(existing_file) > 1.5 * 1024 * 1024 * 1024:  # 1.5GB in bytes
                # Move existing file to kaggle_data as chunked
                chunked_file = os.path.join('data/kaggle_data', 'chunked_data.json')
                os.rename(existing_file, chunked_file)
            else:
                # Read existing data if file size is under 1.5GB
                with open(existing_file, 'r') as f:
                    for line in f:
                        combined_data.append(json.loads(line))

        # Add new data
        for file in files:
            with open(file, 'r') as f:
                for line in f:
                    data = json.loads(line)
                    # Skip records with id=1 (subscription confirmation messages)
                    if data.get('id') != 1:
                        combined_data.append(data)
        
        # Remove duplicates based on entire record
        unique_data = []
        seen = set()
        for record in combined_data:
            record_str = json.dumps(record, sort_keys=True)
            if record_str not in seen:
                seen.add(record_str)
                unique_data.append(record)
                
        # Write processed data to new file in kaggle_data folder
        processed_file = os.path.join('data/kaggle_data', 'processed_data.json')
        with open(processed_file, 'w') as f:
            for record in unique_data:
                json.dump(record, f)
                f.write('\n')
        
        # Create dataset-metadata.json in kaggle_data folder
        metadata = {
            "title": dataset_name,
            "id": f"federodriguezh/{dataset_name}",
            "licenses": [{"name": "CC0-1.0"}],
            "isPrivate": True
        }
        
        metadata_file = os.path.join('data/kaggle_data', 'dataset-metadata.json')
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f)

        # Upload to Kaggle using kaggle_data folder
        api.dataset_create_version(
            folder='data/kaggle_data',
            version_notes=f"Auto update {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        # Clean up files
        for file in glob.glob('data/kaggle_data/*'):
            os.remove(file)
        if os.path.exists('data/existing'):
            subprocess.run(['rm', '-rf', 'data/existing'])
        if os.path.exists('data/kaggle_data'):
            subprocess.run(['rm', '-rf', 'data/kaggle_data'])
        
        return True
    
    except Exception as e:
        print(f"Error processing/uploading to Kaggle: {str(e)}")
        return False

def cleanup_files():
    """Clean up json files when count exceeds 10"""
    json_files = glob.glob('data/*.json')
    if len(json_files) > 10:
        # Sort files by creation time
        json_files.sort(key=os.path.getctime)
        
        # Upload to Kaggle
        if upload_to_kaggle("btcp-ob", json_files):
            try:
                # Use git rm to remove the files
                subprocess.run(['git', 'rm', '-f'] + json_files, check=True)
                print(f"Successfully removed files using git rm")
                
                # Configure git
                subprocess.run(['git', 'config', '--local', 'user.email', 'github-actions[bot]@users.noreply.github.com'])
                subprocess.run(['git', 'config', '--local', 'user.name', 'github-actions[bot]'])
                
                # Commit and push changes
                subprocess.run(['git', 'commit', '-m', 'Remove processed files [skip ci]'])
                subprocess.run(['git', 'push'])
                print("Successfully committed and pushed changes")
                
            except subprocess.CalledProcessError as e:
                print(f"Error in git operations: {str(e)}")

if __name__ == "__main__":
    cleanup_files()
