from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Video  # , Ticket
import pycountry
import tempfile
import openai
import yt_dlp
import math
import json
import os
import re
from datetime import datetime
import speech_recognition as sr
from json import JSONDecodeError
###
openai.api_key_path = "/home/ubuntu/OA-API-K.txt"
###
tempStem = '/home/ubuntu/sc/out'
tempWebm = '/home/ubuntu/sc/out.webm'
tempFlac = '/home/ubuntu/sc/out.flac'
###
# Hardcoded transcribe_audio() for testing purposes
# def transcribe_audio(audio_file):
#     # For testing, hardcoded audio_file
#     audio_file = "/path/to/your/test_audio_file.flac"
# Step 2: Transcribe FLAC to TXT
###


# Functions

def transcribe_audio(audio_file):
    recognizer = sr.Recognizer()
    recognizer.energy_threshold = 300
    STtranscript = ''

    with sr.AudioFile(audio_file) as source:
        audio_duration = math.ceil(source.DURATION)
        num_chunks = 6  # Desired number of chunks

        chunk_size = math.ceil(audio_duration / num_chunks)
        overlap = 2  # Adjust the overlap duration as needed

        for i in range(num_chunks):
            start = i * (chunk_size - overlap)
            end = min((i + 1) * chunk_size, audio_duration)

            audio_data = recognizer.record(
                source, offset=start, duration=end - start)

            try:
                chunk_transcript = recognizer.recognize_google(audio_data)
                STtranscript += chunk_transcript + ' '
            except sr.UnknownValueError:
                print("Google Speech Recognition could not understand audio")
            except sr.RequestError as e:
                print(
                    f"\nCould not request results from Google Speech Recognition service; {e}\n")
    STtranscript = STtranscript[0].upper() + STtranscript[1:] + "."
    return STtranscript


def downloadAndTranscribe(youtube_url, fileStem):
    # Download the YouTube audio and data using yt-dlp
    tempFp = os.path.join(fileStem, 'out')
    try:
        with yt_dlp.YoutubeDL({'format': 'bestaudio/best', 'writesubtitles': True, 'extractaudio': True, 'outtmpl': f'{tempFp}.%(ext)s'}) as ydlp:
            yt_dict = ydlp.extract_info(youtube_url, download=False)
            # print(json.dumps(ydlp.sanitize_info(yt_dict)))
            ydlp.download([youtube_url])
    except Exception as ex:
        strEx = str(ex)
        print('\nYT-DLP FAILED WITH ERROR: \n' + strEx)
        return f'YT-DLP FAILED WITH ERROR: {strEx}'

    # Convert .webm to .flac using FFmpeg
    try:
        os.system(f"ffmpeg -y -i {tempFp}.webm -c:a flac {tempFp}.flac")
        print(f"\nFFMPEG PRODUCED {tempFp}.flac")
    except Exception as ex:
        strEx = str(ex)
        print('\nFFMPEG FAILED WITH ERROR: \n' + strEx)
        return f'FFMPEG FAILED WITH ERROR: {strEx}'

    # Transcribe the Youtube Audio
    STtranscript = transcribe_audio(tempFp + '.flac')
    print(f"\n STtranscript: {STtranscript} \n")

    # Return the YT data dictionary
    return {'dict': yt_dict, 'STtranscript': STtranscript}

# Regex the Youtube ID from a URL


def extract_video_id(url):
    # Regular expression pattern to match YouTube video IDs
    pattern = r"(?:(?:youtu\.be\/|v\/|vi\/|u\/\w\/|embed\/|shorts\/)|(?:(?:watch)?\?v(?:i)?=|\&v(?:i)?=))([^#\&\?]+)"

    # Find the video ID using the pattern
    match = re.search(pattern, url)

    if match:
        video_id = match.group(1)
        return video_id
    else:
        return None

# Views


