import lxml.etree as ET
import subprocess


class XML:
    def __init__(self, file):
        self.file = ET.parse(file)

    def get_text(self, section):
        text = ''
        if section == 'all':
            return ' '.join(ET.tostring(self.file, encoding='utf-8', method='text').decode('utf-8').replace('\n', ' ').split())
        sections = self.file.xpath(f'.//sec[contains(@sec-type, "{section}")]')
        if sections:
            return ' '.join(ET.tostring(sections[0], encoding='utf-8', method='text').decode('utf-8').replace('\n', ' ').split())
        else:
            # for html only
            for header in self.file.xpath('.//h2'):
                print(ET.tostring(header, encoding='utf-8', method='text').decode('utf-8').lower())
                if section.replace('methods', 'method') in ET.tostring(header, encoding='utf-8', method='text').decode('utf-8').lower():
                    section_xml = ET.tostring(self.file).decode('utf-8').split(ET.tostring(header).decode('utf-8'))[1].split('<h2')[0]
                    while True:
                        try:
                            text += ' '.join(ET.tostring(ET.fromstring('<div>' + section_xml + '</div>'), encoding='utf-8', method='text').decode('utf-8').replace('\n', ' ').split()) + ' '
                        except:
                            section_xml = section_xml[:-1]
        if text.strip() == '':
            for sec in self.file.xpath('.//sec'):
                if len(sec.xpath('.//title')) > 0:
                    if section.replace('methods', 'method') in sec.xpath('.//title')[0].text.lower():
                        text += ' '.join(ET.tostring(sec, encoding='utf-8', method='text').decode('utf-8').replace('\n', ' ').split()) + ' '
        return text.strip()
    

def get_methods_from_pmcid(pmcid):
    files = open('oa_file_list.txt', 'r').readlines()
    for line in files:
        if pmcid in line:
            subprocess.check_call('rm -rf package/*', shell=True)
            url = 'https://ftp.ncbi.nlm.nih.gov/pub/pmc/' + line.split()[0]
            subprocess.check_call(f'curl -o package/package.tar.gz {url}', shell=True, stderr=subprocess.DEVNULL)
            subprocess.check_call('cd package; gunzip -c package.tar.gz | tar xopf -', shell=True)
            try:
                file = subprocess.check_output('find package/*/*.nxml', shell=True).decode('utf-8').strip()
            except:
                return
            return XML(file).get_text('method')
