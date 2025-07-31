# Web Timetable Generator

As a lot of students in IITM use google calendar to keep a track of their courses and other daily activities, the following is a program to create a google calendar `.ics` file which can be imported to your calendar.

## Steps for running
You can create your own timetable in the follwing way

### Step 1
Clone the repository or download the `.zip` file.
```
git clone https://github.com/vatsalramanuj/timetable_maker.git
```

### Step 2
Open the folder location and install the requirements and run the `app.py` file.
```
pip install requirements.txt
python3 app.py
```

### Step 3 
Click on the localhost link, typically at http://127.0.0.1:5000
You will be prompted to add your **course number**, **course name**, **slot** and the **classroom**. Finally click on the `Generate Timetable ` button and a file called `timetable.ics` will be downloaded. A duplicate file will also be created in the directory where your app is saved. 

### Step 4
To import the .ics file in your google calendar, navigate to the web version of [Calendar](https://calendar.google.com/calendar/) and tap the "**+**" on the other calendars tab on the left. Chose the "**import**" option and select your `timetable.ics` file while importing from computer. 

## Features
1. Semester start date and duration of recurrence (in weeks) can be customised. 
2. Mtech level courses (5 level and above) will automatically be slotted to their correct timeslots (12:00 to 12:50 instead of 13:00 to 13:50) whenever required.
3. Optionally you can create a seaparate time table like "classes" in which you can upload the `.ics` file.
