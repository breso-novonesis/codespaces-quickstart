import os
import requests
import random
from typing import Any, Text, Dict, List

from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet

# --- HELPER FUNCTIONS (These remain the same) ---

def run_remediation_script(script_name: str, user_id: str) -> bool:
    """
    Placeholder function to simulate running a remediation script.
    In a real system, this would make an API call to AWS SSM or Microsoft Intune.
    """
    print(f"INFO: Attempting to run script '{script_name}' for user '{user_id}'.")
    # Simulate a 75% success rate for the POC
    return random.random() < 0.75

def create_servicenow_ticket(user_id: str, short_description: str, details: str) -> str:
    """Creates a ServiceNow incident and returns the ticket number."""
    SN_INSTANCE = os.environ.get("SN_INSTANCE")
    SN_USER = os.environ.get("SN_USER")
    SN_PASSWORD = os.environ.get("SN_PASSWORD")

    if not all([SN_INSTANCE, SN_USER, SN_PASSWORD]):
        print("ERROR: ServiceNow credentials not configured.")
        return "N/A (Config Error)"

    url = f"https://{SN_INSTANCE}.service-now.com/api/now/table/incident"
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    data = {"caller_id": user_id, "short_description": short_description, "description": details, "urgency": "3", "impact": "3"}

    try:
        response = requests.post(url, auth=(SN_USER, SN_PASSWORD), headers=headers, json=data)
        response.raise_for_status()
        ticket_data = response.json().get("result", {})
        return ticket_data.get("number", "N/A")
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Failed to create ServiceNow ticket: {e}")
        return "N/A (Connection Error)"

# --- NEW, SPECIFIC CUSTOM ACTIONS ---

class ActionFixPrinter(Action):
    def name(self) -> str:
        return "action_fix_printer"

    async def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        user_id = tracker.sender_id
        script_name = "Clear-Print-Spooler.ps1"
        
        success = run_remediation_script(script_name, user_id)

        if success:
            dispatcher.utter_message(response="utter_confirm_printer_fix")
        else:
            short_desc = "Automated fix failed for: Printer Issue"
            details = f"Attempted to run script '{script_name}' for user '{user_id}' but it failed."
            ticket_number = create_servicenow_ticket(user_id, short_desc, details)
            dispatcher.utter_message(response="utter_inform_ticket_number", ticket_number=ticket_number)
        return []

class ActionResetPassword(Action):
    def name(self) -> str:
        return "action_reset_password"

    async def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        user_id = tracker.sender_id
        script_name = "Initiate-Password-Reset.ps1"

        success = run_remediation_script(script_name, user_id)

        if success:
            dispatcher.utter_message(response="utter_confirm_password_reset_fix")
        else:
            short_desc = "Automated fix failed for: Password Reset"
            details = f"Attempted to run script '{script_name}' for user '{user_id}' but it failed."
            ticket_number = create_servicenow_ticket(user_id, short_desc, details)
            dispatcher.utter_message(response="utter_inform_ticket_number", ticket_number=ticket_number)
        return []

class ActionCreateServiceNowTicket(Action):
    def name(self) -> str:
        return "action_create_servicenow_ticket"

    async def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        user_query = tracker.latest_message.get('text')
        user_id = tracker.sender_id
        short_desc = "Chatbot Fallback: User query unclassified"
        details = f"The user reported an issue that the chatbot could not categorize.\n\nUser Query: '{user_query}'"
        ticket_number = create_servicenow_ticket(user_id, short_desc, details)
        return [SlotSet("ticket_number", ticket_number)]