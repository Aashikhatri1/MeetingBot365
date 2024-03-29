      
import subprocess
from pymongo import MongoClient
import time
from dotenv import load_dotenv
import os
import certifi
from bson import ObjectId

from getCables import ServerHandler  
from zoombot import create_browser_instance, join_meeting, check_end_of_meeting  
from meetbot import join_google_meeting 
import boto3
ca = certifi.where()
from API_requests import send_post_request, get_diarisation_result, get_all_indicator_list, create_indicator_diarisation, save_diarisation_to_file, upload_file_to_s3
from analysis import gpt_response
# Load environment variables from .env file
load_dotenv()

def check_new_submissions():
    DB_CONNECTION = os.environ.get('DB_URI')
    try:
        client = MongoClient(DB_CONNECTION,tlsCAFile=ca)
        Meeting_automation = client['Meeting_automation']
        Zoom_meeting_link = Meeting_automation['meeting_link']

        last_count = Zoom_meeting_link.count_documents({})
        print(f'Initial count: {last_count}')  # print initial count

        while True:
            current_count = Zoom_meeting_link.count_documents({})
            print(f'Current count: {current_count}')  # print current count

            if current_count > last_count:
                # fetch the latest document
                cursor = Zoom_meeting_link.find().sort([('_id', -1)]).limit(1)
                for doc in cursor:
                    try:
                        print(f'Document status: {doc["status"]}')  # Print the status regardless of its value

                        # check if status is 'submitted'
                        if doc['status'] == 'submitted':
                            print(f'New document submitted: {doc}')
                            link = doc['link']  # assuming 'link' is the field name for the meeting link
                            print(f'Link: {link}')
                            id = doc['id']
                            #id = doc['_id']

                            # Get the first available cable
                            #available_cable_name = ServerHandler.get_available_cable_name()
                            #available_cable = ServerHandler.get_available_cable(available_cable_name, link)
                            available_cable_name = 'Line 1 (Virtual Audio Cable)'
                            available_cable = 'Line 1 (Virtual Audio Cable)'
                            print(f'First available cable: {available_cable}')
                            

                            # Change the status of the document to 'processing'
                            result = Zoom_meeting_link.update_one({'_id': doc['_id']}, {"$set": {"status": "processing"}})

                            # Print a success message if the update was successful
                            if result.modified_count > 0:
                                print('Document status updated successfully.')
                                
                                # Run join_meeting with link as argument
                                
                                print('Joining the meeting...')
                                if 'zoom' in link:
                                    driver = create_browser_instance()
                                    join_meeting(driver, link, available_cable)
                                #elif 'teams' in link:
                                #    join_teams_meeting(driver, link, available_cable)
                                elif 'google' in link:
                                    join_google_meeting('driver', link, available_cable)  
                                else:
                                    print('Unknown meeting link type.')
                                    
                                # Run recorder.py
                                print('Running recorder.py...')
                                recorder_process = subprocess.run(['python', 'recorder.py', doc['id'], available_cable_name, link], capture_output=True) 
                                if recorder_process.returncode != 0:
                                    print('recorder.py failed with error:')
                                    print(recorder_process.stderr.decode())
                                if recorder_process.returncode == 0:
                                    print('recorder.py finished successfully.')
                                    file_path = 'recording.wav'
                                    response = send_post_request(file_path, id)
                                    print('response', response.text)   

                                    #time.sleep(5*60)
                                    time.sleep(2*60)
                                    diarisation = get_diarisation_result(id)
                                    print('diarisation', diarisation)

                                    #upload_diarisation = create_meeting_diarisation(str(id), diarisation)
                                    #print('upload_diarisation', upload_diarisation)
                                    
                                    saved_diarisation = save_diarisation_to_file(id)
                                    upload_to_s3 = upload_file_to_s3(id, object_name=None)
                                    print('upload_to_s3', upload_to_s3)

                                    indicators = get_all_indicator_list()
                                    print('indicators', indicators)

                                    recording_analysis = gpt_response(indicators, diarisation)
                                    print('recording_analysis', recording_analysis)
                                    
                                    rtype = 'meeting'
                                    upload_analysis = create_indicator_diarisation(str(id), rtype, diarisation, recording_analysis)
                                    print('upload_analysis',upload_analysis) 
                                   
                                else:
                                    print('recorder.py failed.')
                            else:
                                print('Failed to update document status.')
                    except Exception as e:
                        print(f'An error occurred while processing document: {e}')
                last_count = current_count
            # wait for a while before checking again
            time.sleep(3)  # adjust according to requirement
    except Exception as e:
        print(f'An error occurred: {e}')

if __name__ == "__main__":
    check_new_submissions()

