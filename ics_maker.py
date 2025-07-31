import pandas as pd
import io
import os
import json
import re
from datetime import datetime, timedelta
import urllib.parse 
import uuid 

# ------------------------ Inputs ---------------------------------------

csv_file_path = 'my_courses.csv' # The csv where your courses are stored 
degree = "btech" # Choose your degree btech or mtech
slot_mapping_file_path = f'slot_mapping/{degree}.json' # Chose the json for your degree
start_date = "2025-08-04" # in "yyyy-mm-dd" format

num_recurrence_weeks = 15 # length of the semester (usually 15 weeks) 


# ----------------------- Functions -------------------------------------
def convert_to_24_hour_py(time_str, ampm_str):
    """
    Converts a time string (HH:MM) and optional AM/PM to 24-hour format (HH:MM).
    Assumes time_str is in HH:MM format (e.g., "01:00", "13:00").
    ampm_str is the 'AM' or 'PM' part, if present.
    """
    hours, minutes = map(int, time_str.split(':'))

    if ampm_str: 
        ampm_str_lower = ampm_str.lower()
        if ampm_str_lower == 'pm' and hours < 12: 
            hours += 12
        elif ampm_str_lower == 'am' and hours == 12: 
            hours = 0 
    return f"{hours:02d}:{minutes:02d}"


def generate_ics_file(events_data, start_date_of_week, num_weeks, output_filename="timetable.ics"):
    """
    Generates an ICS file containing all timetable events with weekly recurrence.

    Args:
        events_data (list): A list of dictionaries, each representing a parsed course event.
                            Each dict should have: course_name, course_no, day, startTime, endTime, location.
        start_date_of_week (datetime.date): The date of the Monday for the week
                                            you want to schedule events.
        num_weeks (int): The number of weeks the recurrence should last.
        output_filename (str): The name of the .ics file to create.
    """
    ics_content = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Your Timetable Generator//EN",
        "X-WR-CALNAME:My Academic Timetable" 
    ]

    days_map = {
        "Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3, "Friday": 4,
        "Saturday": 5, "Sunday": 6
    }

    for event in events_data:
        day_of_week = event['day']
        start_time_str = event['startTime']
        end_time_str = event['endTime']
        event_location = event.get('location', 'Unknown Location') 

        day_offset = days_map.get(day_of_week, 0)
        event_date = start_date_of_week + timedelta(days=day_offset)

        
        start_dt = datetime.strptime(f"{event_date} {start_time_str}", "%Y-%m-%d %H:%M")
        end_dt = datetime.strptime(f"{event_date} {end_time_str}", "%Y-%m-%d %H:%M")

        
        
        dtstamp = datetime.now().strftime("%Y%m%dT%H%M%S")
        dtstart = start_dt.strftime("%Y%m%dT%H%M%S")
        dtend = end_dt.strftime("%Y%m%dT%H%M%S")

        
        
        rrule = f"FREQ=WEEKLY;COUNT={num_weeks}"

        ics_content.extend([
            "BEGIN:VEVENT",
            f"UID:{uuid.uuid4()}@your-timetable.com", 
            f"DTSTAMP:{dtstamp}",
            f"DTSTART:{dtstart}",
            f"DTEND:{dtend}",
            f"SUMMARY:{event['courseName']} ({event['courseNo']})",
            f"DESCRIPTION:Course: {event['courseName']}\\nCourse No: {event['courseNo']}\\nSlot: {event['slot']}\\nLocation: {event_location}", 
            f"LOCATION:{event_location}", 
            f"RRULE:{rrule}",
            "END:VEVENT"
        ])

    ics_content.append("END:VCALENDAR")

    with open(output_filename, 'w') as f:
        f.write("\n".join(ics_content))
    
    print(f"\nICS file '{output_filename}' generated successfully.")
    print(f"To add all events to your Google Calendar:")
    print(f"1. Download the file: '{output_filename}'")
    print(f"2. Go to Google Calendar (calendar.google.com).")
    print(f"3. In the left sidebar, next to 'Other calendars', click the '+' icon.")
    print(f"4. Select 'Import'.")
    print(f"5. Choose the '{output_filename}' file from your computer and select the calendar to add it to.")
    print(f"All your courses will be added with weekly recurrence for {num_weeks} weeks.")


