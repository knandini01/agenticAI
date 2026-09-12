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
        self.candidate_models = ['gemini-flash-latest', 'gemini-3.1-flash-lite', 'gemini-3.8-flash']
        self.model_name = self.candidate_models[0]

    def get_action(self, prompt: str, screenshot: Image.Image, previous_actions: list) -> dict:
        """Send the screenshot and prompt to Gemini and get a tool call."""
        
        # We define the tools schema manually for Google GenAI
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
        tool_open_browser = types.FunctionDeclaration(
            name='open_browser',
            description='Opens the default web browser directly to a specified URL (e.g. "https://www.google.com" or "https://en.wikipedia.org").',
            parameters={
                'type': 'OBJECT',
                'properties': {
                    'url': {'type': 'STRING'}
                },
                'required': ['url']
            }
        )
        tool_browser_navigate = types.FunctionDeclaration(
            name='browser_navigate',
            description='Navigates the currently active browser to a new URL by focusing the address bar (Ctrl+L), typing the URL, and pressing Enter.',
            parameters={
                'type': 'OBJECT',
                'properties': {
                    'url': {'type': 'STRING'}
                },
                'required': ['url']
            }
        )
        tool_browser_new_tab = types.FunctionDeclaration(
            name='browser_new_tab',
            description='Opens a new browser tab with Ctrl+T and optionally navigates to a URL.',
            parameters={
                'type': 'OBJECT',
                'properties': {
                    'url': {'type': 'STRING'}
                }
            }
        )
        tool_browser_close_tab = types.FunctionDeclaration(
            name='browser_close_tab',
            description='Closes the active browser tab with Ctrl+W.',
            parameters={'type': 'OBJECT'}
        )
        tool_click_and_type = types.FunctionDeclaration(
            name='click_and_type',
            description='Clicks on an input field/search bar, clears any existing text, types the new text, and optionally presses Enter.',
            parameters={
                'type': 'OBJECT',
                'properties': {
                    'x': {'type': 'INTEGER'},
                    'y': {'type': 'INTEGER'},
                    'text': {'type': 'STRING'},
                    'press_enter': {'type': 'BOOLEAN', 'description': 'Whether to press Enter after typing.'}
                },
                'required': ['x', 'y', 'text']
            }
        )
        tool_browser_scroll = types.FunctionDeclaration(
            name='browser_scroll',
            description='Scrolls the active web page "down" or "up" by a pixel amount (default 400).',
            parameters={
                'type': 'OBJECT',
                'properties': {
                    'direction': {'type': 'STRING', 'enum': ['down', 'up']},
                    'amount': {'type': 'INTEGER'}
                },
                'required': ['direction']
            }
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
            tool_click, tool_double_click, tool_type_text, tool_press_key, tool_hotkey, tool_wait, 
            tool_check_app_opened, tool_open_browser, tool_browser_navigate, tool_browser_new_tab, 
            tool_browser_close_tab, tool_click_and_type, tool_browser_scroll, tool_done
        ])
        
        system_instruction = (
            "You are an expert desktop and browser automation agent on Windows. You are given screenshots and a user goal.\n"
            "BROWSER AUTOMATION RULES:\n"
            "1. To open a website or launch a browser, use `open_browser(url=...)` or `browser_navigate(url=...)`. "
            "This directly opens the browser and navigates without manual address bar clicking.\n"
            "2. To search or fill web form inputs, use `click_and_type(x, y, text, press_enter=True)`. "
            "It automatically focuses the input, clears placeholder text, types the query, and presses Enter!\n"
            "3. To scroll down web pages to read more or locate links, use `browser_scroll(direction='down')`.\n"
            "4. To open multiple tabs, use `browser_new_tab(url=...)` and close them with `browser_close_tab()`.\n"
            "5. To click web links or buttons, use `click(x, y)`.\n"
            "\n"
            "GENERAL RULES:\n"
            "1. When opening an app, ensure it actually launches before calling `done`. Use `check_app_opened` or verify the window in the screenshot.\n"
            "2. When searching in Start menu or Windows Search, always press Enter or click the result.\n"
            "3. Take one action at a time and carefully inspect the new screenshot before deciding the next step."
        )

        # Format history
        history_text = "Previous actions taken:\n"
        for act in previous_actions:
            history_text += f"- {act}\n"
        if not previous_actions:
            history_text += "None.\n"

        user_content = f"Goal: {prompt}\n{history_text}\nWhat is the next action?"

        # Optimize screenshot for lightning-fast network transmission (~90% smaller payload)
        buf = io.BytesIO()
        screenshot.convert('RGB').save(buf, format='JPEG', quality=80)
        buf.seek(0)
        opt_screenshot = Image.open(buf)

        response = None
        last_error = None
        for model in self.candidate_models:
            try:
                import time
                t0 = time.time()
                response = self.client.models.generate_content(
                    model=model,
                    contents=[opt_screenshot, user_content],
                    config=types.GenerateContentConfig(
                        tools=[tools],
                        system_instruction=system_instruction,
                        temperature=0.0
                    )
                )
                dt = round(time.time() - t0, 2)
                self.model_name = model
                print(f"Model ({model}) responded in {dt}s")
                break
            except Exception as e:
                last_error = e
                continue

        if response is None:
            return {'name': 'error', 'args': {'message': f'All models failed. Last error: {last_error}'}}

        if response.function_calls:
            fc = response.function_calls[0]
            # Handle possible differences in argument structure
            args = {k: v for k, v in fc.args.items()} if fc.args else {}
            return {
                'name': fc.name,
                'args': args
            }
        elif response.text:
            return {
                'name': 'message',
                'args': {'text': response.text}
            }
        else:
            return {'name': 'error', 'args': {'message': 'No tool call or text returned.'}}
