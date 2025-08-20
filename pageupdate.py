import requests,sys, os
import argparse
import json
import html
import xml.etree.ElementTree as etree

parser = argparse.ArgumentParser(description='Update or create QuickBase code pages')
parser.add_argument('--filename', help='File to upload')
parser.add_argument('--pageid', type=int, help='Page ID for updating existing page')
parser.add_argument('--env', help='Environment to use (overrides current_environment in config)')
parser.add_argument('--get', action='store_true', help='Download page from QuickBase instead of uploading')

args = parser.parse_args()

# Load configuration from JSON
with open('pageupdate_config.json', 'r', encoding='utf-8') as config_file:
    config = json.load(config_file)
    
# Use specified environment or fall back to current_environment
current_env = args.env if args.env else config["current_environment"]

if current_env not in config["environments"]:
    print(f"Error: Environment '{current_env}' not found in config")
    print(f"Available environments: {', '.join(config['environments'].keys())}")
    sys.exit()

env_config = config["environments"][current_env]

qbUserToken = env_config["USER_TOKEN"]
qbRealm = env_config["QB_REALM"] 
qbRealmHost = f"{qbRealm}.quickbase.com"
qbBaseURL = f"https://{qbRealm}.quickbase.com"
qbApplicationDBID = env_config["QB_APPLICATION_DBID"]
pages_config = env_config["pages"]

pyFileName = args.filename
pyFileId = args.pageid
isNewPage = False
isGetOperation = args.get

if not pyFileName:
    if isGetOperation and pyFileId:
        # Try to find filename by page ID in config first
        filename_from_config = None
        for filename, page_id in pages_config.items():
            if page_id == pyFileId:
                filename_from_config = filename
                break
        
        if filename_from_config:
            pyFileName = filename_from_config
        else:
            # Prompt user for filename
            pyFileName = input(f"Enter filename to save page {pyFileId}: ").strip()
            if not pyFileName:
                print("Error: No filename provided")
                sys.exit()
    else:
        pyFileName = max((file for file in os.listdir('.') if file.endswith(('.html','.js'))), key=os.path.getmtime)

if not pyFileId:
    pyFileId = pages_config.get(pyFileName)
    if not pyFileId:
        isNewPage = True

if not pyFileName:
    print("No file specified and no suitable files found")
    sys.exit()


class DatabaseClient:
    def add_replace_db_pages(self):
        
        # Request URL Handler
        url = qbBaseURL + '/db/' + qbApplicationDBID

        # Generate Headers For Request
        headers = {
            'Content-Type': 'application/xml',
            'QUICKBASE-ACTION': 'API_AddReplaceDBPage',
        }

        # Specify The File Path And Get Contents
        file_path = f'./{pyFileName}'
        with open(file_path, 'r', encoding='utf-8') as file:
            contents = file.read()
        
        # Create A Request Dictionary - different params for new vs existing pages
        if isNewPage:
            request_dict = {
                'pagename': pyFileName,
                'pagetype': '1',
                'usertoken': qbUserToken,
                'pagebody': contents,
            }
        else:
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
            if isNewPage:
                new_page_id = int(parsed.findtext('pageID'))
                print(f"Success! New page '{pyFileName}' created with ID: {new_page_id}")
                print(f"View page: https://{qbRealm}.quickbase.com/db/{qbApplicationDBID}?pageID={new_page_id}&a=dbpage")
                self._add_page_to_config(pyFileName, new_page_id)
            else:
                print(f"Success! {pyFileName} Has Been Updated And Completed")
                print(f"View page: https://{qbRealm}.quickbase.com/db/{qbApplicationDBID}?pageID={pyFileId}&a=dbpage")
        else:
            error_text = parsed.findtext('errtext', 'Unknown error')
            print(f"Error Code {error_code}: {error_text}")

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

    def _add_page_to_config(self, filename, page_id):
        config_file = 'pageupdate_config.json'
        
        with open(config_file, 'r+', encoding='utf-8') as file:
            config = json.load(file)
            
            # Add the new page to current environment
            current_env = config["current_environment"]
            config["environments"][current_env]["pages"][filename] = page_id
            
            # Write updated config back
            file.seek(0)
            json.dump(config, file, indent=2)
            file.truncate()
        
        print(f"Added '{filename}' : {page_id} to {config_file}")

    def get_db_page(self):
        if not pyFileId:
            print(f"Error: Page ID not found for '{pyFileName}' in config")
            return
        
        # Request URL Handler
        url = qbBaseURL + '/db/' + qbApplicationDBID
        
        # Generate Headers For Request
        headers = {
            'Content-Type': 'application/xml',
            'QUICKBASE-ACTION': 'API_GetDBPage',
        }
        
        # Create A Request Dictionary
        request_dict = {
            'pageid': pyFileId,
            'usertoken': qbUserToken,
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
            # Extract page content from pagebody element including BR tags
            pagebody_element = parsed.find('pagebody')
            if pagebody_element is not None:
                # Get the inner XML content of pagebody
                page_content = ''.join(pagebody_element.itertext())
                if not page_content:
                    # Fallback: get the raw XML content
                    page_content = etree.tostring(pagebody_element, encoding='unicode', method='xml')
                    # Remove the outer pagebody tags
                    page_content = page_content.replace('<pagebody>', '').replace('</pagebody>', '')
            else:
                page_content = ''
            
            # Remove BR tags first, then decode HTML entities, then trim
            page_content = page_content.replace('<BR/>', '\n').replace('<br/>', '\n')
            page_content = html.unescape(page_content)
            page_content = page_content.strip()
            
            # Write to file
            with open(pyFileName, 'w', encoding='utf-8') as file:
                file.write(page_content)
            
            print(f"Success! Downloaded '{pyFileName}' from QuickBase (Page ID: {pyFileId})")
            
            # Add to config if this page ID wasn't already mapped
            if pyFileName not in pages_config or pages_config[pyFileName] != pyFileId:
                self._add_page_to_config(pyFileName, pyFileId)
        else:
            error_text = parsed.findtext('errtext', 'Unknown error')
            print(f"Error Code {error_code}: {error_text}")

# Example usage
client = DatabaseClient()
if isGetOperation:
    client.get_db_page()
else:
    client.add_replace_db_pages()