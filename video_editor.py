import os
import cv2
import multiprocessing
import numpy as np
import PIL
from PIL import Image, ImageDraw, ImageFont
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.LANCZOS
from moviepy.editor import VideoFileClip, ImageClip, CompositeVideoClip, concatenate_videoclips, AudioFileClip, CompositeAudioClip, afx
import moviepy.video.fx.all as vfx
def create_phrase_image(phrase_words, highlight_index, video_width=1080, video_height=1920, highlight_color="yellow", font_path=None, font_size=90):
    img = Image.new('RGBA', (video_width, video_height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    
    def get_font(size):
        if font_path and os.path.exists(font_path):
            try: return ImageFont.truetype(font_path, size)
            except: pass
        for font_name in ["impact.ttf", "arialbd.ttf", "segoeuib.ttf", "malgun.ttf"]:
            try: return ImageFont.truetype(font_name, size)
            except: continue
        return ImageFont.load_default()
        
    font = get_font(font_size)
    
    def get_widths(f):
        sw = draw.textlength(" ", font=f) if hasattr(draw, 'textlength') else draw.textsize(" ", font=f)[0]
        wws = [draw.textlength(w, font=f) if hasattr(draw, 'textlength') else draw.textsize(w, font=f)[0] for w in phrase_words]
        tw = sum(wws) + sw * (len(phrase_words) - 1)
        return sw, wws, tw
        
    space_width, word_widths, total_width = get_widths(font)
    
    max_width = video_width - 80
    
    lines = []
    current_line = []
    current_w = 0
    
    for idx, (w, w_width) in enumerate(zip(phrase_words, word_widths)):
        if current_w + w_width > max_width and current_line:
            lines.append((current_line, current_w - space_width))
            current_line = [(idx, w, w_width)]
            current_w = w_width + space_width
        else:
            current_line.append((idx, w, w_width))
            current_w += w_width + space_width
    if current_line:
        lines.append((current_line, current_w - space_width))
        
    line_height = int(font_size * 1.3)
    total_height = len(lines) * line_height
    start_y = int(video_height * 0.6) - (total_height // 2) + (line_height // 2)
    
    stroke_width = 5
    stroke_width = 8
    stroke_color = "black"
    shadow_offset = 6
    
    for i, (line_words, line_width) in enumerate(lines):
        current_x = (video_width - line_width) / 2
        y = start_y + i * line_height
        for idx, w, w_width in line_words:
            fill_color = highlight_color if idx == highlight_index else "white"
            if hasattr(draw, 'textlength'):
                draw.text((current_x + shadow_offset, y + shadow_offset), w, font=font, fill="black", stroke_width=stroke_width, stroke_fill="black")
                draw.text((current_x, y), w, font=font, fill=fill_color, stroke_width=stroke_width, stroke_fill=stroke_color)
            else:
                for dx in [-stroke_width, stroke_width]:
                    for dy in [-stroke_width, stroke_width]:
                        draw.text((current_x + dx + shadow_offset, y + dy + shadow_offset), w, font=font, fill="black")
                        draw.text((current_x + dx, y + dy), w, font=font, fill=stroke_color)
                draw.text((current_x, y), w, font=font, fill=fill_color)
            current_x += w_width + space_width
            
    return np.array(img)
def get_face_tracking_x_centers(video, base_w):
    

    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    
    fps = 10
    duration = video.duration
    w, h = video.size
    times = np.arange(0, duration, 1.0 / fps)
    raw_x_centers = []
    
    last_x = w / 2
    for t in times:
        try:
            frame = video.get_frame(t)
            gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
            
            if len(faces) > 0:
                largest_face = max(faces, key=lambda rect: rect[2] * rect[3])
                x, y, fw, fh = largest_face
                x_center_abs = x + fw / 2
                x_center_abs = max(base_w / 2, min(w - base_w / 2, x_center_abs))
                last_x = x_center_abs
        except Exception:
            pass
        raw_x_centers.append(last_x)
            
    if len(raw_x_centers) > 0:
        deadzone_x = []
        current_target = raw_x_centers[0]
        for x in raw_x_centers:
            if abs(x - current_target) > w * 0.15: # 15% width deadzone
                current_target = x
            deadzone_x.append(current_target)
            
        window_size = min(30, len(deadzone_x))
        window = np.ones(window_size) / float(window_size)
        padded = np.pad(deadzone_x, (window_size//2, window_size-1-window_size//2), mode='edge')
        smoothed_x = np.convolve(padded, window, 'valid')
    else:
        smoothed_x = [w / 2] * len(times)
        
    def get_x_center(t):
        if t >= duration:
            t = duration - 0.001
        # Use Linear Interpolation to smoothly adjust 10fps data to 30fps/60fps.
        return np.interp(t, times, smoothed_x)
        
    return get_x_center
def generate_short(video_path, start_time, end_time, transcription_result, output_path="output_short.mp4", highlight_color="yellow", font_path=None, font_size=90, bgm_path=None):
    
    words = []
    zoom_segments = []
    valid_segments = []
    
    current_compressed_time = 0.0
    for segment in transcription_result.get('segments', []):
        if segment['start'] <= end_time and segment['end'] >= start_time:
            seg_s = max(start_time, segment['start'])
            seg_e = min(end_time, segment['end'])
            
            if seg_e - seg_s < 0.1: continue
            
            valid_segments.append({'start': seg_s, 'end': seg_e})
            
            zoom_segments.append({
                'start': current_compressed_time,
                'end': current_compressed_time + (seg_e - seg_s),
                'zoom': 1.08 if len(zoom_segments) % 2 == 1 else 1.0
            })
            
            if 'words' in segment:
                for w in segment['words']:
                    w_s = max(seg_s, w['start'])
                    w_e = min(seg_e, w['end'])
                    if w_s < w_e:
                        words.append({
                            'word': w['word'],
                            'start': current_compressed_time + (w_s - seg_s),
                            'end': current_compressed_time + (w_e - seg_s)
                        })
                        
            current_compressed_time += (seg_e - seg_s)
                    
    def get_zoom_factor(t):
        for seg in zoom_segments:
            if seg['start'] <= t <= seg['end']:
                return seg['zoom']
        return 1.0
                    
    raw_video = VideoFileClip(video_path)
    subclips = []
    for seg in valid_segments:
        subclips.append(raw_video.subclip(seg['start'], seg['end']))
        
    if not subclips:
        video = raw_video.subclip(start_time, end_time)
    else:
        video = concatenate_videoclips(subclips)
    
    w, h = video.size
    fg_ratio = 3 / 4  # Wider crop for the main video
    bg_ratio = 9 / 16
    
    
    if w / h > fg_ratio:
        fg_base_w = int(h * fg_ratio)
        fg_base_h = h
        get_x_center = get_face_tracking_x_centers(video, fg_base_w)
    else:
        fg_base_w = w
        fg_base_h = int(w / fg_ratio)
        def get_x_center(t): return w / 2
    def process_frame(get_frame, t):
        frame = get_frame(t)
        
        # 1. Background (9:16 blurred)
        bg_crop_w = int(h * bg_ratio) if (w/h > bg_ratio) else w
        bg_crop_h = h if (w/h > bg_ratio) else int(w / bg_ratio)
        bx1 = int((w - bg_crop_w) / 2)
        by1 = int((h - bg_crop_h) / 2)
        bg_cropped = frame[by1:by1+bg_crop_h, bx1:bx1+bg_crop_w]
        
        bg_resized = cv2.resize(bg_cropped, (1080, 1920), interpolation=cv2.INTER_LINEAR)
        bg_blurred = cv2.GaussianBlur(bg_resized, (99, 99), 0)
        bg_blurred = cv2.addWeighted(bg_blurred, 0.6, np.zeros_like(bg_blurred), 0.4, 0)
        
        # 2. Foreground (3:4 tracking crop)
        zf = get_zoom_factor(t)
        w_crop = int(fg_base_w / zf)
        h_crop = int(fg_base_h / zf)
        
        xc = get_x_center(t)
        x1 = max(0, min(w - w_crop, int(xc - w_crop / 2)))
        y1 = int(h / 2 - h_crop / 2)
            
        fg_cropped = frame[y1:y1+h_crop, x1:x1+w_crop]
        fg_h = int(1080 / (w_crop / h_crop))
        fg_resized = cv2.resize(fg_cropped, (1080, fg_h), interpolation=cv2.INTER_LINEAR)
        
        # 3. Composite
        final_frame = bg_blurred.copy()
        paste_y = max(0, min(1920 - fg_h, int((1920 - fg_h) / 2)))
        final_frame[paste_y:paste_y+fg_h, 0:1080] = fg_resized
        
        return final_frame
        
    video = video.fl(process_frame)
    
    subtitle_clips = []
    chunk_size = 4
    chunks = [words[i:i + chunk_size] for i in range(0, len(words), chunk_size)]
    
    for chunk in chunks:
        if not chunk: continue
        phrase_words = [w['word'].strip() for w in chunk]
        
        for idx, current_word in enumerate(chunk):
            w_start = current_word['start']
            w_end = current_word['end']
            duration = w_end - w_start
            if duration <= 0: duration = 0.1
                
            img_array = create_phrase_image(phrase_words, idx, 1080, 1920, highlight_color=highlight_color, font_path=font_path, font_size=font_size)
            txt_clip = ImageClip(img_array).set_start(w_start).set_duration(duration)
            
            if idx == 0:
                def bounce(t):
                    if t < 0.05: return 0.8 + (0.25 * (t / 0.05))
                    elif t < 0.15: return 1.05 - (0.05 * ((t - 0.05) / 0.10))
                    return 1.0
                txt_clip = txt_clip.resize(bounce)
                
            txt_clip = txt_clip.set_position('center')
            
            subtitle_clips.append(txt_clip)
            
    final_video = CompositeVideoClip([video] + subtitle_clips)
    
    if bgm_path and os.path.exists(bgm_path):
        try:
            bgm = AudioFileClip(bgm_path).fx(afx.volumex, 0.15)
            if bgm.duration < final_video.duration:
                bgm = afx.audio_loop(bgm, duration=final_video.duration)
            else:
                bgm = bgm.subclip(0, final_video.duration)
            
            # Fade out BGM at the end
            bgm = bgm.audio_fadeout(2.0)
                
            final_audio = CompositeAudioClip([final_video.audio, bgm])
            final_video = final_video.set_audio(final_audio)
        except Exception as e:
            print(f"Failed to apply BGM: {e}")
    
    # Create parent dir if not exists
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    

    # Try GPU encoding first, fallback to CPU
    try:
        final_video.write_videofile(
            output_path, 
            fps=30, 
            codec="h264_nvenc", 
            audio_codec="aac",
            bitrate="8000k",
            ffmpeg_params=["-pix_fmt", "yuv420p"],
            preset="fast",
            threads=multiprocessing.cpu_count(),
            logger=None
        )
    except Exception:
        # Fallback to fast CPU encoding if nvenc fails
        final_video.write_videofile(
            output_path, 
            fps=30, 
            codec="libx264", 
            audio_codec="aac",
            bitrate="8000k",
            ffmpeg_params=["-pix_fmt", "yuv420p"],
            preset="ultrafast",
            threads=multiprocessing.cpu_count(),
            logger=None
        )
    
    video.close()
    final_video.close()
