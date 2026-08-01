

\# Bash API documentation for https://bfb6e9a081ec2e01c1.gradio.live/

API Endpoints: 3



1\. Confirm that you have cURL installed on your system.



```bash

curl --version

```



2\. Find the API endpoint below corresponding to your desired function in the app. Copy the code snippet, replacing the placeholder values with your own input data.



Making a prediction and getting a result requires 2 requests: a POST and a GET request. The POST request returns an EVENT\_ID, which is used in the second GET request to fetch the results. In these snippets, we've used awk and read to parse the results, combining these two requests into one command for ease of use.



If your endpoint accepts files, you must first upload them via a POST to `/upload`, then reference the returned path with the meta key: `{"path": "...", "meta": {"\_type": "gradio.FileData"}}`. See \[curl docs](https://www.gradio.app/guides/querying-gradio-apps-with-curl).



\### API Name: /voice\_clone

Description: Generate speech by cloning a reference voice



```bash

FILE\_PATH=$(curl -s -X POST http://127.0.0.1:7860/gradio\_api/upload -F 'files=@/path/to/your/file' | tr -d '\[]" ')



curl -X POST http://127.0.0.1:7860/gradio\_api/call/v2/voice\_clone -s -H "Content-Type: application/json" \\

&#x20; -d '{"text": "Hello!!", "reference\_audio": {"path": "'$FILE\_PATH'", "meta": {"\_type": "gradio.FileData"}}, "ref\_transcript": "Hello!!", "use\_fast\_mode": true}' \\

&#x20; | awk -F'"' '{ print $4}' \\

&#x20; | read EVENT\_ID; curl -N http://127.0.0.1:7860/gradio\_api/call/voice\_clone/$EVENT\_ID

```



Accepts a JSON object with 4 keys:



text:

\- Type: str

\- Required

\- The input value that is provided in the Text to Synthesize Textbox component. 



reference\_audio:

\- Type: filepath

\- Required

\- The input value that is provided in the Reference Audio (3+ seconds) Audio component. The FileData class is a subclass of the GradioModel class that represents a file object within a Gradio interface. It is used to store file data and metadata when a file is uploaded.



Attributes:

&#x20;   path: The server file path where the file is stored.

&#x20;   url: The normalized server URL pointing to the file.

&#x20;   size: The size of the file in bytes.

&#x20;   orig\_name: The original filename before upload.

&#x20;   mime\_type: The MIME type of the file.

&#x20;   is\_stream: Indicates whether the file is a stream.

&#x20;   meta: Additional metadata used internally (should not be changed).



ref\_transcript:

\- Type: str

\- Required

\- The input value that is provided in the Transcript (Optional - improves quality) Textbox component. 



use\_fast\_mode:

\- Type: bool

\- Required

\- The input value that is provided in the Fast Mode (skip transcript) Checkbox component. 



Returns an array of 1 element:



\- Type: filepath

\- The output value that appears in the "Generated Speech" Audio component.







\### API Name: /custom\_voice

Description: Generate speech using preset voices



```bash

curl -X POST http://127.0.0.1:7860/gradio\_api/call/v2/custom\_voice -s -H "Content-Type: application/json" \\

&#x20; -d '{"text": "Hello!!", "voice\_name": "serena", "instruction": "Hello!!"}' \\

&#x20; | awk -F'"' '{ print $4}' \\

&#x20; | read EVENT\_ID; curl -N http://127.0.0.1:7860/gradio\_api/call/custom\_voice/$EVENT\_ID

```



Accepts a JSON object with 3 keys:



text:

\- Type: str

\- Required

\- The input value that is provided in the Text to Synthesize Textbox component. 



voice\_name:

\- Type: Literal\['serena', 'vivian', 'ono\_anna', 'sohee', 'aiden', 'dylan', 'eric', 'ryan', 'uncle\_fu']

\- Required

\- The input value that is provided in the Voice Character Dropdown component. 



instruction:

\- Type: str

\- Required

\- The input value that is provided in the Style Instruction (Optional) Textbox component. 



Returns an array of 1 element:



\- Type: filepath

\- The output value that appears in the "Generated Speech" Audio component.







\### API Name: /voice\_design

Description: Generate speech from text description



```bash

curl -X POST http://127.0.0.1:7860/gradio\_api/call/v2/voice\_design -s -H "Content-Type: application/json" \\

&#x20; -d '{"text": "Hello!!", "voice\_description": "Hello!!"}' \\

&#x20; | awk -F'"' '{ print $4}' \\

&#x20; | read EVENT\_ID; curl -N http://127.0.0.1:7860/gradio\_api/call/voice\_design/$EVENT\_ID

```



Accepts a JSON object with 2 keys:



text:

\- Type: str

\- Required

\- The input value that is provided in the Text to Synthesize Textbox component. 



voice\_description:

\- Type: str

\- Required

\- The input value that is provided in the Voice Description Textbox component. 



Returns an array of 1 element:



\- Type: filepath

\- The output value that appears in the "Generated Speech" Audio component.

