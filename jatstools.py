import lxml.etree as ET


class XML:
    def __init__(self, file):
        self.file = ET.parse(file)

    def get_text(self, section):
        sections = self.file.xpath(f'.//sec[contains(@sec-type, "{section}")]')
        if sections:
            return ' '.join(ET.tostring(sections[0], encoding='utf-8', method='text').decode('utf-8').replace('\n', ' ').split())
        else:
            # scuffed jats aka html
            for header in self.file.xpath('.//h2'):
                if section.replace('methods', 'method') in ET.tostring(header, encoding='utf-8', method='text').decode('utf-8').lower():
                    section_xml = ET.tostring(self.file).decode('utf-8').split(ET.tostring(header).decode('utf-8'))[1].split('<h2')[0]
                    while True:
                        try:
                            return ' '.join(ET.tostring(ET.fromstring('<div>' + section_xml + '</div>'), encoding='utf-8', method='text').decode('utf-8').replace('\n', ' ').split())
                        except:
                            section_xml = section_xml[:-1]
        return ''