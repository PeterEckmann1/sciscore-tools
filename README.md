# sciscore-tools

A set of tools to extract text from various file formats, run it through SciScore, and extract the results.

## Setup

Should work on any Python 3 verison.

 * Install the requires packages with `pip install fasttext spacy numpy requests Unidecode`
 * `pdftotext` must also be installed from https://www.xpdfreader.com/download.html
 * Obtain the `methods-model.bin` file and place it in the same directory as `pdftools.py`
 * Obtain a `auth.json` file with your SciScore API credentials

## Text extraction and API querying

First create a SciScore object with 
```
import sciscore
api = sciscore.SciScore('report_folder')
```
where `report_folder` is the location to accumulate API responses. Then, call `api.generate_report_from_file('example.pdf', 'example_doi')` for each file you want the SciScore of, where `example.pdf` is a file of format `.pdf`, `.doc`, `.docx`, or `.xml`, and `example_doi` is the DOI or other identifier for the file, which will show up in a column of the final table.
<br>
When finished with running all your files, call `api.make_csv('out.csv')` to generate a csv with all the results together. Individual reports for each paper are also stored in `report_folder`.

sciscore-tools has utilities for retrieving `.xml` files given a PMID or PMCID from the PMC Open Access subset. First, download `oa_file_list.txt` from the [PMC FTP](https://ftp.ncbi.nlm.nih.gov/pub/pmc/). Then, you can call `api.generate_report_from_pmid('34825147')` for a PMID, or `api.generate_report_from_pmcid('PMC8605177')` for a PMCID. This will do all the processing internally, so you do not have to call `generate_report_from_file` again.