def create_timetable(csv_file_path, slot_to_time_mapping, start_date_of_week):
    """
    Creates a timetable from a CSV file containing course data and a slot-to-time mapping.

    Args:
        csv_file_path (str): The file path to the CSV file containing the course table.
                             Expected columns: 'Course No', 'Course Name', 'Slot', 'Class'.
        slot_to_time_mapping (dict): A dictionary mapping slot codes to their
                                     corresponding day and time.
                                     Example: {'A': 'Monday 09:00-10:00', 'B': 'Tuesday 10:00-11:00'}
        start_date_of_week (datetime.date): The date of the Monday for the week
                                            you want to schedule events.

    Returns:
        pandas.DataFrame: A DataFrame representing the generated timetable.
        list: A list of parsed event dictionaries suitable for ICS generation.
    """
    if not os.path.exists(csv_file_path):
        print(f"Error: CSV file not found at '{csv_file_path}'")
        return pd.DataFrame(), [] 

    try:
        df_courses = pd.read_csv(csv_file_path)

    except Exception as e:
        print(f"An error occurred during CSV file reading: {e}")
        print("Please ensure the CSV file is correctly formatted with columns: 'Course No', 'Course Name', 'Slot', 'Class'.")
        return pd.DataFrame(), []

    
    required_columns = ['courseNo', 'courseName', 'slot', 'class']
    if not all(col in df_courses.columns for col in required_columns):
        missing_cols = [col for col in required_columns if col not in df_courses.columns]
        print(f"Error: Missing required columns in CSV: {', '.join(missing_cols)}")
        print("Please ensure your CSV has 'Course No', 'Course Name', 'Slot', and 'Class' columns.")
        return pd.DataFrame(), []

    df_courses['slot'] = df_courses['slot'].astype(str).str.strip()

    
    multi_part_slot_aggregations = {}
    for key in slot_to_time_mapping.keys():
        if '/' in key:
            prefix = key.split('/')[0]
            if len(prefix) == 1 and prefix.isalpha():
                if prefix not in multi_part_slot_aggregations:
                    multi_part_slot_aggregations[prefix] = []
                multi_part_slot_aggregations[prefix].append(key)
    

    timetable_data = [] 
    ics_events_data = [] 

    for index, row in df_courses.iterrows():
        course_no = str(row.get('courseNo', 'N/A')).strip()
        course_name = row.get('courseName', 'N/A')
        original_slot = row.get('slot', '')
        class_location = str(row.get('class', '')) 

        final_time_slots_for_course = []

        if original_slot in multi_part_slot_aggregations:
            for remapped_key in multi_part_slot_aggregations[original_slot]:
                if remapped_key in slot_to_time_mapping:
                    final_time_slots_for_course.append(slot_to_time_mapping[remapped_key])
                else:
                    print(f"Warning: Remapped slot '{remapped_key}' (from original '{original_slot}') not found in mapping for course '{course_name}'.")
            
            if not final_time_slots_for_course and original_slot in slot_to_time_mapping:
                final_time_slots_for_course.append(slot_to_time_mapping[original_slot])
                print(f"Info: No multi-part mappings found for '{original_slot}', falling back to direct mapping.")

        if not final_time_slots_for_course and original_slot in slot_to_time_mapping:
            final_time_slots_for_course.append(slot_to_time_mapping[original_slot])
        elif not final_time_slots_for_course:
            print(f"Warning: No time mapping found for slot '{original_slot}' for course '{course_name}'.")
            final_time_slots_for_course.append('N/A (Mapping Missing)')

        time_slot_combined_string = ", ".join(final_time_slots_for_course)

        
        is_mtech_course = False
        first_digit_match = re.search(r'\d', course_no)
        print(course_no)
        if first_digit_match:
            first_digit = int(first_digit_match.group(0))
            if first_digit >= 5:
                is_mtech_course = True
        
        if is_mtech_course:
            individual_time_slots_for_shift = [s.strip() for s in time_slot_combined_string.split(',') if s.strip()]
            modified_time_slots = []
            
            target_time_regex = re.compile(r'^(Mon|Tue|Wed|Thu|Fri)\s+13:00\s*(?:AM|PM|am|pm)?\s*-\s*13:50\s*(?:AM|PM|am|pm)?$', re.IGNORECASE)

            for single_time_range in individual_time_slots_for_shift:
                normalized_time_range = re.sub(r'\s+', ' ', single_time_range).strip()
                
                normalized_time_range = re.sub(r'\s+', ' ', single_time_range).strip()
                if normalized_time_range[-19:] == "13:00 PM - 13:50 PM":
                    day_of_week = normalized_time_range[:-19]
                    new_time_range = f"{day_of_week} 12:00 PM - 12:50 PM"
                    modified_time_slots.append(new_time_range)
                else:
                    modified_time_slots.append(single_time_range)
            
            time_slot_combined_string = ", ".join(modified_time_slots)
        

        
        for single_time_range_for_ics in [s.strip() for s in time_slot_combined_string.split(',') if s.strip()]:
            full_time_slot_regex = re.compile(r'^(\w+)\s+(\d{1,2}:\d{2})\s*([AP]M|[ap]m)?\s*-\s*(\d{1,2}:\d{2})\s*([AP]M|[ap]m)?$', re.IGNORECASE)
            full_match = full_time_slot_regex.match(single_time_range_for_ics)

            if full_match:
                day_for_ics = full_match.group(1)
                start_time_24hr = convert_to_24_hour_py(full_match.group(2), full_match.group(3))
                end_time_24hr = convert_to_24_hour_py(full_match.group(4), full_match.group(5))

                ics_events_data.append({
                    'courseName': course_name,
                    'courseNo': course_no,
                    'slot': original_slot,
                    'day': day_for_ics,
                    'startTime': start_time_24hr,
                    'endTime': end_time_24hr,
                    'location': class_location 
                })
            else:
                print(f"Warning: Could not parse time string for ICS generation: '{single_time_range_for_ics}' for course '{course_name}'")


        timetable_data.append({
            'Course No': course_no,
            'Course Name': course_name,
            'Slot': original_slot,
            'Class': class_location, 
            'Time Slot': time_slot_combined_string
        })

    df_timetable = pd.DataFrame(timetable_data)
    return df_timetable, ics_events_data





