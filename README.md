# sciscore-tools

A set of tools to extract text from various file formats, run it through SciScore, and extract the results.

## Setup

 * Install the requires packages with `pip install fasttext spacy numpy requests Unidecode`
 * `pdftotext` must also be installed from https://www.xpdfreader.com/download.html
 * Obtain the `methods-model.bin` file and place it in the same directory as `pdftools.py`
 * Obtain a `auth.json` file with your SciScore API credentials

## Text extraction

Currently, text can be extracted from `.doc`, `.docx`, `.xml`, and `.pdf` files. To extract from a PDF (and the process for other file formats is similar), first create a new object with `pdf = PDF('example.pdf')`. This will perform the conversion using `pdftotext` and attempt to remove boilerplate text like line numbers, copyright information, etc. To access this text, call `pdf.get_text(section)`. For our purposes, call `methods = pdf.get_text('methods')` to extract the methods section using a sentence classifier.

## Querying the SciScore API

