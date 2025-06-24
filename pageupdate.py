import requests,sys, os
import pageupdate_conf as authentication
import xml.etree.ElementTree as etree

qbUserToken = authentication.USER_TOKEN
qbRealmHost = authentication.QB_REALM_HOST
qbBaseURL = authentication.QB_BASE_URL
qbApplicationDBID = authentication.QB_APPLICATION_DBID

pyFileId = None
pyFileName = None
# Count the number of passed in arguments
argument_count = len(sys.argv) - 1

if argument_count == 0:
    most_recent_file = max((file for file in os.listdir('.') if file.endswith(('.html','.js'))), key=os.path.getmtime)
    page = authentication.pages.get(most_recent_file)
    pyFileName = most_recent_file
    pyFileId = page
elif argument_count == 2:
    pyFileName = sys.argv[1]
    pyFileId = sys.argv[2]

if pyFileId == None or pyFileName == None:
    print("Invalid number of arguments")
    sys.exit()


class DatabaseClient:
    def __init__(self):
        self.qb_dbid = getattr(self, 'qb_dbid', None) 
        self.field_values = {}
        self.apptoken = qbUserToken
        self.realmhost = qbRealmHost
        self.base_url = qbBaseURL
        self.application_dbid = qbApplicationDBID
        self.session = requests.Session()

    def add_replace_db_pages(self):
        
        # Request URL Handler
        url = self.base_url + '/db/' + qbApplicationDBID

        # Generate Headers For Request
        headers = {
            'Content-Type': 'application/xml',
            'QUICKBASE-ACTION': 'API_AddReplaceDBPage',
        }

        # Specify The File Path And Get Contents
        file_path = f'./{pyFileName}'
        with open(file_path, 'r', encoding='utf-8') as file:
            contents = file.read()
        
        # Create A Request Dictionary
        request_dict = {
            'pageid': pyFileId,
            'usertoken': qbUserToken,
            'pagebody': contents,
        }

        # Convert to XML 
        xml_data = self._build_request(**request_dict)

        # Submit Request
        request = requests.post(url, xml_data, headers=headers)
        response = request.content

        # Get Request Response
        parsed = etree.fromstring(response)
        error_code = int(parsed.findtext('errcode'))
        if error_code == 0:
            print(f"Success! {pyFileName} Has Been Updated And Completed")
        else:
            print("Error Code", error_code)

    def _build_request(self, **kwargs):
        # Convert the dictionary to an XML string with CDATA around pagebody
        request_xml = "<?xml version='1.0' encoding='utf-8'?>\n<qdbapi>"
        for key, value in kwargs.items():
            if key == 'pagebody':
                request_xml += f"<{key}><![CDATA[{value}]]></{key}>"
            else:
                request_xml += f"<{key}>{value}</{key}>"
        request_xml += "</qdbapi>"
        return request_xml

# Example usage
client = DatabaseClient()
client.add_replace_db_pages()