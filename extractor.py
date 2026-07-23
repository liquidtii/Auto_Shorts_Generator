import os
import json
import math
import re
import google.generativeai as genai
import openai
import PIL
from PIL import Image

if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.LANCZOS

from moviepy.editor import VideoFileClip, AudioFileClip
from rich.console import Console
from rich.progress import Progress, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn
from faster_whisper import WhisperModel

def extract_audio(video_path, audio_path="temp_audio.wav"):
    video = VideoFileClip(video_path)
    video.audio.write_audiofile(audio_path, logger=None)

def transcribe_audio(audio_path, model_size="base"):
    console = Console()
    
    clip = AudioFileClip(audio_path)
    total_duration = clip.duration
    clip.close()
    
    with console.status(f"[bold cyan]Preparing high-performance Whisper({model_size}) model...[/bold cyan]", spinner="dots"):
        model = WhisperModel(model_size, device="cuda", compute_type="float16")
        
    console.print(f"[bold cyan]Starting speech transcription. (Progress will be shown below)[/bold cyan]")
    
    segments, info = model.transcribe(audio_path, word_timestamps=True)
    transcription_result = {'segments': []}
    
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(),
        transient=True
    ) as progress:
        task = progress.add_task(f"[bold cyan]Transcribing speech to text...[/bold cyan]", total=math.ceil(total_duration))
        
        for segment in segments:
            if hasattr(segment, 'words') and segment.words:
                words_data = [{'word': w.word, 'start': w.start, 'end': w.end} for w in segment.words]
            else:
                words_list = segment.text.split()
                words_data = []
                if words_list:
                    word_dur = (segment.end - segment.start) / len(words_list)
                    for i, w in enumerate(words_list):
                        words_data.append({
                            'word': w,
                            'start': segment.start + i * word_dur,
                            'end': segment.start + (i + 1) * word_dur
                        })
                        
            seg_dict = {
                'start': segment.start,
                'end': segment.end,
                'text': segment.text,
                'words': words_data
            }
            transcription_result['segments'].append(seg_dict)
            progress.update(task, completed=min(math.ceil(segment.end), math.ceil(total_duration)))
            
    return transcription_result

def extract_hooks_llm(transcription_result, llm_provider="gemini", api_key=None, max_duration=60):
    segments = transcription_result.get('segments', [])
    if not segments:
        return [{"start": 0.0, "end": 10.0, "reason": "No speech detected"}]
        
    text_with_timestamps = ""
    for seg in segments:
        text_with_timestamps += f"[{seg['start']:.2f} - {seg['end']:.2f}] {seg['text']}\n"
        
    if not api_key:
        end_time = min(max_duration, segments[-1]['end'])
        return [{"start": 0.0, "end": end_time, "reason": "Default segment (no API key)"}]
        
    prompt = f"""
    You are an expert short-form video editor (TikTok/Reels/Shorts).
    Analyze the following video transcript and identify the most engaging, viral "hook" segment.
    The segment should be between 30 to {max_duration} seconds long.
    It should start with a strong hook and end at a natural conclusion.
    
    Transcript (format [start_time - end_time] text):
    {text_with_timestamps}
    
    Output JSON format only:
    [
      {{
        "start": start_time_in_seconds_as_float,
        "end": end_time_in_seconds_as_float,
        "reason": "Why this is a good hook"
      }}
    ]
    """
    
    try:
        if llm_provider == "gemini":
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.5-flash')
            response = model.generate_content(prompt)
            text = response.text
        elif llm_provider == "openai":
            client = openai.OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}]
            )
            text = response.choices[0].message.content
        else:
            print(f"Unsupported LLM provider: {llm_provider}")
            return [{"start": 0.0, "end": min(max_duration, segments[-1]['end']), "reason": "Unsupported LLM fallback"}]
        
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            json_str = match.group(0)
            data = json.loads(json_str)
            return data
        else:
            print("Failed to parse JSON from LLM response. Using default fallback.")
            return [{"start": 0.0, "end": min(max_duration, segments[-1]['end']), "reason": "LLM parse fallback"}]
    except Exception as e:
        print(f"Error calling LLM: {e}")
        return [{"start": 0.0, "end": min(max_duration, segments[-1]['end']), "reason": "LLM error fallback"}]
