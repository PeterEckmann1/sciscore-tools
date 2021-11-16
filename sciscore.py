import requests
from zipfile import ZipFile
import os
import json
import csv
import unidecode
import string


auth = json.load(open('auth.json', 'r'))
SMALL_CHARSET = string.digits + string.ascii_letters + string.whitespace + '()*+-_=<>:&!.,?'
ORDER = list(reversed(['Rigor', 'Resources', 'Misc']))


class SciScore:
    def __init__(self, report_folder, fix_whitespace=True, user_id=auth['user-id'], user_type='institution', api_key=auth['api-key']):
        if not os.path.exists(report_folder):
            os.mkdir(report_folder)
        self.folder = report_folder
        self.fix_whitespace = fix_whitespace
        self.user_id = user_id
        self.user_type = user_type
        self.api_key = api_key
        self.columns = []
        self.rows = []

    def _make_request(self, paper_id, text):
        r = requests.post(url=auth['url'],
                          data={'userId': self.user_id,
                                'userType': self.user_type,
                                'documentId': paper_id,
                                'sectionContent': text,
                                'apiKey': self.api_key,
                                'jsonOutput': 'true'})
        if r.status_code != 200:
            if text == unidecode.unidecode(text):
                if text == ''.join([char for char in text if char in SMALL_CHARSET]):
                    raise Exception('sciscore error', r.status_code, r.text)
                else:
                    print('used small charset for', paper_id)
                    r, text = self._make_request(paper_id, ''.join([char for char in text if char in SMALL_CHARSET]))
            else:
                print('used unidecode for', paper_id)
                r, text = self._make_request(paper_id, unidecode.unidecode(text))
        return r, text

    def generate_report_from_file(self, file, paper_id):
        if paper_id.replace('/', '_') in os.listdir(self.folder):
            return
        if file.endswith('.pdf'):
            import pdftools
            self.generate_report_from_text(pdftools.PDF(file).get_text('methods'), paper_id)
        elif file.endswith('.docx') or file.endswith('.doc'):
            import docxtools
            self.generate_report_from_text(docxtools.Document(file).get_text('methods'), paper_id)
        elif file.endswith('.xml'):
            import jatstools
            self.generate_report_from_text(jatstools.XML(file).get_text('method'), paper_id)
        else:
            raise TypeError('invalid file type; please enter a .pdf, .xml, .docx, or .doc')

    def generate_report_from_text(self, methods, paper_id):
        folder_name = f"{self.folder}/{paper_id.replace('/', '_')}"
        if methods == '':
            methods = 'blank'
        methods = methods.replace('', '').replace('', '')
        r, methods = self._make_request(paper_id, methods)
        open(folder_name + '.zip', 'wb').write(r.content)
        ZipFile(folder_name + '.zip').extractall(folder_name)
        os.remove(folder_name + '.zip')
        for f_name in os.listdir(folder_name):
            if 'star_table' in f_name:
                os.remove(f'{folder_name}/{f_name}')
        if self.fix_whitespace:
            self._fix_whitespace(folder_name, methods)

    def _fix_whitespace(self, folder, text):
        whitespace_locs = []
        doc_no_whitespace = ''
        loc = 0
        for char in text:
            if char == ' ':
                whitespace_locs.append(loc)
            else:
                doc_no_whitespace += char
                loc += 1
        with open(folder + '/report.json', 'r', encoding='utf-8') as f:
            report_json = json.loads(f.read())
            for section in report_json['sections']:
                for sentence in section['srList']:
                    sentence['sentence'] = self._fix_sent(sentence['sentence'], doc_no_whitespace, whitespace_locs)
            for section in report_json['rigor-table']['sections']:
                for sentence in section['srList']:
                    if sentence['sentence'] not in {'not detected.', 'not required.'}:
                        sentence['sentence'] = self._fix_sent(sentence['sentence'], doc_no_whitespace, whitespace_locs)
        with open(folder + '/report.json', 'w', encoding='utf-8') as f:
            f.write(json.dumps(report_json))

    def _fix_sent(self, sentence, doc_no_whitespace, whitespace_locs):
        sentence_no_whitespace = sentence.replace(' ', '')
        sent_loc = doc_no_whitespace.find(sentence_no_whitespace)
        if sent_loc == -1:
            raise Exception('sentence not found')
        fixed_sent = ''
        for j, i in enumerate(range(sent_loc, sent_loc + len(sentence_no_whitespace))):
            if i in whitespace_locs:
                fixed_sent += ' '
            fixed_sent += sentence_no_whitespace[j]
        return fixed_sent.strip()

    def _add_data(self, column, data):
        if column not in self.columns:
            self.columns.append(column)
            self.rows[-1].append('')
        self.rows[-1][self.columns.index(column)] = data

    def _add_row(self, report_json):
        self.rows.append([None for _ in range(len(self.columns))])
        self._add_data('ID', report_json['docIdentifier'])
        self._add_data('SciScore', report_json['sciscore'])
        for section in report_json['rigor-table']['sections']:
            for sentence in section['srList']:
                if 'title' in sentence:
                    self._add_data(f"Rigor: {section['title']}: {sentence['title']}", sentence['sentence'])
                else:
                    self._add_data(f"Rigor: {section['title']}", sentence['sentence'])
        for section in report_json['rigor-table']['other-sections']:
            for sentence in section['srList']:
                self._add_data(f"Rigor: {section['sectionName']}", sentence['sentence'])
        for section in report_json['sections']:
            self._add_data(f"Resources: {section['sectionName']} count", sum([sum([1 for mention in sr['mentions']]) for sr in section['srList']]))
            self._add_data(f"Resources: {section['sectionName']} with RRID count", sum([sum([1 for mention in sr['mentions'] if mention['rrid']]) for sr in section['srList']]))
            self._add_data(f"Resources: {section['sectionName']} with suggested RRID count", sum([sum([1 for mention in sr['mentions'] if not mention['rrid'] and 'suggestedRrid' in mention]) for sr in section['srList']]))
            self._add_data(f"Resources: {section['sectionName']} first sentence", section['srList'][0]['sentence'])
        if 'misc-table' in report_json:
            for section in report_json['misc-table']['sections']:
                self._add_data(f"Misc: {section['sectionName']} count", sum([1 for sr in section['srList']]))
                self._add_data(f"Misc: {section['sectionName']} first sentence", section['srList'][0]['sentence'])

    def _swap_columns(self, column1, column2):
        for row in self.rows:
            row[column1], row[column2] = row[column2], row[column1]
        self.columns[column1], self.columns[column2] = self.columns[column2], self.columns[column1]

    def _normalize_rows(self):
        defaults = [None for _ in self.rows[-1]]
        for row in self.rows:
            for i, col in enumerate(row):
                if defaults[i] is None and col is not None:
                    if isinstance(col, str):
                        defaults[i] = ''
                    else:
                        defaults[i] = 0
        new_rows = []
        for i, row in enumerate(self.rows):
            row = row + [None for _ in range(len(self.rows[-1]) - len(row))]
            for i in range(len(row)):
                if row[i] is None:
                    row[i] = defaults[i]
            new_rows.append(row)
        self.rows = new_rows

    def make_csv(self, file):
        for id in os.listdir(self.folder):
            self._add_row(json.loads(open(f'{self.folder}/{id}/report.json', 'r', encoding='utf-8').read()))
        self._normalize_rows()
        for i, col in enumerate(self.columns):
            if i < 2:
                continue
            max_order = ORDER.index(col.split(':')[0])
            max_j = 0
            for j in range(i, len(self.columns)):
                order = ORDER.index(self.columns[j].split(':')[0])
                if order > max_order:
                    max_order = order
                    max_j = j
            if max_order > ORDER.index(col.split(':')[0]):
                self._swap_columns(i, max_j)
        for i, col in enumerate(self.columns):
            for j in range(i + 1, len(self.columns)):
                if self.columns[j].count(':') > 1 and col.startswith('Rigor') and self.columns[j].startswith((':'.join(col.split(':')[:2]))):
                    self._swap_columns(i + 1, j)
                    break
        writer = csv.writer(open(file, 'w', encoding='utf-8', newline=''), quoting=csv.QUOTE_ALL)
        writer.writerow(self.columns)
        writer.writerows(self.rows)