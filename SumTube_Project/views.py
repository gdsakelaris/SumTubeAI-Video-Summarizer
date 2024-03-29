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
from .models import Video, Ticket
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from json import JSONDecodeError
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled


openai.api_key_path = "/home/ubuntu/OpenAPI_Key.txt"
tempStem = '/home/ubuntu/sc/out'
tempWebm = '/home/ubuntu/sc/out.webm'
tempFlac = '/home/ubuntu/sc/out.flac'

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
    transcript = transcript[0].upper() + transcript[1:]+"."
    return transcript

def downloadAndTranscribe(youtube_url, fileStem):
    # Extract the YouTube ID from the URL
    ytId = extract_video_id(youtube_url)

    # Define tempFp here
    tempFp = os.path.join(fileStem, 'out')

    try:
        # Attempt to fetch the transcript
        transcript_list = YouTubeTranscriptApi.list_transcripts(ytId)
        transcript = transcript_list.find_transcript(['en']).fetch()
        full_transcript = ' '.join([t['text'] for t in transcript])
        return {'dict': {}, 'transcript': full_transcript}
    except TranscriptsDisabled:
        # If transcripts are disabled for the video, fall back to voice recognition
        try:
            with yt_dlp.YoutubeDL({'format': 'bestaudio/best', 'writesubtitles': True, 'extractaudio': True, 'outtmpl': f'{tempFp}.%(ext)s'}) as ydlp:
                yt_dict = ydlp.extract_info(youtube_url, download=False)
                ydlp.download([youtube_url])
        except Exception as ex:
            strEx = str(ex)
            print('\nYT-DLP FAILED WITH ERROR: \n' + strEx)
            return f'YT-DLP FAILED WITH ERROR: {strEx}'

        try:
            os.system(f"ffmpeg -y -i {tempFp}.webm -c:a flac {tempFp}.flac")
            print(f"\nFFMPEG PRODUCED {tempFp}.flac")
        except Exception as ex:
            strEx = str(ex)
            print('\nFFMPEG FAILED WITH ERROR: \n' + strEx)
            return f'FFMPEG FAILED WITH ERROR: {strEx}'

        transcript = transcribe_audio(tempFp + '.flac')
        print(f"\n TRANSCRIPT: {transcript} \n")
        return {'dict': yt_dict, 'transcript': transcript}

    except Exception as e:
        print(f'Error occurred: {e}')
        return f'Error occurred: {e}'


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


