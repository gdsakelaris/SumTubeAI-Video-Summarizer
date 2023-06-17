from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from .models import Video, Ticket

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

# ##
# openai.api_key_path = "/home/ubuntu/gptKey.txt"
# openai.api_key_path = "../Daniel_misc/TEMP_K.txt"
# tempStem = 'c:\sc\out'  # '/home/ubuntu/sc/out'#'c:\sc\out'
# tempWebm = 'c:\sc\out.webm'  # '/home/ubuntu/sc/out.webm'#'c:\sc\out.webm'#
# tempFlac = 'c:\sc\out.flac'  # '/home/ubuntu/sc/out.flac'#'c:\sc\out.flac'#
# ##
# Hardcoded transcribe_audio() for testing purposes
# def transcribe_audio(audio_file):
#     # For testing, hardcoded audio_file
#     audio_file = "/path/to/your/test_audio_file.flac"
# Step 2: Transcribe FLAC to TXT
# ##

# Functions


def transcribe_audio(audio_file):
    recognizer = sr.Recognizer()
    recognizer.energy_threshold = 300
    transcript = ''

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
                transcript += chunk_transcript + ' '
            except sr.UnknownValueError:
                print("Google Speech Recognition could not understand audio")
            except sr.RequestError as e:
                print(
                    f"\nCould not request results from Google Speech Recognition service; {e}\n")
    transcript = transcript[0].upper() + transcript[1:] + "."
    return transcript

# ##
# Hardcoded ydl() for testing purposes
# def ydl(youtube_url, fileStem):
#     # For testing, hardcoded youtube_url and fileStem
#     youtube_url = "https://www.youtube.com/watch?v=-ZsSWltYFGs"
#     fileStem = "test_video"
# ##


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
    transcript = transcribe_audio(tempFp + '.flac')
    print(f"\n TRANSCRIPT: {transcript} \n")

    # Return the YT data dictionary
    return {'dict': yt_dict, 'transcript': transcript}

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
def add_transcript(request):
    if request.method == 'POST':
        proceed = False
        # Get URL from POST
        inputUrl = request.POST.get('address')
        inputTokens = request.POST.get('input-tokens')
        print(inputTokens)
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
                'transcript': vid.transcript,
                'gptRaw': vid.gptRaw,
                'lang': vid.lang,
                'gptSummary': vid.gptSummary,
                'gptRec1': vid.gptRec1,
                'gptRec2': vid.gptRec2,
                # 'gptRec3': vid.gptRec3,
            }
            # Pass the context to the template
            return render(request, 'add_transcript.html', context)
        else:
            # URL does not exist
            transcript = 'null'

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
                transcript = dataAndTranscript['transcript']
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
                    "transcript": transcript
                }
                maxTokens = int(inputTokens)
                maxSentenceCount = 1
                print("Tokens Used: " + str(maxTokens))
                # Full Prompt in JSON syntax
                prompt_data = {
                    "response-task": f"You are to produce a TL;DR from a Youtube Transcript, stored in 'yt-metadata'. The TL;DR must be in {langString} and it is restricted to using {str(maxSentenceCount)} sentence(s) at maximum. Furthermore, you will also recommend 2 unique Youtube Channels related to this video. You will perform these tasks according to the following format and rules.",
                    "response-format": '{ "tldr": "<tldr-response>", "rec1": "<recommendation-response-1>", "rec2": "<recommendation-response-2>" }',
                    "response-rules": f"You will return your responses as a JSON object structured like 'response-format'. That is, it will be a parseable JSON object where the keys are 'tldr', 'rec1', and 'rec2' and the values for each are your responses. The values are forbidden from including double quotes since it must be parseable JSON. Again, ensure JSON syntax is followed so that I can parse your response as JSON, so each key and value must be bound by double quotes (per JSON syntax). Values must be bound by a set of double quotes, do not forget this. Parseable JSON is the most important aspect of your response.",
                    "tldr-rules": f"The value for 'tldr' should not contain any recommendation information, as that should only appear in the 'recX' values. The 'tldr' value should only contain the TL;DR sentence(s). The response is forbidden from containing double quotes. It can only use {str(maxSentenceCount)} sentence(s) at maximum.",
                    "recommendation-rules": f"The values for the 'rec1' and 'rec2' keys should each include a unique YouTube channel and a brief synopsis in {langString} of that recommended channel. The recommended channels should be two different channels. The format for this response can be <channel-name>: <channel-description>.",
                    "yt-metadata": video_data
                }

                # Convert prompt_data to JSON string
                prompt = json.dumps(prompt_data)

                try:
                    # Make Completion API call
                    response = openai.Completion.create(
                        model="text-davinci-003",
                        prompt=prompt,
                        max_tokens=maxTokens,
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
                gptRaw = response.choices[0].text
                print(gptRaw)
                print(inputLangCode)
                print(langString)
                # Parse the JSON
                gptSummary = 'JSON Parsing Failed'
                gptRec1 = 'JSON Parsing Failed'
                gptRec2 = 'JSON Parsing Failed'
                # gptRec3 = 'JSON Parsing Failed'
                try:
                    gptJson = json.loads(gptRaw)
                    gptSummary = gptJson['tldr']
                    gptRec1 = gptJson['rec1']
                    gptRec2 = gptJson['rec2']
                    # gptRec3 = gptJson['rec3']
                except JSONDecodeError as e:
                    print(e)

                # Save to DB
                Video.objects.create(
                    ytId=ytId,
                    url=inputUrl,
                    title=title,
                    description=description,
                    published_date=date,
                    transcript=transcript,
                    gptRaw=gptRaw,
                    lang=langString,
                    gptSummary=gptSummary,
                    gptRec1=gptRec1,
                    gptRec2=gptRec2,
                    # gptRec3=gptRec3,
                )
                vid = Video.objects.get(ytId=ytId, lang=langString)

                # Pass context to template
                context = {
                    'ytId': vid.ytId,
                    'inputUrl': vid.url,
                    'vidTitle': vid.title,
                    'date': vid.published_date,
                    'description': vid.description,
                    'transcript': vid.transcript,
                    'gptRaw': vid.gptRaw,
                    'lang': vid.lang,
                    'gptSummary': vid.gptSummary,
                    'gptRec1': vid.gptRec1,
                    'gptRec2': vid.gptRec2,
                    # 'gptRec3': vid.gptRec3,
                }
                return render(request, 'add_transcript.html', context)
            else:
                return render(request, 'add_transcript.html')
    else:
        # HTML Request was not 'POST'
        return render(request, 'add_transcript.html')


@login_required
def post_ticket(request):
    print("in get_contact")
    if request.method == 'POST':
        try:
            name = request.POST.get('name')
            surname = request.POST.get('surname')
            email = request.POST.get('email')
            message = request.POST.get('message')

            # Create the support ticket in the DB
            Ticket.objects.create(
                name=name,
                surname=surname,
                email=email,
                message=message
            )

            # Render a response
            return render(request, 'contact_response.html', {'name': name, 'surname': surname, 'email': email, 'message': message})
        except Exception as ex:
            return render(request, 'contact_response.html', {'name': f'error occured: {str(ex)}', 'surname': f'null', 'email': f'null', 'message': 'null'})
    else:
        return render(request, 'contact_response.html', {'name': 'error occured', 'surname': 'error occured', 'email': 'error occured', 'message': 'error occured'})


@login_required
def index(request):
    # get video objects
    # videos = Video.objects.all()
    # context = {'videos': videos}
    return render(request, 'index.html')


@login_required
def contact(request):
    return render(request, 'contact.html')
