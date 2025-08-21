import requests
from zipfile import ZipFile
import os
import json
import csv
import unidecode
import string
import xml.etree.cElementTree as ET
import subprocess
from tqdm import tqdm


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
        self.id_to_methods = {}
        self.id_to_pmcid = {}

    def _make_request(self, paper_id, text):
        try:
            r = requests.post(url=auth['url'],
                            data={'userId': self.user_id,
                                    'userType': self.user_type,
                                    'documentId': paper_id,
                                    'sectionContent': text,
                                    'apiKey': self.api_key,
                                    'jsonOutput': 'true'})
        except:
            r = None
        if r is None or r.status_code != 200:
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
            self.generate_report_from_text(pdftools.PDF(file, paper_id).get_text('methods'), paper_id)
        elif file.endswith('.docx') or file.endswith('.doc'):
            import docxtools
            self.generate_report_from_text(docxtools.Document(file).get_text('methods'), paper_id)
        elif file.endswith('.xml'):
            import jatstools
            self.generate_report_from_text(jatstools.XML(file).get_text('method'), paper_id)
        else:
            raise TypeError('invalid file type; please enter a .pdf, .xml, .docx, or .doc')

    def generate_report_from_pmid(self, pmid):
        try:
            r = requests.get(f'https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/', params={'tool': 'sciscore-tools', 'email': 'petereckmann@gmail.com', 'ids': pmid}).text
        except:
            return
        if '<version pmcid="' in r:
            pmcid = r.split('<version pmcid="')[1].split('"')[0].split('.')[0]
            self.id_to_pmcid[pmid] = pmcid
            return self.generate_report_from_pmcid(pmcid, id=pmid)
        else:
            self.id_to_pmcid[pmid] = 'no PMCID'
            return self.generate_report_from_text('no methods', pmid)

    def generate_report_from_pmcid(self, pmcid, id=None):
        if not id:
            id = pmcid
        import jatstools
        for line in open('oa_file_list.txt', 'r'):
            if pmcid in line:
                subprocess.check_call('rm -rf package/*', shell=True)
                url = 'https://ftp.ncbi.nlm.nih.gov/pub/pmc/' + line.split()[0]
                try:
                    subprocess.check_call(f'curl -o package/package.tar.gz {url}', shell=True, stderr=subprocess.DEVNULL)
                except:
                    return
                subprocess.check_call('cd package; gunzip -c package.tar.gz | tar xopf -', shell=True)
                try:
                    file = subprocess.check_output('find package/*/*.nxml', shell=True).decode('utf-8').strip()
                except:
                    print('no nxml found for', pmcid)
                    return
                
                #get rid of this
                #return jatstools.XML(file).get_text('method')
                self.generate_report_from_text(jatstools.XML(file).get_text('method'), id)

    def generate_report_from_text(self, methods, paper_id):
        folder_name = f"{self.folder}/{paper_id.replace('/', '_')}"
        self.id_to_methods[paper_id] = methods
        # return
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
        return sentence
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
        # self._add_data('PMID', report_json['docIdentifier'])
        # if report_json['docIdentifier'] not in self.id_to_pmcid:
        #     self.generate_report_from_pmid(report_json['docIdentifier'])
        try:
            self._add_data('PMCID', report_json['docIdentifier']) #self.id_to_pmcid[report_json['docIdentifier']])
        except:
            self._add_data('PMCID', 'no PMCID')
        try:
            if self.generate_report_from_pmcid(report_json['docIdentifier']).strip() == '':
                self._add_data('Methods section available?', 'No')
            else:
                self._add_data('Methods section available?', 'Yes')
            # self._add_data('Methods section available?', 'Yes' if (self.id_to_methods[report_json['docIdentifier']].strip() != '' and self.id_to_pmcid[report_json['docIdentifier']] != 'no PMCID') else 'No')
        except:
            self._add_data('Methods section available?', 'No')
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
        for id in tqdm(os.listdir(self.folder)):
            if id.endswith('.txt'):
                self.rows.append([None for _ in range(len(self.columns))])
                self._add_data('PMID', id.split('.')[0])
                self._add_data('PMCID', 'error')
                self._add_data('Methods section available?', 'No')
            else:
                self._add_row(json.loads(open(f'{self.folder}/{id}/report.json', 'r', encoding='utf-8').read()))  
        self._normalize_rows()
        for i, col in enumerate(self.columns):
            if i < 4:
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

        
        columns = ['PMCID', 
                    'Methods section available?',
                    'SciScore',
                    'Rigor: Ethics',
                    'Rigor: Ethics: IACUC',
                    'Rigor: Ethics: IRB',
                    'Rigor: Ethics: Euthanasia Agents',
                    'Rigor: Ethics: Field Sample Permit',
                    'Rigor: Ethics: Consent',
                    'Rigor: Randomization',
                    'Rigor: Blinding',
                    'Rigor: Power Analysis',
                    'Rigor: Replication',
                    'Rigor: Replication: Type',
                    'Rigor: Replication: Number',
                    'Rigor: Code Information',
                    'Rigor: Data Information',
                    'Rigor: Protocol Information',
                    'Rigor: Inclusion and Exclusion Criteria',
                    'Rigor: Attrition',
                    'Rigor: Cell Line Authentication',
                    'Rigor: Cell Line Authentication: Authentication',
                    'Rigor: Cell Line Authentication: Contamination',
                    'Rigor: Sex as a biological variable',
                    'Rigor: Subject Demographics: Age',
                    'Rigor: Subject Demographics: Weight',
                    'Resources: Antibodies count',
                    'Resources: Antibodies with RRID count',
                    'Resources: Antibodies with suggested RRID count',
                    'Resources: Antibodies first sentence',
                    'Resources: Experimental Models: Cell Lines count',
                    'Resources: Experimental Models: Cell Lines with RRID count',
                    'Resources: Experimental Models: Cell Lines with suggested RRID count',
                    'Resources: Experimental Models: Cell Lines first sentence',
                    'Resources: Recombinant DNA count',
                    'Resources: Recombinant DNA with RRID count',
                    'Resources: Recombinant DNA with suggested RRID count',
                    'Resources: Recombinant DNA first sentence',
                    'Resources: Experimental Models: Organisms/Strains count',
                    'Resources: Experimental Models: Organisms/Strains with RRID count',
                    'Resources: Experimental Models: Organisms/Strains with suggested RRID count',
                    'Resources: Experimental Models: Organisms/Strains first sentence',
                    'Resources: Software and Algorithms count',
                    'Resources: Software and Algorithms with RRID count',
                    'Resources: Software and Algorithms with suggested RRID count',
                    'Resources: Software and Algorithms first sentence',
                    'Misc: Oligonucleotides count',
                    'Misc: Oligonucleotides first sentence',
                    'Misc: Unresolved RRIDs count',
                    'Misc: Unresolved RRIDs first sentence',
                    'Misc: Statistical Tests count',
                    'Misc: Statistical Tests first sentence']
        writer.writerow(columns)
        fixed_rows = []
        for row in self.rows:
            fixed_row = []
            for col in columns:
                if col in self.columns:
                    fixed_row.append(str(row[self.columns.index(col)]).replace('not required.', 'not required').replace('not detected.', 'not detected'))
                else:
                    fixed_row.append('')
            fixed_rows.append(fixed_row)
        writer.writerows(fixed_rows)
