import os
from jira import JIRA

# --- Jira Connection ---
try:
    jira = JIRA({'server': JIRA_URL}, basic_auth=(JIRA_USER, JIRA_API_TOKEN))
    print(f"Connected to Jira at {JIRA_URL}")
except Exception as e:
    print(f"Error connecting to Jira: {e}")
    exit()

# --- Script Logic ---
if __name__ == "__main__":
    print(f"Starting data recovery for project: {PROJECT_KEY}")

    # JQL query to get all issues in the specified project
    if TEST_ISSUE_KEY:
        jql_query = f"issue = {TEST_ISSUE_KEY}"
        print(f"Processing only test issue: {TEST_ISSUE_KEY}")
    else:
        jql_query = f"project = {PROJECT_KEY} ORDER BY key ASC"


    try:
        # Search for all issues in the project, expanding changelog for each
        # maxResults=False ensures all issues are retrieved
        issues = jira.search_issues(jql_query, expand='changelog', maxResults=False)
        total_issues_found = len(issues)
        print(f"Found {len(issues)} issues in project {PROJECT_KEY}.")

        if not issues:
            print("No issues found in the project.")
            exit()

        for i, issue in enumerate(issues[START_AT_ISSUE_INDEX:]):
            current_issue_number_in_run = i + 1
            actual_issue_index_in_project = i + START_AT_ISSUE_INDEX + 1
            print(f"\nProcessing issue {current_issue_number_in_run} of this run ({actual_issue_index_in_project}/{total_issues_found} overall): {issue.key}")

            original_component_value = None
            # Iterate through histories in reverse to find the most recent valid value
            for history in reversed(issue.changelog.histories):
                for item in history.items:
                    # Ensure the item is a field change and has fieldId before accessing it
                    # Also check if the field ID matches your old Product field
                    if hasattr(item, 'fieldId') and item.fieldId == OLD_CUSTOM_COMPONENT_FIELD_ID:
                        # Prioritize 'toString' if available and not empty, otherwise 'fromString'
                        if hasattr(item, 'toString') and item.toString is not None and item.toString != '':
                            original_component_value = item.toString
                            break # Found a value, stop looking in this history item
                        elif hasattr(item, 'fromString') and item.fromString is not None and item.fromString != '':
                            original_component_value = item.fromString
                            # Don't break yet, keep looking for a 'toString' value in older items if current 'toString' is empty
                if original_component_value: # If a value was found in any item of this history, stop searching histories
                    break

            if original_component_value is not None and original_component_value != '':
                print(f"  Found original value for custom field '{OLD_CUSTOM_COMPONENT_FIELD_ID}': '{original_component_value}'.")

                components_to_set = [{'name': original_component_value}]

                # Get the current values of the standard 'Components' field on the issue
                # The 'components' field is a list of Component objects.
                current_components_obj = getattr(issue.fields, NEW_JIRA_COMPONENTS_FIELD_NAME, [])
                # Convert current components to a list of names for comparison
                current_component_names = [comp.name for comp in current_components_obj] if current_components_obj else []

                if sorted(current_component_names) == sorted([original_component_value]):
                    print(f"  Field '{NEW_JIRA_COMPONENTS_FIELD_NAME}' on {issue.key} already has value '{original_component_value}'. Skipping update.")
                else:
                    issue.update(fields={NEW_JIRA_COMPONENTS_FIELD_NAME: components_to_set})
                    print(f"  Successfully updated '{NEW_JIRA_COMPONENTS_FIELD_NAME}' on {issue.key} to '{original_component_value}'.")
            else:
                print(f"  No historical or non-empty value found for custom field '{OLD_CUSTOM_COMPONENT_FIELD_ID}' in changelog for {issue.key}.")

    except Exception as e:
        print(f"An error occurred during issue processing: {e}")
    print("\nScript execution finished.")