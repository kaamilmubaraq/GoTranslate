import os
import urllib.request
import tarfile
import lzma
import shutil
import json
import sys

def install_local_dictionary():
    print("🚀 Starting Manual Dictionary Installation...")
    
    # 1. Get the download URL dynamically from PyPI
    print("🔍 Finding latest dictionary version...")
    try:
        with urllib.request.urlopen("https://pypi.org/pypi/jamdict-data/json") as url:
            data = json.loads(url.read().decode())
            # Find the source tar.gz
            download_url = None
            for release in data['urls']:
                if release['packagetype'] == 'sdist':
                    download_url = release['url']
                    break
            
            if not download_url:
                raise Exception("Could not find download URL")
                
    except Exception as e:
        print(f"❌ Error finding URL: {e}")
        return

    # 2. Download the package
    tar_name = "jamdict_data_temp.tar.gz"
    print(f"⬇️ Downloading dictionary data (approx 50MB)...")
    try:
        urllib.request.urlretrieve(download_url, tar_name)
    except Exception as e:
        print(f"❌ Download failed: {e}")
        return

    # 3. Extract and Decompress
    print("📦 Extracting files (this may take a moment)...")
    try:
        # Open the tar.gz
        with tarfile.open(tar_name, "r:gz") as tar:
            # Look for the .xz database file inside
            member = [m for m in tar.getmembers() if m.name.endswith("jamdict.db.xz")][0]
            
            # Extract the .xz file to a temp file
            f_xz = tar.extractfile(member)
            
            # Decompress .xz -> .db
            print("⏳ Decompressing database (Slow step)...")
            with lzma.open(f_xz) as compressed:
                with open("jamdict.db", "wb") as out_db:
                    shutil.copyfileobj(compressed, out_db)
                    
        print("✅ jamdict.db successfully created in this folder!")
        
    except Exception as e:
        print(f"❌ Extraction failed: {e}")
    finally:
        # Cleanup
        if os.path.exists(tar_name):
            os.remove(tar_name)

if __name__ == "__main__":
    install_local_dictionary()