# -------------------- Execution ----------------------------
if __name__ == "__main__":

    start_date_for_events = datetime.strptime(start_date, '%Y-%m-%d').date() 
    slot_mapping = {}
    if not os.path.exists(slot_mapping_file_path):
        print(f"Error: Slot mapping file not found at '{slot_mapping_file_path}'")
        print("Please create a JSON file with your slot to time mappings.")
    else:
        try:
            with open(slot_mapping_file_path, 'r') as f:
                slot_mapping = json.load(f)
            print(f"Slot mapping loaded successfully from '{slot_mapping_file_path}'")
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON from '{slot_mapping_file_path}': {e}")
            print("Please ensure your slot mapping JSON file is correctly formatted.")
        except Exception as e:
            print(f"An unexpected error occurred while loading slot mapping: {e}")

    if slot_mapping:
        generated_timetable_df, ics_events_list = create_timetable(csv_file_path, slot_mapping, start_date_for_events)

        if not generated_timetable_df.empty:
            
            output_csv_filename = 'my_timetable.csv'
            generated_timetable_df.to_csv(output_csv_filename, index=False)

            print(f"Timetable successfully generated and saved to '{output_csv_filename}'")
            print("\nGenerated Timetable Preview:")
            print(generated_timetable_df)

            
            if ics_events_list:
                generate_ics_file(ics_events_list, start_date_for_events, num_recurrence_weeks)
            else:
                print("No events parsed for ICS generation.")
        else:
            print("Timetable generation failed. Please check the error messages above.")
    else:
        print("Timetable generation skipped due to errors in loading slot mapping.")
