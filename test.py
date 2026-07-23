import os
import json
import re
from extractor import extract_hooks_llm
from video_editor import generate_short

def time_to_seconds(time_str):
    parts = time_str.split(':')
    if len(parts) == 3:
        h, m, s = parts
        return int(h) * 3600 + int(m) * 60 + float(s)
    elif len(parts) == 2:
        m, s = parts
        return int(m) * 60 + float(s)
    return float(time_str)

def parse_test_out(file_path):
    segments = []
    full_text = ""
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            match = re.match(r'\[([\d:\.]+) --> ([\d:\.]+)\](.*)', line)
            if match:
                start_str, end_str, text = match.groups()
                start = time_to_seconds(start_str)
                end = time_to_seconds(end_str)
                text = text.strip()
                full_text += text + " "
                
                words_list = []
                words = text.split()
                if words:
                    duration = end - start
                    word_dur = duration / len(words)
                    for i, w in enumerate(words):
                        words_list.append({
                            'word': w,
                            'start': start + i * word_dur,
                            'end': start + (i + 1) * word_dur
                        })
                        
                segments.append({
                    'start': start,
                    'end': end,
                    'text': text,
                    'words': words_list
                })
    return {'text': full_text.strip(), 'segments': segments}

def main():
    try:
        with open("settings.json", "r", encoding="utf-8") as f:
            settings = json.load(f)
    except FileNotFoundError:
        print("settings.json 파일이 없습니다. main.py를 한 번 실행해서 설정을 생성해주세요.")
        return
        
    api_key = settings.get("api_key")
    if not api_key:
        print("API 키가 없습니다. settings.json을 확인하세요.")
        return
        
    print("test_out.txt 파싱 중...")
    if not os.path.exists("test_out.txt"):
        print("test_out.txt 파일이 존재하지 않습니다.")
        return
        
    transcription_result = parse_test_out("test_out.txt")
    
    print("d.mp4 영상 길이 확인 중...")
    from moviepy.editor import VideoFileClip
    try:
        clip = VideoFileClip("d.mp4")
        video_duration = clip.duration
        clip.close()
    except Exception as e:
        print("d.mp4 읽기 실패:", e)
        return
        
    # d.mp4 길이를 넘어가는 자막은 완전히 무시 (잘못된 하이라이트 추출 방지)
    valid_segments = []
    for seg in transcription_result['segments']:
        if seg['start'] < video_duration - 5: # 약간의 여유를 둠
            valid_segments.append(seg)
    transcription_result['segments'] = valid_segments
    transcription_result['text'] = "\n".join([seg['text'] for seg in valid_segments])
    
    print("Gemini API로 하이라이트(Hook) 구간 찾는 중...")
    hooks = extract_hooks_llm(transcription_result, api_key=api_key, max_duration=60)
    
    if not hooks:
        print("하이라이트를 찾지 못했습니다.")
        return
        
    best_hook = hooks[0]
    print(f"찾은 하이라이트: {best_hook['start']} ~ {best_hook['end']}")
    print(f"이유: {best_hook['reason']}")
    
    start_sec = float(best_hook['start'])
    end_sec = float(best_hook['end'])
    
    print("\n영상 렌더링 시작...")
    
    font_path = settings.get("font_path")
    if font_path == "": font_path = None
    bgm_path = settings.get("bgm_path")
    if bgm_path == "": bgm_path = None
    
    output_path = "test_short.mp4"
    counter = 1
    while os.path.exists(output_path):
        output_path = f"test_short_{counter}.mp4"
        counter += 1
        
    generate_short(
        video_path="d.mp4",
        start_time=start_sec,
        end_time=end_sec,
        transcription_result=transcription_result,
        output_path=output_path,
        highlight_color=settings.get("highlight_color", "yellow"),
        font_path=font_path,
        font_size=settings.get("font_size", 90),
        bgm_path=bgm_path
    )
    print(f"\n✓ 테스트 영상 렌더링 완료: {output_path}")

if __name__ == "__main__":
    main()