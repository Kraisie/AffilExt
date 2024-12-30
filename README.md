# AffilExt

AffilExt is a program to extract author affiliations from LaTeX source files. It can automatically download LaTeX files 
from arXiv or use pre-existing files.

## Setup
This code requires Python version `3.12`. To install the required packages, the following command can be used:
```sh
pip install -r requirements.txt
``` 
After installing all packages, the program can be run with 
```sh
cd src
python main.py
```

## Usage
```
usage: main.py [-h] [-c "CAT"] [-r N] [-s S] [-k PATH] [--clear-cache]
               [--clear-metadata]
               MODE

Downloads papers from an ArXiv category, downloads source files and extracts
authors and affiliations.

positional arguments:
  MODE                  Choose whether to download papers only, extract LaTeX
                        commands used for author and affiliation definitions,
                        or both. Default: 'all'.

options:
  -h, --help            show this help message and exit
  -c "CAT", --category "CAT"
                        The ArXiv category from which articles are downloaded.
                        Works for both API download and Kaggle import. Use
                        'all' to use all entries of the Kaggle dataset, no
                        matter the category. Default: 'cs.SE'.
  -r N, --max_results N
                        Maximum number of papers to download. Has to be
                        between 1 and 30_000 (inclusive). Default: 200.
  -s S, --chunk-size S  Number of paper metadata entries to request from the
                        API at once. Has to be between 10 and 1000
                        (inclusive). Default: 500.
  -k PATH, --kaggle PATH
                        The path to the Kaggle arXiv dataset file. This will
                        use the Kaggle file instead of the arXiv API.
  --clear-cache         Deletes all files related to arXiv (arXiv metadata,
                        latex files) and the ROR dataset. Also removes the
                        list of papers to skip downloading.
  --clear-metadata      Deletes all previously generated data before running.
```

### Samples
To download the articles of the category "Artificial Intelligence" we can use the following command:
```sh
python main.py download -c "cs.AI" -r 30000
```
Some categories have more than 30,000 papers. We can use the 
[Kaggle arXiv Dataset](https://www.kaggle.com/datasets/Cornell-University/arxiv)
to bypass the API limitations:
```sh
python main.py download -c "cs" -k /path/to/kaggle_dataset
```
To download and extract data from the papers, we can use:
```sh
python main.py all -c "cs" -k /path/to/kaggle_dataset
```
If we already downloaded or otherwise acquired `tex`-files for extraction, we can use the following command
to only run the extraction steps:
```sh
python main.py extract
```

## Generated Data
The program creates a `data` folder for all its data. The files for a specific paper are in a folder 
named by the arXiv ID of that paper. That folder contains the downloaded LaTeX files and the generated data.
The generated data is in the `JSON` format and split into files based on the content.

### File sizes
On average, the `.tex` files of 10,000 papers require 740 MB of disk space. We generate 220 MB of data for 10,000 
papers. ArXiv contains over 2.6 Million papers. Based on those numbers, we can estimate a required disk space of 250 GB
(190 GB for the `.tex` files and 60 GB of generated data). Keep in mind that this is just an estimate and does not 
include cached API responses, the ROR dataset and other generated statistics. Downloading the complete corpus from the
S3 Bucket requires at least 2.7 TB of disk space due to other files provided by the authors, like figures and PDF files.

## Known Issues
When running the program in a terminal, a Keyboard Interupt (Ctrl+C) does not end the program when it is currently
running multithreaded code. Stopping the execution in an IDE works fine.

## Scripts
There are some scripts in `src/scripts`. These are meant to help explore the data. These are not meant to be used in 
the rest of the code and might or might not work. We are keeping these scripts in there so you can use them to 
familiarize yourself with the generated data. `export_stats.py` was used to generate graphs for a thesis. The language 
used in those graphs is German, and they most likely are of no benefit outside that work. However, we want to 
highlight the generation of a force-directed graph in that script to display some of the extracted data in an easily 
understandable and interactive way. As we do not include the used JavaScript libraries locally, you will need to allow 
your browser to load JavaScript from the web, run a (local) web server, or use some editor/IDE like VS Code to run the 
web server for you.
