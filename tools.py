import dashscope.files
import streamlit as st
from streamlit_text_rating.st_text_rater import st_text_rater
from streamlit.components.v1 import html

from pptx import Presentation
from docx import Document
import io
import broadscope_bailian

import dashscope
from dashscope import Files
from dashscope import Assistants
from dashscope.assistants.files import Files as AssistantFiles
from dashscope import Threads
from dashscope import Messages
from dashscope import Runs
import oss2
from itertools import islice
import os
import json
import time


# Configure credentials
accessKeyId = st.secrets["ALIYUN_ACCESS_KEY"]
accessKeySecret = st.secrets["ALIYUN_ACCESS_Key_SECRET"]
agentKey = st.secrets["ALIYUN_AGENT_KEY"]
dashscope.api_key=st.secrets["DASHSCOPE_API_KEY"]
endpoint = 'oss-cn-beijing.aliyuncs.com'
bucket_name = 'eric-paide-kb'

# Retrieve the existing assistant
assistant_id = st.secrets["ALIYUN_APP_ID_AGENT"]
assistant = Assistants.retrieve(assistant_id)

#==== Start of Upload KB files to AssistantFile, only need to run once; If any updates, please re-run this code ====
# Get all files in local KB folder
local_folder_path = 'KB'  # Replace with the actual local folder path
file_list = os.listdir(local_folder_path)

# Upload files to AssistantFiles and get file IDs
file_ids = []
for file_name in file_list:
    local_file_path = os.path.join(local_folder_path, file_name)
    file_id = Files.upload(file_path=local_file_path, purpose='assistant', description='Assistant KB')['output']['uploaded_files'][0]['file_id']
    file_ids.append(file_id)

# Create AssistantFiles object based on the uploaded oss files
for file_id in file_ids:
    assistant_file = AssistantFiles.create(assistant_id, file_id=file_id)
    print("status code:", assistant_file.status_code, " - id:", assistant_file.id)
#==== End of uploading KB files ====

# List all the files in the assistant
assistant_files = AssistantFiles.list(assistant_id,
                                      sort_by="created_at",
                                      sort_order="desc")
print(len(assistant_files.data))
print(assistant_files.data)

# #==== Start of Delete all the files in the assistant
# for assistant_file in assistant_files.data:
#     assistant_file_deleted = AssistantFiles.delete(assistant_file.id, assistant_id=assistant_id)
#     print(assistant_file_deleted)
# #==== End of Delete all the files in the assistant

prompt = input("请输入问题: ")
thread = Threads.create(messages=[{"role": "user", "content": prompt}])
# Check if the thread was created successfully
if thread.status_code != 200:
    print('Create Thread failed, status code: %s, code: %s, message: %s' % (thread.status_code, thread.code, thread.message))
else:
    print('Create Thread success, id: %s' % thread.id)
    
    # Create a new message to start the conversation
    message = Messages.create(thread_id=thread.id, role="user", content=prompt)
    if message.status_code != 200:
        print('Create Message failed, status code: %s, code: %s, message: %s' % (message.status_code, message.code, message.message))
    else:
        print('Create Message success, id: %s' % message.id)

        # Create a new run to run message
        run = Runs.create(thread_id=thread.id, assistant_id=assistant_id)
        if run.status_code != 200:
            print('Create Run failed, status code: %s, code: %s, message: %s' % (run.status_code, run.status, run.message))
        else:
            print('Create Run success, id: %s' % run.id)
            # Wait for the run to complete or requires_action
            msgs = []
            while True:
                run = Runs.wait(run.id, thread_id=thread.id)
                if run.status_code != 200:
                    print('Wait for Run failed, status code: %s, code: %s' % (run.status_code, run.status))
                else:
                    if run.status == "completed":
                        msgs = Messages.list(thread_id=thread.id)
                        if msgs.status_code != 200:
                            print('Get run failed, status code: %s, code: %s, message: %s' % (msgs.status_code, run.status, msgs.message))
                        else:
                            print(json.dumps(msgs, default=lambda o: o.__dict__, sort_keys=True, indent=4))
                        break
                    if run.status == "failed" or run.status == "expired":
                        print('Run failed, status code: %s, code: %s' % (run.status_code, run.status))
                        print(run)
                        break
                    else:
                        time.sleep(1)
            
            # Get the thread messages, to get the run output
            new_text = ""
            if msgs:
                for msg in msgs.data:
                    for content in msg["content"]:
                        new_text = content["text"]["value"]
                        print(new_text)