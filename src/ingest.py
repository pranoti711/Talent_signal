"""Download raw datasets for Talent Signal and copy them into data/raw/."""
import shutil
from pathlib import Path

import kagglehub
from dotenv import load_dotenv

load_dotenv()  # loads KAGGLE_USERNAME / KAGGLE_KEY if present in .env

RAW_DIR = Path("data/raw")

# Kaggle handle = "<owner>/<dataset-slug>" (taken from the dataset URL)
DATASETS = {
    "linkedin_postings": "arshkon/linkedin-job-postings",
    # Optional validation source: verify the slug on its Kaggle page first
    # "ds_skills": "asaniczka/data-science-job-postings-and-skills",
}


def download(name: str, handle: str) -> Path:
    print(f"Downloading {handle} ...")
    cache_path = Path(kagglehub.dataset_download(handle))
    target = RAW_DIR / name
    target.mkdir(parents=True, exist_ok=True)

    # Copy files from kagglehub's cache into our project folder
    for item in cache_path.rglob("*"):
        if item.is_file():
            dest = target / item.relative_to(cache_path)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, dest)
    print(f"  saved to {target}")
    return target


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for name, handle in DATASETS.items():
        download(name, handle)


if __name__ == "__main__":
    main()