@login_required
def get_results(request):
    if request.method == 'POST':
        proceed = False
        # Get URL from POST
        inputUrl = request.POST.get('address')
        # inputTokens = request.POST.get('input-tokens')
        # print(inputTokens)
        ytId = extract_video_id(inputUrl)
        if ytId is not None:
            print(f"\nTHIS IS ID {ytId}\n")
        else:
            # ID could not be Regexed
            print(f"\nERROR: INPUTTED URL WAS NOT A VALID URL, NO ID EXTRACTED\n")
            return render(request, 'error.html', {'error': f'Inputted URL was invalid. Could not recognize Youtube ID in URL: {inputUrl}'})

        # Get Language from POST
        inputLangCode = request.POST.get('language')
        langString = inputLangCode
        try:
            langString = pycountry.languages.get(alpha_2=inputLangCode).name
        except AttributeError as ex:
            print("PYCOUNTRY FAILED WITH ERROR: " + str(ex))
            return render(request, 'error.html', {'error': f'PYCOUNTRY failed with error: {str(ex)}'})

        # Check if the URL already exists in the database
        if Video.objects.filter(ytId=ytId, lang=langString).exists():
            # URL already exists, get the Video object
            vid = Video.objects.get(ytId=ytId, lang=langString)
            # Retrieve data from Video
            context = {
                'ytId': vid.ytId,
                'inputUrl': vid.url,
                'vidTitle': vid.title,
                'date': vid.published_date,
                'description': vid.description,
                'STtranscript': vid.STtranscript,
                'STRaw': vid.STRaw,
                'lang': vid.lang,
                'STSummary': vid.STSummary,
                'STRec1': vid.STRec1,
                'STRec2': vid.STRec2,
                # 'STRec3': vid.STRec3,
            }
            # Pass the context to the template
            return render(request, 'results.html', context)
        else:
            # URL does not exist
            STtranscript = 'null'

            # Hand 'tempDir' in a 'with' context manager
            with tempfile.TemporaryDirectory() as tempDir:
                try:
                    # Returns Metadata and Transcript
                    dataAndTranscript = downloadAndTranscribe(
                        inputUrl, tempDir)
                    if isinstance(dataAndTranscript, str):
                        return render(request, 'error.html', {'error': f'DOWNLOAD AND TRANSCRIBE FAILED WITH ERROR: {dataAndTranscript}'})
                    elif isinstance(dataAndTranscript, dict):
                        proceed = True
                except Exception as ex:
                    strEx = str(ex)
                    print("DOWNLOAD AND TRANSCRIBE FAILED WITH ERROR: " + strEx)
                    return render(request, 'error.html', {'error': f'DOWNLOAD AND TRANSCRIBE FAILED WITH ERROR: {strEx}'})

            # OPENAI API
            if proceed:
                # Take data
                STtranscript = dataAndTranscript['STtranscript']
                yt_data = dataAndTranscript['dict']
                title = yt_data.get('title', 'Title Not Found')
                dateObj = datetime.strptime(
                    yt_data.get('upload_date'), "%Y%m%d")
                date = dateObj.strftime('%Y-%m-%d')
                description = yt_data.get(
                    'description', 'Description Not Found')
                # language = yt_data.get('subtitles', {}).get('language')
                # subtitles = yt_data.get('subtitles', {})   # if user-loaded, can get .vtt
                # Youtube metadata for prompt
                video_data = {
                    "title": title,
                    "description": description,
                    "STtranscript": STtranscript
                }
                # maxTokens = int(inputTokens)
                # maxSentenceCount = 1
                # print("Tokens Used: " + str(maxTokens))
                # Full Prompt in JSON syntax
                prompt_data = {
                    "response-task": f"You are to generate a concise and informative summary (TL;DR) from a YouTube video's transcript, which is stored in the 'yt-metadata' field. The TL;DR summary should capture the main points and key information of the video. It should be written in clear and understandable English. Additionally, you need to recommend two unique YouTube channels related to the video. Follow the format and rules below to complete these tasks effectively.",
                    "response-format": '{{"tldr": "{tldr-response}", "rec1": "{recommendation-response-1}", "rec2": "{recommendation-response-2}"}}',
                    "response-rules": "Your response should be a JSON object structured like the 'response-format' provided. The keys should be 'tldr', 'rec1', and 'rec2', and the values should be your respective responses. The response values should be enclosed in double quotes and follow the JSON syntax. Remember, the parseable JSON format is crucial for successful evaluation.",
                    "tldr-rules": "The 'tldr' value should contain a concise summary of the video without any recommendation information. It should consist of three to five complete sentences. Avoid using double quotes in your response.",
                    "recommendation-rules": "The 'rec1' and 'rec2' values should each recommend a unique YouTube channel related to the video. Ensure that the recommended channels are different. Follow the format: <channel-name>.",
                    "yt-metadata": video_data
                }

                # Convert prompt_data to JSON string
                prompt = json.dumps(prompt_data)

                try:
                    # Make Completion API call
                    response = openai.Completion.create(
                        model="text-davinci-003",
                        prompt=prompt,
                        max_tokens=500,
                        temperature=0.7,
                        top_p=0.5,
                        # frequency_penalty=0.0,
                        # presence_penalty=1,
                    )
                except Exception as ex:
                    strEx = str(ex)
                    print("OPENAI FAILED WITH ERROR: " + strEx)
                    return render(request, 'error.html', {'error': f'OPENAI FAILED WITH ERROR: {strEx}'})

                # Get the response
                STRaw = response.choices[0].text
                print(STRaw)
                print(inputLangCode)
                print(langString)
                # Parse the JSON
                STSummary = 'JSON Parsing Failed'
                STRec1 = 'JSON Parsing Failed'
                STRec2 = 'JSON Parsing Failed'
                # STRec3 = 'JSON Parsing Failed'
                try:
                    STJson = json.loads(STRaw)
                    STSummary = STJson['tldr']
                    STRec1 = STJson['rec1']
                    STRec2 = STJson['rec2']
                    # STRec3 = STJson['rec3']
                except JSONDecodeError as e:
                    print(e)

                # Save to DB
                Video.objects.create(
                    ytId=ytId,
                    url=inputUrl,
                    title=title,
                    description=description,
                    published_date=date,
                    STtranscript=STtranscript,
                    STRaw=STRaw,
                    lang=langString,
                    STSummary=STSummary,
                    STRec1=STRec1,
                    STRec2=STRec2,
                    # STRec3=STRec3,
                )
                vid = Video.objects.get(ytId=ytId, lang=langString)

                # Pass context to template
                context = {
                    'ytId': vid.ytId,
                    'inputUrl': vid.url,
                    'vidTitle': vid.title,
                    'date': vid.published_date,
                    'description': vid.description,
                    'STtranscript': vid.STtranscript,
                    'STRaw': vid.STRaw,
                    'lang': vid.lang,
                    'STSummary': vid.STSummary,
                    'STRec1': vid.STRec1,
                    'STRec2': vid.STRec2,
                    # 'STRec3': vid.STRec3,
                }
                return render(request, 'results.html', context)
            else:
                return render(request, 'results.html')
    else:
        # HTML Request was not 'POST'
        return render(request, 'results.html')


@login_required
def index(request):
    # get video objects
    # videos = Video.objects.all()
    # context = {'videos': videos}
    return render(request, 'index.html')