# VIEWS 
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
            return render(request, 'error.html', { 'error': f'Inputted URL was invalid. Could not recognize Youtube ID in URL: {inputUrl}' })
        
        
        # Check if the URL already exists in the database
        if Video.objects.filter(ytId=ytId).exists():
            # URL already exists, get the Video object
            vid = Video.objects.get(ytId=ytId)
            # Retrieve data from Video
            context = {
                        'ytId': vid.ytId,
                        'inputUrl': vid.url,
                        'vidTitle': vid.title,
                        'date': vid.published_date,
                        'description': vid.description,
                        'transcript': vid.transcript,
                        'gptRaw': vid.gptRaw,                       
                        'gptSummary': vid.gptSummary,                      
                      }

            # Pass the context to the template
            return render(request, 'results.html', context)
        else:
            # URL does not exist
            transcript = 'null'
            
            # Hand 'tempDir' in a 'with' context manager
            with tempfile.TemporaryDirectory() as tempDir:
                try:
                    # Returns Metadata and Transcript
                    dataAndTranscript = downloadAndTranscribe(inputUrl, tempDir)
                    if isinstance(dataAndTranscript, str):
                        return render(request, 'error.html', { 'error': f'DOWNLOAD AND TRANSCRIBE FAILED WITH ERROR: {dataAndTranscript}' })
                    elif isinstance(dataAndTranscript, dict):
                        proceed = True
                except Exception as ex:
                    strEx = str(ex)
                    print("DOWNLOAD AND TRANSCRIBE FAILED WITH ERROR: " + strEx)
                    return render(request, 'error.html', { 'error': f'DOWNLOAD AND TRANSCRIBE FAILED WITH ERROR: {strEx}' })

        # OPENAI API:
            if proceed:
                # Take data
                transcript = dataAndTranscript['transcript']
                yt_data = dataAndTranscript['dict']
                title = yt_data.get('title', 'Title Not Found')

                # Check if 'upload_date' exists and is not None
                upload_date = yt_data.get('upload_date')
                if upload_date:
                    dateObj = datetime.strptime(upload_date, "%Y%m%d")
                    date = dateObj.strftime('%Y-%m-%d')
                else:
                    date = "2000-09-12"  # Default value for unknown date

                description = yt_data.get('description', 'Description Not Found')            

                # Youtube metadata for prompt
                video_data = {
                    "title": title,
                    "description": description,
                    "transcript": transcript
                }

                maxSentenceCount = 10
                # print("Tokens Used: " + str(maxTokens))

                # Full Prompt in JSON syntax
                prompt_data = {
                    "response-task": f"You are to produce a thorough and concise summary of a Youtube video transcript, stored in 'yt-metadata'. You will perform these tasks according to the following format and rules. For this entire request (meaning the combination of the prompt tokens used and the completion tokens), you may use no more than 4096 tokens.",
                    "response-format": '{ "tldr": "<tldr-response>"}',
                    "response-rules": f"You will return your responses as a JSON object structured like 'response-format'. That is, it will be a parseable JSON object where the key is 'tldr'. The value is forbidden from including double quotes since it must be parseable JSON. Again, ensure JSON syntax is followed so that I can parse your response as JSON, so each key and value must be bound by double quotes (per JSON syntax). Value must be bound by a set of double quotes, do not forget this. Parseable JSON is the most important aspect of your response.",
            
                    "tldr-rules": f"The 'tldr' value should only contain highly specific TL;DR sentence(s). The response is forbidden from containing double quotes. The response must thoroughly summarize the video's transcript.",
                    
                    "yt-metadata": video_data
                }
                
                prompt = json.dumps(prompt_data)

                # Calculate the approximate token count for the prompt (assuming 1 word = 1 token)
                prompt_token_count = len(prompt.split())

                # Set the max tokens for completion based on the estimated prompt token count
                max_allowed_tokens = 4096
                max_completion_tokens = max_allowed_tokens - prompt_token_count - 300

                try:
                    # Make Completion API call
                    response = openai.Completion.create(
                        model="gpt-3.5-turbo-instruct",
                        prompt=prompt,
                        max_tokens=max_completion_tokens,
                        temperature=0.7,
                        top_p=1,
                        # presence_penalty=1,
                    )
                except Exception as ex:
                    strEx = str(ex)
                    print("OPENAI FAILED WITH ERROR: " + strEx)
                    return render(request, 'error.html', { 'error': f'OPENAI FAILED WITH ERROR: {strEx}' })

                # Get the response
                gptRaw = response.choices[0].text
                print(gptRaw)
                gptSummary = ''

                try:
                    gptJson = json.loads(gptRaw)
                    gptSummary = gptJson['tldr']

                except JSONDecodeError as e:
                    print(e)
                
                # SAVE TO DATABASE
                Video.objects.create(
                    ytId=ytId,
                    url=inputUrl, 
                    title=title, 
                    description=description, 
                    published_date=date, 
                    transcript=transcript,
                    gptRaw=gptRaw, 
                    gptSummary=gptSummary, 
                )
                vid = Video.objects.get(ytId=ytId)

                # Pass the context to the template
                context = {
                    'ytId': vid.ytId,
                    'inputUrl': vid.url,
                    'vidTitle': vid.title,
                    'date': vid.published_date,
                    'description': vid.description,
                    'transcript': vid.transcript,
                    'gptRaw': vid.gptRaw,
                    'gptSummary': vid.gptSummary,
                }
                
                return render(request, 'results.html', context)
            else:
                return render(request, 'results.html')
    else:
        # HTML Request was not 'POST'
        return render(request, 'results.html')

@login_required
def post_ticket(request):
    print("in get_contact")
    if request.method == 'POST':
        try:
            name = request.POST.get('name')
            surname = request.POST.get('surname')
            email = request.POST.get('email')
            message = request.POST.get('message')

            # Create the Support Ticket in the Database
            Ticket.objects.create(name=name, surname=surname, email=email, message=message)
            
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