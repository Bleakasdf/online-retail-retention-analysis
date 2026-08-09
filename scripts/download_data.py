from pathlib import Path
from urllib.request import urlretrieve
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
URL = "https://cdn.uci-ics-mlr-prod.aws.uci.edu/502/online%2Bretail%2Bii.zip"


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    archive = RAW / "online_retail_ii.zip"
    urlretrieve(URL, archive)
    with ZipFile(archive) as source:
        source.extractall(RAW)
    print(RAW / "online_retail_II.xlsx")


if __name__ == "__main__":
    main()
