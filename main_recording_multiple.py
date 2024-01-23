import subprocess
from pymongo import MongoClient
import time
from dotenv import load_dotenv
import os
import certifi
from bson import ObjectId
import boto3
import requests
import time

ca = certifi.where()
from API_requests import send_post_request, get_diarisation_result, get_all_indicator_list, create_indicator_diarisation, save_diarisation_to_file, upload_file_to_s3
from analysis import gpt_response

# Load environment variables from .env file
load_dotenv()

def check_for_recording_url():
    DB_CONNECTION = os.environ.get('DB_URI')
    ca = certifi.where()

    try:
        client = MongoClient(DB_CONNECTION, tlsCAFile=ca)
        Meeting_automation = client['Meeting_automation']
        recording_link = Meeting_automation['recordingLink']

        #last_processed_id = None
        last_processed_id = get_last_document_id(recording_link)
        print(last_processed_id)

        while True:
            query = {}
            if last_processed_id is not None:
                query['_id'] = {'$gt': ObjectId(last_processed_id)}

            cursor = recording_link.find(query).sort([('_id', 1)])
            documents = list(cursor)

            for doc in documents:
                process_document(doc)  # Process each new document
                last_processed_id = doc['_id']

            time.sleep(3)  # adjust the sleep time as per your requirements
            print('Waiting for new entry..')
    except Exception as e:
        print(f"An error occurred: {e}")

def get_last_document_id(collection):
    last_document = collection.find().sort([('_id', -1)]).limit(1).next()
    return last_document['_id'] if last_document else None

def process_document(doc):
    id = doc["id"]
    rtype = doc["type"] 
    print(f"Received new submission with ID: {id}")
    # You can now use 'id' as needed
    time.sleep(1*60)
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

    upload_analysis = create_indicator_diarisation(str(id), rtype, diarisation, recording_analysis)
    print('upload_analysis',upload_analysis) 
        

if __name__ == "__main__":
    check_for_recording_url()
