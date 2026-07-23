import warnings
warnings.filterwarnings("ignore", category=SyntaxWarning, module="moviepy")

import os
import json
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel

from extractor import extract_audio, transcribe_audio, extract_hooks_llm
from video_editor import generate_short

console = Console()
SETTINGS_FILE = "settings.json"

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def run_setup(settings):
    clear_screen()
    console.print("\n[bold cyan]--- Settings Configuration ---[/bold cyan]")
    settings["llm_provider"] = Prompt.ask("Select LLM Provider", choices=["gemini", "openai"], default=settings.get("llm_provider", "gemini"))
    
    if settings["llm_provider"] == "gemini":
        settings["gemini_api_key"] = Prompt.ask("Gemini API Key", default=settings.get("gemini_api_key", ""))
    elif settings["llm_provider"] == "openai":
        settings["openai_api_key"] = Prompt.ask("OpenAI API Key", default=settings.get("openai_api_key", ""))
        
    settings["output_dir"] = Prompt.ask("Output Directory", default=settings.get("output_dir", "."))
    settings["model_size"] = Prompt.ask("Whisper Model Size", choices=["tiny", "base", "small", "medium", "large"], default=settings.get("model_size", "base"))
    settings["max_duration"] = int(Prompt.ask("Max Short Duration (seconds)", default=str(settings.get("max_duration", 60))))
    settings["highlight_color"] = Prompt.ask("Highlight Word Color", default=settings.get("highlight_color", "yellow"))
    settings["font_path"] = Prompt.ask("Custom Font Path (Press Enter if none)", default=settings.get("font_path", ""))
    settings["font_size"] = int(Prompt.ask("Subtitle Font Size", default=str(settings.get("font_size", 90))))
    settings["bgm_path"] = Prompt.ask("Background Music (BGM) Path (Press Enter if none)", default=settings.get("bgm_path", ""))
    
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=4)
        console.print("[green]Settings saved successfully![/green]")
    except Exception as e:
        console.print(f"[bold red]Failed to save settings: {e}[/bold red]")
        
    Prompt.ask("\n[bold]Press Enter to continue...[/bold]", default="")
    return settings

def main():
    # Store settings in memory so they persist across loops
    settings = {
        "llm_provider": "gemini",
        "gemini_api_key": os.environ.get("GEMINI_API_KEY", ""),
        "openai_api_key": os.environ.get("OPENAI_API_KEY", ""),
        "output_dir": ".",
        "model_size": "base",
        "max_duration": 60,
        "highlight_color": "yellow",
        "font_path": "",
        "font_size": 90,
        "bgm_path": ""
    }
    
    is_first_run = not os.path.exists(SETTINGS_FILE)
    
    if not is_first_run:
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                # migrate old api_key if exists
                if "api_key" in loaded and "gemini_api_key" not in loaded:
                    loaded["gemini_api_key"] = loaded.pop("api_key")
                settings.update(loaded)
        except Exception as e:
            console.print(f"[yellow]Error loading settings file: {e}[/yellow]")
            is_first_run = True

    # Check if essential keys are missing
    needs_setup = is_first_run
    if settings["llm_provider"] == "gemini" and not settings.get("gemini_api_key"):
        needs_setup = True
    elif settings["llm_provider"] == "openai" and not settings.get("openai_api_key"):
        needs_setup = True
        
    if needs_setup:
        console.print("[yellow]Initial setup is required. Please configure your settings.[/yellow]")
        settings = run_setup(settings)

    while True:
        clear_screen()
        console.print(Panel.fit("[bold blue]🎬 ASG(Auto Short Generator))[/bold blue]", border_style="blue"))
        console.print("\n[bold green]Main Menu[/bold green]")
        console.print("1. Process New Video (Generate Shorts)")
        console.print("2. Change Settings")
        console.print("3. Exit")
        
        choice = Prompt.ask("Please select an option", choices=["1", "2", "3"])
        
        if choice == "3":
            console.print("[yellow]Exiting program. Goodbye![/yellow]")
            break
            
        elif choice == "2":
            settings = run_setup(settings)
            
        elif choice == "1":
            video_path = Prompt.ask("\n[bold yellow]Enter the absolute/relative path of the video file to process[/bold yellow]")
            
            # Remove quotes if user dragged and dropped
            video_path = video_path.strip('"').strip("'")
            
            if not os.path.exists(video_path):
                console.print(f"[bold red]Error: File not found -> {video_path}[/bold red]")
                continue
                
            console.print(f"\n[bold magenta]Starting job:[/bold magenta] {video_path}")
            
            audio_path = "temp_audio.wav"
            
            try:
                # 1. Extract Audio
                with console.status("[bold cyan]Extracting audio...[/bold cyan]", spinner="dots"):
                    extract_audio(video_path, audio_path)
                console.print("[green]✓ Audio extraction complete[/green]")
                
                # 2. Transcribe
                # The progress bar is handled inside the transcribe_audio function.
                transcription = transcribe_audio(audio_path, model_size=settings.get("model_size", "base"))
                console.print("[green]✓ Transcription complete[/green]")
                
                # 3. Find Hooks
                with console.status(f"[bold cyan]{settings.get('llm_provider').capitalize()} AI is analyzing the most engaging hooks...[/bold cyan]", spinner="arc"):
                    hooks = extract_hooks_llm(
                        transcription, 
                        llm_provider=settings.get("llm_provider", "gemini"),
                        api_key=settings.get(f"{settings.get('llm_provider')}_api_key", ""), 
                        max_duration=settings.get("max_duration", 60)
                    )
                
                console.print(f"[bold green]✓ Found {len(hooks)} highlight segment(s)![/bold green]")
                
                # 4. Generate Shorts
                for i, hook in enumerate(hooks):
                    start = hook.get("start", 0)
                    end = hook.get("end", settings.get("max_duration", 60))
                    reason = hook.get("reason", "No reason provided")
                    
                    console.print(Panel(f"[bold]Short #{i+1}[/bold]\nSegment: {start}s ~ {end}s\nReason: {reason}", border_style="yellow"))
                    
                    base_out_name = os.path.join(settings.get("output_dir", "."), f"short_{i+1}")
                    out_name = f"{base_out_name}.mp4"
                    counter = 1
                    while os.path.exists(out_name):
                        out_name = f"{base_out_name}_{counter}.mp4"
                        counter += 1
                    
                    with console.status(f"[bold cyan]Editing Short #{i+1} and generating subtitles...[/bold cyan]", spinner="aesthetic"):
                        generate_short(
                            video_path, 
                            start, 
                            end, 
                            transcription, 
                            output_path=out_name,
                            highlight_color=settings.get("highlight_color", "yellow"),
                            font_path=settings.get("font_path") if settings.get("font_path") else None,
                            font_size=settings.get("font_size", 90),
                            bgm_path=settings.get("bgm_path") if settings.get("bgm_path") else None
                        )
                    console.print(f"[green]✓ Short #{i+1} saved: {out_name}[/green]")
                    
            except Exception as e:
                console.print(f"[bold red]An error occurred during processing: {e}[/bold red]")
            finally:
                if os.path.exists(audio_path):
                    os.remove(audio_path)
                    
            console.print("[bold green]\nAll tasks completed![/bold green]")
            Prompt.ask("\n[bold]Press Enter to return to the main menu...[/bold]", default="")

if __name__ == "__main__":
    main()
