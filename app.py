from flask import Flask, request, send_file, jsonify
from datetime import datetime, date
import os
import json
import pandas as pd
import re # Import re for regex operations in parsing

# Import core timetable generation logic from your existing file
# Ensure ics_maker.py is in the same directory as app.py
try:
    from ics_maker import create_timetable, generate_ics_file, convert_to_24_hour_py
except ImportError as e:
    print(f"Error importing ics_maker.py: {e}")
    print("Please ensure ics_maker.py is in the same directory as app.py")
    exit()

app = Flask(__name__)

# Define paths relative to the app.py script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_FILE_PATH = os.path.join(BASE_DIR, 'my_courses.csv')
SLOT_MAPPING_DIR = os.path.join(BASE_DIR, 'slot_mapping')
ICS_OUTPUT_FILENAME = os.path.join(BASE_DIR, 'timetable.ics')

@app.route('/')
def index():
    """Serves the main HTML page."""
    return send_file(os.path.join(BASE_DIR, 'index.html'))

@app.route('/generate-timetable', methods=['POST'])
def generate_timetable_endpoint():
    """
    Receives timetable configuration and course data, generates ICS,
    and sends it back for download.
    """
    try:
        data = request.get_json()
        degree = ""
        # degree = data.get('degree')
        start_date_str = data.get('startDate')
        num_weeks_str = data.get('numWeeks')
        courses_data = data.get('courses', [])

        # --- Input Validation ---
        # if not degree or degree not in ['btech', 'mtech']:
        #     return jsonify({"error": "Invalid or missing degree."}), 400
        
        if not start_date_str:
            return jsonify({"error": "Semester Start Date is required."}), 400
        try:
            start_date_for_events = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"error": "Invalid date format. Use YYYY-MM-DD."}), 400

        if not num_weeks_str:
            return jsonify({"error": "Number of Recurrence Weeks is required."}), 400
        try:
            num_recurrence_weeks = int(num_weeks_str)
            if num_recurrence_weeks <= 0:
                raise ValueError
        except ValueError:
            return jsonify({"error": "Number of Recurrence Weeks must be a positive integer."}), 400
        
        if not courses_data:
            return jsonify({"error": "No course details provided."}), 400

        # --- 1. Create my_courses.csv from received data ---
        df_courses_to_save = pd.DataFrame(courses_data)
        df_courses_to_save.to_csv(CSV_FILE_PATH, index=False)
        print(f"Generated '{CSV_FILE_PATH}' from web input.")

        # --- 2. Load slot mapping ---
        slot_mapping_file_path = "slot_mapping.json"
        print(slot_mapping_file_path)
        if not os.path.exists(slot_mapping_file_path):
            return jsonify({"error": f"Slot mapping file '{slot_mapping_file_path}' not found on server."}), 500
        
        slot_mapping = {}
        try:
            with open(slot_mapping_file_path, 'r') as f:
                slot_mapping = json.load(f)
            print(f"Slot mapping loaded successfully from '{slot_mapping_file_path}'.")
        except json.JSONDecodeError:
            return jsonify({"error": f"Invalid JSON format in slot mapping file '{slot_mapping_file_path}'."}), 500
        except Exception as e:
            return jsonify({"error": f"Error loading slot mapping: {str(e)}"}), 500

        # --- 3. Call core timetable generation logic ---
        # create_timetable returns (pandas.DataFrame, list_of_ics_events_data)
        generated_timetable_df, ics_events_list = create_timetable(
            CSV_FILE_PATH, slot_mapping, start_date_for_events
        )

        if generated_timetable_df.empty or not ics_events_list:
            return jsonify({"error": "Timetable generation resulted in no events."}), 500

        # --- 4. Generate ICS file ---
        generate_ics_file(ics_events_list, start_date_for_events, num_recurrence_weeks, ICS_OUTPUT_FILENAME)
        print(f"ICS file '{ICS_OUTPUT_FILENAME}' generated successfully.")

        # --- 5. Send ICS file back to client ---
        return send_file(ICS_OUTPUT_FILENAME, as_attachment=True, download_name='timetable.ics', mimetype='text/calendar')

    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({"error": f"An internal server error occurred: {str(e)}"}), 500

if __name__ == '__main__':
    # Create slot_mapping directory if it doesn't exist
    os.makedirs(SLOT_MAPPING_DIR, exist_ok=True)
    # You might want to pre-populate slot_mapping/btech.json and mtech.json here
    # or ensure they are present manually.

    # To run the Flask app:
    # 1. Save this file as app.py
    # 2. Save your ics_maker.py in the same directory.
    # 3. Create a 'slot_mapping' directory in the same place and put your .json files inside.
    # 4. Save the HTML frontend as index.html in the same directory.
    # 5. Run: python app.py
    # 6. Open your browser to http://127.0.0.1:5000/
    app.run(debug=True) # debug=True allows auto-reloading and better error messages
