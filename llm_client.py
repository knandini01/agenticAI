import os
from google import genai
from google.genai import types
from PIL import Image
import json
import io

class LLMClient:
    def __init__(self):
        # Assumes GEMINI_API_KEY is in environment
        self.client = genai.Client()
        self.candidate_models = ['gemini-3.1-flash-lite', 'gemini-3.8-flash', 'gemini-3.7-flash', 'gemini-3.6-flash']
        self.model_name = self.candidate_models[0]

    def get_action(self, prompt: str, screenshot: Image.Image, previous_actions: list) -> dict:
        """Send the screenshot and prompt to Gemini and get tool calls."""
        
        tool_launch_app = types.FunctionDeclaration(
            name='launch_app',
            description='Fastest way to open any Windows program (e.g. "notepad", "calc", "chrome"). Automatically presses Win, types the app name, and hits Enter in 1 second.',
            parameters={
                'type': 'OBJECT',
                'properties': {
                    'app_name': {'type': 'STRING', 'description': 'The name of the application to open.'}
                },
                'required': ['app_name']
            }
        )
        tool_click = types.FunctionDeclaration(
            name='click',
            description='Move mouse to coordinates (x, y) and click.',
            parameters={
                'type': 'OBJECT',
                'properties': {
                    'x': {'type': 'INTEGER'},
                    'y': {'type': 'INTEGER'}
                },
                'required': ['x', 'y']
            }
        )
        tool_double_click = types.FunctionDeclaration(
            name='double_click',
            description='Move mouse to coordinates (x, y) and double click.',
            parameters={
                'type': 'OBJECT',
                'properties': {
                    'x': {'type': 'INTEGER'},
                    'y': {'type': 'INTEGER'}
                },
                'required': ['x', 'y']
            }
        )
        tool_type_text = types.FunctionDeclaration(
            name='type_text',
            description='Type the given text. Set press_enter=True if you want to press Enter immediately after typing.',
            parameters={
                'type': 'OBJECT',
                'properties': {
                    'text': {'type': 'STRING'},
                    'press_enter': {'type': 'BOOLEAN', 'description': 'Whether to press Enter after typing.'}
                },
                'required': ['text']
            }
        )
        tool_press_key = types.FunctionDeclaration(
            name='press_key',
            description='Press a keyboard key (e.g., enter, win, tab, escape, up, down).',
            parameters={
                'type': 'OBJECT',
                'properties': {
                    'key': {'type': 'STRING'}
                },
                'required': ['key']
            }
        )
        tool_hotkey = types.FunctionDeclaration(
            name='hotkey',
            description='Press keys combination together (e.g. ["win", "r"], ["ctrl", "a"]).',
            parameters={
                'type': 'OBJECT',
                'properties': {
                    'keys': {
                        'type': 'ARRAY',
                        'items': {'type': 'STRING'}
                    }
                },
                'required': ['keys']
            }
        )
        tool_wait = types.FunctionDeclaration(
            name='wait',
            description='Wait for a number of seconds for windows to open or animate.',
            parameters={
                'type': 'OBJECT',
                'properties': {
                    'seconds': {'type': 'NUMBER'}
                },
                'required': ['seconds']
            }
        )
        tool_check_app_opened = types.FunctionDeclaration(
            name='check_app_opened',
            description='Check whether an application is currently running by process name (e.g., "notepad", "calc", "calculator", "chrome").',
            parameters={
                'type': 'OBJECT',
                'properties': {
                    'app_name': {'type': 'STRING'}
                },
                'required': ['app_name']
            }
        )
        tool_open_url = types.FunctionDeclaration(
            name='open_url',
            description='Directly open a website or search URL in Chrome or default browser. Can open YouTube searches directly (e.g. "https://www.youtube.com/results?search_query=...").',
            parameters={
                'type': 'OBJECT',
                'properties': {
                    'url': {'type': 'STRING', 'description': 'Full URL to open.'},
                    'browser': {'type': 'STRING', 'description': 'Browser name, default is chrome.'}
                },
                'required': ['url']
            }
        )
        tool_focus_address_bar = types.FunctionDeclaration(
            name='focus_address_bar',
            description='Press Ctrl+L in browser to highlight the address bar before typing a new URL or search query.',
            parameters={'type': 'OBJECT', 'properties': {}}
        )
        tool_check_window_title_contains = types.FunctionDeclaration(
            name='check_window_title_contains',
            description='Check if any open window title matches a keyword (e.g. "YouTube", video title, "Chrome").',
            parameters={
                'type': 'OBJECT',
                'properties': {
                    'keyword': {'type': 'STRING'}
                },
                'required': ['keyword']
            }
        )
        tool_maximize_window = types.FunctionDeclaration(
            name='maximize_window',
            description='Maximizes the browser or active window (Win+Up) so screen coordinates are full screen.',
            parameters={'type': 'OBJECT', 'properties': {}}
        )
        tool_click_first_video = types.FunctionDeclaration(
            name='click_first_video',
            description='Smoothly moves cursor to the first YouTube video result and clicks it to begin playback.',
            parameters={'type': 'OBJECT', 'properties': {}}
        )
        tool_done = types.FunctionDeclaration(
            name='done',
            description='Call this when the main objective is completely achieved.',
            parameters={
                'type': 'OBJECT',
                'properties': {
                    'message': {'type': 'STRING'}
                },
                'required': ['message']
            }
        )

        tools = types.Tool(function_declarations=[
            tool_open_url, tool_click_first_video, tool_maximize_window, tool_focus_address_bar, tool_check_window_title_contains,
            tool_launch_app, tool_click, tool_double_click, tool_type_text, tool_press_key, tool_hotkey, tool_wait, tool_check_app_opened, tool_done
        ])
        
        system_instruction = (
            "You are an expert Windows and browser desktop automation agent.\n"
            "CRITICAL RULES:\n"
            "1. WEBSITES & MEDIA (YouTube, Google, etc.):\n"
            "   - When asked to open a website or search on YouTube (e.g., 'open youtube and search <song> and play it'):\n"
            "     ALWAYS use open_url(url='https://www.youtube.com/results?search_query=<encoded_query>') DIRECTLY! "
            "This opens Chrome and navigates directly to the exact search results in 1 step!\n"
            "   - If typing a URL into an already open browser, ALWAYS call focus_address_bar() first before typing!\n"
            "2. PLAYING VIDEOS:\n"
            "   - Once on the search results page, look at the screenshot and click the FIRST video title/thumbnail (usually around x: 450-550, y: 250-320).\n"
            "   - Wait 2 seconds for the video to begin playing.\n"
            "3. SELF-VERIFICATION IS STRICTLY MANDATORY:\n"
            "   - NEVER call 'done' until you have actually verified that the song or video is playing (by checking the video player on screen or calling check_window_title_contains)!\n"
            "   - If the video is not playing yet, click on the video result item or press spacebar to play.\n"
            "4. Execute actions cleanly and promptly."
        )

        # Format history
        history_text = "Previous actions taken:\n"
        for act in previous_actions:
            history_text += f"- {act}\n"
        if not previous_actions:
            history_text += "None.\n"

        user_content = f"Goal: {prompt}\n{history_text}\nWhat is the next action?"

        # High-speed compressed JPEG encoding
        buf = io.BytesIO()
        screenshot.save(buf, format='JPEG', quality=80)
        img_part = types.Part.from_bytes(data=buf.getvalue(), mime_type='image/jpeg')

        response = None
        last_error = None
        for model in self.candidate_models:
            try:
                response = self.client.models.generate_content(
                    model=model,
                    contents=[img_part, user_content],
                    config=types.GenerateContentConfig(
                        tools=[tools],
                        system_instruction=system_instruction,
                        temperature=0.0
                    )
                )
                self.model_name = model
                break
            except Exception as e:
                last_error = e
                continue

        if response is None:
            return {'type': 'error', 'message': f'All models failed. Last error: {last_error}'}

        if response.function_calls:
            actions = []
            for fc in response.function_calls:
                args = {k: v for k, v in fc.args.items()} if fc.args else {}
                actions.append({'name': fc.name, 'args': args})
            return {'type': 'actions', 'actions': actions}
        elif response.text:
            return {
                'type': 'message',
                'text': response.text
            }
        else:
            return {'type': 'error', 'message': 'No tool call or text returned.'}
