
import nltk
import shutil
import os
import ssl

# Bypass SSL check if needed (sometimes causes download issues)
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

def fix_nltk():
    print("Searching for corrupted NLTK data...")
    found = False
    for path in nltk.data.path:
        punkt_path = os.path.join(path, 'tokenizers', 'punkt')
        punkt_zip = os.path.join(path, 'tokenizers', 'punkt.zip')
        
        if os.path.exists(punkt_path):
            print(f"Removing directory: {punkt_path}")
            shutil.rmtree(punkt_path)
            found = True
            
        if os.path.exists(punkt_zip):
            print(f"Removing file: {punkt_zip}")
            os.remove(punkt_zip)
            found = True
            
    if not found:
        print("No existing 'punkt' data found to delete.")
    
    print("Downloading 'punkt' tokenizer freshly...")
    try:
        nltk.download('punkt', quiet=False)
        print("Download complete.")
        
        # Verify
        print("Verifying load...")
        nltk.data.find('tokenizers/punkt')
        print("Verification SUCCESS! 'punkt' is ready.")
        
    except Exception as e:
        print(f"Download or Verification FAILED: {e}")
        exit(1)

if __name__ == "__main__":
    fix_nltk()
