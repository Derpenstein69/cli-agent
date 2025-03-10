## MAIN FUNCTIONS | Line ~33
## HELPER FUNCTIONS | Line ~381

from pieces.gui import *
import json
from bs4 import BeautifulSoup
import os
import re
from pieces.api.pieces_websocket import WebSocketManager
from pieces.api.api_functions import *
from pieces.api.system import *
from pieces.api.assets import *
from pieces.api.config import *
import pickle
from pieces import __version__

# Globals for CLI Memory.
ws_manager = WebSocketManager()
current_asset = None
parser = None
application = None
###############################################################################
############################## MAIN FUNCTIONS #################################
###############################################################################

def startup(): # startup function to run before the cli begin
    global models,model_id,word_limit,application,pieces_os_version
    pieces_os_version = open_pieces_os()
    if pieces_os_version:

        # Call the connect api
        application = connect_api()

        # MODELS
        models = get_models_ids()
        create_file = True
        # Check if the models file exists
        if models_file.is_file():
            with open(models_file, 'rb') as f:
                model_data = pickle.load(f)
            model_id = model_data["model_id"]
            word_limit = model_data["word_limit"]
            try: # Checks if the current model is valid
                get_current_model_name()
                create_file = False
            except:
                pass
            
        if create_file:
            default_model_name = "GPT-3.5-turbo Chat Model"
            model_id = models[default_model_name]["uuid"] # default model id
            word_limit = models[default_model_name]["word_limit"] # The word limit of the default model
            dump_pickle(file = models_file, model_id=model_id, word_limit=word_limit)
            global current_asset
        current_asset = get_asset_ids(1)[0] # default current asset to the most recent
    else:
        server_startup_failed()
        

def ask(query, **kwargs):
    global model_id, ws_manager
    try:
        ws_manager.ask_question(model_id, query)
    except Exception as e:
        show_error("Error occurred while asking the question:", e)

def search(query, **kwargs):
    global asset_ids 

    search_type = kwargs.get('search_type', 'assets')

    # Join the list of strings into a single search phrase
    search_phrase = ' '.join(query)

    # Call the API function with the search phrase and type
    results = search_api(search_phrase, search_type)

    # Check and extract asset IDs from the results
    if results:
        # Extract the iterable which contains the search results
        iterable_list = results.iterable if hasattr(results, 'iterable') else []

        # Check if iterable_list is a list and contains SearchedAsset objects
        if isinstance(iterable_list, list) and all(hasattr(asset, 'exact') and hasattr(asset, 'identifier') for asset in iterable_list):
            # Extracting suggested and exact IDs
            suggested_ids = [asset.identifier for asset in iterable_list if not asset.exact]
            exact_ids = [asset.identifier for asset in iterable_list if asset.exact]

            # Combine and store best and suggested matches in asset_ids
            combined_ids = exact_ids + suggested_ids
            asset_ids = {index + 1: asset_id for index, asset_id in enumerate(combined_ids)}

            # Prepare the combined list of names for printing
            combined_details = [(asset_id, get_asset_name_by_id(asset_id)) for asset_id in combined_ids]

            # Print the combined asset details
            if combined_details:
                print_asset_details(combined_details, "Asset Matches:", search_type)
            else:
                print("No matches found.")
        else:
            print("Unexpected response format or empty iterable.")
    else:
        print("No results found.")



def change_model(**kwargs): # Change the model used in the ask command
    global model_id,word_limit
    model_index = kwargs.get('MODEL_INDEX')
    try:
        if model_index:
            model_name = list(models.keys())[model_index-1] # because we begin from 1
            word_limit = models[model_name].get("word_limit")
            model_id  = models[model_name].get("uuid")
            dump_pickle(file = models_file,model_id = model_id,word_limit = word_limit)
            print(f"Switched to {model_name} with uuid {model_id}")
        else:
            raise Exception("Invalid model index or model index not provided.")
    except:
        print("Invalid model index or model index not provided.")
        print("Please choose from the list or use 'pieces list models'")
        



###############################################################################
############################## HELPER FUNCTIONS ###############################
###############################################################################
def dump_pickle(file,**data):
    """Store data in a pickle file."""
    with open(file, 'wb') as f:
        pickle.dump(data, f)


def get_current_model_name() -> str:
    with open(models_file, 'rb') as f:
        model_data = pickle.load(f)
    model_id = model_data["model_id"]
    models_reverse = {v.get("uuid"):k for k,v in models.items()}
    return models_reverse[model_id]


def get_asset_name_by_id(asset_id):
    asset = get_asset_by_id(asset_id)  # Assuming this function returns the asset details
    return asset.get('name') if asset else "Unknown"

def set_parser(p):
    global parser
    parser = p


# Used to create a valid file name when opening to "Opened Snippets"
def sanitize_filename(name):
    """ Sanitize the filename by removing or replacing invalid characters. """
    # Replace spaces with underscores
    name = name.replace(" ", "_")
    # Remove invalid characters
    name = re.sub(r'[\\/*?:"<>|]', '', name)
    return name

def extract_code_from_markdown(markdown, name, language):
    # Sanitize the name to ensure it's a valid filename
    filename = sanitize_filename(name)
    file_extension = get_file_extension(language)

    # Using BeautifulSoup to parse the HTML and extract text
    soup = BeautifulSoup(markdown, 'html.parser')
    extracted_code = soup.get_text()

    # Minimize multiple consecutive newlines to a single newline
    extracted_code = re.sub(r'\n\s*\n', '\n', extracted_code)

    # Ensure the directory exists, create it if not
    if not os.path.exists(open_snippet_dir):
        os.makedirs(open_snippet_dir)

    # Path to save the extracted code
    file_path = os.path.join(open_snippet_dir, f'{filename}{file_extension}')

    # Writing the extracted code to a new file
    with open(file_path, 'w') as file:
        file.write(extracted_code)

    return file_path

def get_file_extension(language):
    with open(extensions_dir) as f:
        extension_mapping = json.load(f)

    # Lowercase the language for case-insensitive matching
    language = language.lower()

    # Return the corresponding file extension or default to '.txt' if not found
    return extension_mapping.get(language, '.txt')

def version(**kwargs):

    if pieces_os_version:
        print(f"Pieces Version: {pieces_os_version}")
        print(f"Cli Version: {__version__}")
    else:
        ### LOGIC TO look up cache from SQLite3 to get the cli and pieces os version

        # Get the version from cache
        # Establish a local database connection
        # conn = create_connection('applications.db')

        # # Create the table if it does not exist
        # create_table(conn)
        # # create_tables(conn)

        # # Check the database for an existing application
        # application_id = "DEFAULT"  # Replace with a default application ID
        # application = get_application(conn, application_id)
        # # application =  get_application_with_versions(conn, application_id)
        pass
