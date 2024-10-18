from __future__ import print_function
import datetime
import os.path
import sqlite3
from sys import argv
from dateutil import parser
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ['']

# ADD YOUR CALENDAR ID HERE
YOUR_CALENDAR_ID = ''
YOUR_TIMEZONE = 'Asia/Kolkata'  # Example for India

def main():
    """Main function to determine the action to perform based on command-line arguments."""
    creds = None
    # Load credentials from token.json if it exists
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # Authenticate if credentials are not valid
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    # Check command-line arguments
    if len(argv) < 2:
        print("Usage: python timemanagement.py <add|commit> [<duration> <description>]")
        return

    # Determine which function to run        
    if argv[1] == 'add':
        if len(argv) != 4:
            print("Usage for adding event: python timemanagement.py add <duration> <description>")
            return
        duration = argv[2]
        description = argv[3]
        addEvent(creds, duration, description)
    elif argv[1] == 'commit':
        commitHours(creds)
    else:
        print("Unknown command. Use 'add' or 'commit'.")

# Commit hours to database
def commitHours(creds):
    try:
        service = build('calendar', 'v3', credentials=creds)

        # Get today's date
        today = datetime.date.today()
        timeStart = str(today) + "T00:00:00Z"
        timeEnd = str(today) + "T23:59:59Z"  # 'Z' indicates UTC time
        print("Getting today's coding hours")
        
        events_result = service.events().list(
            calendarId=YOUR_CALENDAR_ID,
            timeMin=timeStart,
            timeMax=timeEnd,
            singleEvents=True,
            orderBy='startTime',
            timeZone=YOUR_TIMEZONE
        ).execute()
        
        events = events_result.get('items', [])
        
        if not events:
            print('No coding events found for today.')
            return

        total_duration = datetime.timedelta()
        print("CODING HOURS:")
        
        for event in events:
            # Print the entire event for debugging
            print(event)
            start = event['start'].get('dateTime', event['start'].get('date'))
            end = event['end'].get('dateTime', event['end'].get('date'))
            start_formatted = parser.isoparse(start)  # Convert to datetime
            end_formatted = parser.isoparse(end)  # Convert to datetime
            duration = end_formatted - start_formatted
            total_duration += duration
            
            # Check if 'summary' exists before printing
            if 'summary' in event:
                print(f"{event['summary']}, duration: {duration}")
            else:
                print("Event has no summary.")

        print(f"Total coding time: {total_duration}")

        conn = sqlite3.connect('hours.db')
        cur = conn.cursor()
        print("Opened database successfully")
        
        date = datetime.date.today()
        formatted_total_duration = total_duration.seconds / 3600  # Convert to hours
        coding_hours = (date, 'CODING', formatted_total_duration)
        cur.execute("INSERT INTO hours VALUES(?, ?, ?);", coding_hours)
        conn.commit()
        print("Coding hours added to database successfully")

    except HttpError as error:
        print(f'An error occurred: {error}')

# Add calendar event from current time for length of 'duration'
def addEvent(creds, duration, description):
    try:
        start = datetime.datetime.utcnow()
        end = start + datetime.timedelta(hours=int(duration))
        start_formatted = start.isoformat() + 'Z'
        end_formatted = end.isoformat() + 'Z'

        event = {
            'summary': description,
            'start': {
                'dateTime': start_formatted,
                'timeZone': YOUR_TIMEZONE,
            },
            'end': {
                'dateTime': end_formatted,
                'timeZone': YOUR_TIMEZONE,
            },
        }

        service = build('calendar', 'v3', credentials=creds)
        event = service.events().insert(calendarId=YOUR_CALENDAR_ID, body=event).execute()
        print('Event created: %s' % (event.get('htmlLink')))

    except Exception as e:
        print(f'An error occurred while adding the event: {e}')

def getHours(number_of_days):
    # Get today's date
    today = datetime.date.today()
    seven_days_ago = today - datetime.timedelta(days=int(number_of_days))

    # Get hours from database
    conn = sqlite3.connect('hours.db')
    cur = conn.cursor()
    cur.execute(f"SELECT DATE, HOURS FROM hours WHERE DATE BETWEEN ? AND ?", (seven_days_ago, today))
    hours = cur.fetchall()

    total_hours = 0
    for element in hours:
        print(f"{element[0]}: {element[1]}")
        total_hours += element[1]
    
    if number_of_days > 0:
        print(f"Total hours: {total_hours}")
        print(f"Average hours: {total_hours / float(number_of_days)}")

if __name__ == '__main__':
    main()
