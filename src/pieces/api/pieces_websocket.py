## WEBSOCKET FUNCTIONS 
import json
import websocket
import threading
import pieces_os_client
from rich.live import Live
from rich.markdown import Markdown
from . import config
import pieces_os_client as pos_client

WEBSOCKET_URL = "ws://localhost:1000/qgpt/stream"
TIMEOUT = 20  # seconds




class WebSocketManager:
    def __init__(self):
        self.ws = None
        self.is_connected = False
        self.model_id = ""
        self.query = ""
        self.final_answer = ""
        self.conversation = None
        self.verbose = True
        self.live = None
        self.message_compeleted = threading.Event()
    
    def open_websocket(self):
        """Opens a websocket connection"""
        self.open_event = threading.Event()  # wait for opening event
        self.start_thread = threading.Thread(target=self._start_ws)
        self.start_thread.start()
        self.open_event.wait()
        
    def on_message(self,ws, message):
        """Handle incoming websocket messages."""
        try:
            response = pieces_os_client.QGPTStreamOutput.from_json(message)
            if response.question:
                answers = response.question.answers.iterable
                if not self.live and self.verbose:  # Create live instance if it doesn't exist
                    self.live = Live()
                    self.live.__enter__()  # Enter the context manually
                for answer in answers:
                    text = answer.text
                    self.final_answer += text
                    if self.verbose and text:
                        self.live.update(Markdown(self.final_answer))

                        

            if response.status == 'COMPLETED':
                if self.verbose:
                    self.live.update(Markdown(self.final_answer),refresh=True)
                    self.live.stop()
                    self.live = None
                    print("\n")
                

                self.conversation = response.conversation

                self.message_compeleted.set()

        except Exception as e:
            print(f"Error processing message: {e}")

    def on_error(self, ws, error):
        """Handle websocket errors."""
        print(f"WebSocket error: {error}")
        self.is_connected = False

    def on_close(self, ws, close_status_code, close_msg):
        """Handle websocket closure."""
        if self.verbose:
            print("WebSocket closed")
        self.is_connected = False

    def on_open(self, ws):
        """Handle websocket opening."""
        if self.verbose:
            print("WebSocket connection opened.")
        self.is_connected = True
        self.open_event.set()

    def _start_ws(self):
        """Start a new websocket connection."""
        if self.verbose:
            print("Starting WebSocket connection...")
        ws =  websocket.WebSocketApp(WEBSOCKET_URL,
                                         on_open=self.on_open,
                                         on_message=self.on_message,
                                         on_error=self.on_error,
                                         on_close=self.on_close)
        self.ws = ws
        ws.run_forever()
        

    def send_message(self,model_id,query,relevant):
        """Send a message over the websocket."""
        message=json.dumps({
            "question": {
                "query": query,
                "relevant": relevant,
                "model": model_id
            },
            "conversation": self.conversation})
        if self.is_connected:
            try:
                self.ws.send(message)
                if self.verbose:
                    print("Response: ")
            except websocket.WebSocketException as e:
                print(f"Error sending message: {e}")
        else:
            self.open_websocket()
            self.send_message(model_id,query,relevant)

    def close_websocket_connection(self):
        """Close the websocket connection."""
        if self.ws and self.is_connected:
            self.ws.close()
            self.is_connected = False

    def ask_question(self, model_id,query,relevant={"iterable": []},verbose = True):
        """Ask a question using the websocket."""
        self.final_answer = ""
        self.verbose = verbose
        self.send_message(model_id,query,relevant)
        finishes = self.message_compeleted.wait(TIMEOUT)
        self.message_compeleted.clear()
        if not config.run_in_loop and self.is_connected:
            self.close_websocket_connection()
        self.verbose = True
        if not finishes:
            raise ConnectionError("Failed to get the reponse back")
        return self.final_answer