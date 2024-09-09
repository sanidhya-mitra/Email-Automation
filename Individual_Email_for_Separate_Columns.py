import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import pandas as pd
import requests
from requests.auth import HTTPBasicAuth

# JIRA API credentials
base_url = "https://corecard.atlassian.net/"
api_token = ""
email = ""

# API endpoint to fetch issues
endpoint = f"{base_url}rest/api/3/search"
headers = {
    "Accept": "application/json"
}

# JQL query
jql = "project = CCP AND issuetype = epic AND fixVersion in('R40','R39') AND status not in (Cancelled)"
params = {
    "jql": jql,
    "maxResults": 100, 
    "startAt": 0        # Starting index for pagination
}

# List to store all issues
all_issues = []

try:
    while True:
        # Request
        response = requests.get(
            endpoint,
            headers=headers,
            params=params,
            auth=HTTPBasicAuth(email, api_token)
        )

        if response.status_code == 200:
            data = response.json()

            # Extracting issues from the response
            issues = data.get('issues', [])
            all_issues.extend(issues)

            # Checking if there are more issues to fetch
            total = data.get('total', 0)
            start_at = params['startAt']
            max_results = params['maxResults']
            
            if start_at + max_results >= total:
                break  # All issues have been fetched

            # Update startAt to fetch the next page
            params['startAt'] += max_results
        
            # Prepare data for DataFrame
            df_data = []
            for issue in all_issues:
                key = issue.get('key', '')
                fields = issue.get('fields', {})

                # Extracting the required fields
                summary = fields.get('summary', '')
                status = fields.get('status', {})
                status_name = status.get('name', '') if status else ''
                assignee = fields.get('assignee', {})
                assignee_name = assignee.get('displayName', 'Unassigned') if assignee else 'Unassigned'
                created = fields.get('created', '-')
                fix_versions = fields.get('fixVersions', [])
                fix_versions_names = [version.get('name', '') for version in fix_versions]
                fix_versions_str = ', '.join(fix_versions_names)
                parent = fields.get('parent', {})
                parent_key = parent.get('key', '-')
                # Custom fields
                ba = fields.get('customfield_10112', [])
                ba_manager = ba[0].get('displayName') if ba else None
                ba_res = fields.get('customfield_10113', [])
                ba_resource = ba_res[0].get('displayName') if ba_res else None
                dev = fields.get('customfield_10114', [])
                dev_manager = dev[0].get('displayName') if dev else None
                dev_resource = fields.get('customfield_10115', [])
                development_resource = dev_resource[0].get('displayName') if dev_resource else None
                t_manager = fields.get('customfield_10116', [])
                test_manager = t_manager[0].get('displayName') if t_manager else None
                t_resource = fields.get('customfield_10117', [])
                test_resource = t_resource[0].get('displayName') if t_resource else None
                u_manager = fields.get('customfield_10118', [])
                uat_manager = u_manager[0].get('displayName') if u_manager else None
                u_resource = fields.get('customfield_10119', [])
                uat_resource = u_resource[0].get('displayName') if u_resource else None
                baeffort = fields.get('customfield_10122', None)
                ba_effort = baeffort
                qaeffort = fields.get('customfield_10125', None)
                qa_effort = qaeffort

                # Appending the extracted information as a dictionary to the list
                df_data.append({
                    'Key': key,
                    'Summary': summary,
                    'Status': status_name,
                    'Assignee': assignee_name,
                    'Created': created,
                    'Fix Version': fix_versions_str,
                    'Parent Key': parent_key,
                    'BA Manager': ba_manager,
                    'BA Resource': ba_resource,
                    'Dev Manager': dev_manager,
                    'Dev Resource': development_resource,
                    'Test Manager': test_manager,
                    'Test Resource': test_resource,
                    'UAT Manager': uat_manager,
                    'UAT Resource': uat_resource,
                    'BA Effort': ba_effort,
                    'QA Effort': qa_effort
                })

            # Creating a Master DataFrame from the extracted data
            df = pd.DataFrame(df_data)

                    # Function to make the Key column clickable
            def make_key_clickable(df):
                        df['Key'] = df['Key'].apply(lambda x: f'<a href="{base_url}browse/{x}" target="_blank">{x}</a>')
                        return df

                    # Method to process the DataFrame based on field_id:
                        # It takes two arguments, the dataframe to bifurcate and the ID of the custom field
                        # Then it returns a dataframe for the relevant field_id
            def segregate_dataframe(df, field_id, sub_field=None):
                        # Segregates the dataframe based on the provided field_id and optionally a sub_field.
                        
                        # Parameters:
                        #     df (pd.DataFrame): The original dataframe.
                        #     field_id (str): The main field_id to filter the dataframe.
                        #     sub_field (str): An optional sub_field to differentiate when multiple fields share the same field_id.
                            
                        # Returns:
                        #     pd.DataFrame: The filtered and formatted dataframe.
                        
                        df_filtered = None
                        
                        if field_id == 'customfield_10112':  # BA Manager or BA Effort field_id
                            if sub_field == 'BA Manager':
                                df_filtered = df[df[['BA Manager']].isna().any(axis=1)]
                                df_filtered = df_filtered.fillna('-') 
                                df_filtered = make_key_clickable(df_filtered)
                                return df_filtered[['Key', 'Summary', 'Status', 'Assignee', 'Fix Version', 'BA Manager']]
                            elif sub_field == 'BA Effort':
                                df_filtered = df[df[['BA Effort']].isna().any(axis=1)]
                                df_filtered = df_filtered.fillna('-') 
                                df_filtered = make_key_clickable(df_filtered)
                                return df_filtered[['Key', 'Summary', 'Status', 'Assignee', 'Fix Version', 'BA Effort']]
                        elif field_id == 'customfield_10114':  # Dev Manager or Dev Resource field_id
                            if sub_field == 'Dev Manager':
                                df_filtered = df[df[['Dev Manager']].isna().any(axis=1)]
                                df_filtered = df_filtered.fillna('-')
                                df_filtered = make_key_clickable(df_filtered)
                                return df_filtered[['Key', 'Summary', 'Status', 'Assignee', 'Fix Version', 'Dev Manager']]
                            elif sub_field == 'Dev Resource':
                                df_filtered = df[df[['Dev Resource']].isna().any(axis=1)]
                                df_filtered = df_filtered.fillna('-')
                                df_filtered = make_key_clickable(df_filtered)
                                return df_filtered[['Key', 'Summary', 'Status', 'Assignee', 'Fix Version', 'Dev Resource']]
                        elif field_id == 'customfield_10118':  # UAT Manager or UAT Resource field_id
                            if sub_field == 'UAT Manager':
                                df_filtered = df[df[['UAT Manager']].isna().any(axis=1)]
                                df_filtered = df_filtered.fillna('-')
                                df_filtered = make_key_clickable(df_filtered)
                                return df_filtered[['Key', 'Summary', 'Status', 'Assignee', 'Fix Version', 'UAT Manager']]
                            elif sub_field == 'UAT Resource':
                                df_filtered = df[df[['UAT Resource']].isna().any(axis=1)]
                                df_filtered = df_filtered.fillna('-')
                                df_filtered = make_key_clickable(df_filtered)
                                return df_filtered[['Key', 'Summary', 'Status', 'Assignee', 'Fix Version', 'UAT Resource']]
                        elif field_id == 'customfield_10116':  # Test Manager or Test Resource field_id
                            if sub_field == 'Test Manager':
                                df_filtered = df[df[['Test Manager']].isna().any(axis=1)]
                                df_filtered = df_filtered.fillna('-')
                                df_filtered = make_key_clickable(df_filtered)
                                return df_filtered[['Key', 'Summary', 'Status', 'Assignee', 'Fix Version', 'Test Manager']]
                            elif sub_field == 'Test Resource':
                                df_filtered = df[df[['Test Resource']].isna().any(axis=1)]
                                df_filtered = df_filtered.fillna('-')
                                df_filtered = make_key_clickable(df_filtered)
                                return df_filtered[['Key', 'Summary', 'Status', 'Assignee', 'Fix Version', 'Test Resource']]
                            elif sub_field == 'QA Effort':
                                df_filtered = df[df[['QA Effort']].isna().any(axis=1)]
                                df_filtered = df_filtered.fillna('-')
                                df_filtered = make_key_clickable(df_filtered)
                                return df_filtered[['Key', 'Summary', 'Status', 'Assignee', 'Fix Version', 'QA Effort']]
                        else:
                            raise ValueError("Invalid field_id provided")


                    # Generating DataFrames for BA Manager and BA Effort
            df_ba_manager = segregate_dataframe(df, 'customfield_10112', sub_field='BA Manager')
            df_ba_effort = segregate_dataframe(df, 'customfield_10112', sub_field='BA Effort')

                    # Generating DataFrames for Dev Manager and Dev Resource
            df_dev_manager = segregate_dataframe(df, 'customfield_10114', sub_field='Dev Manager')
            df_dev_resource = segregate_dataframe(df, 'customfield_10114', sub_field='Dev Resource')

                    # Generating DataFrames for UAT Manager and UAT Resource
            df_uat_manager = segregate_dataframe(df, 'customfield_10118', sub_field='UAT Manager')
            df_uat_resource = segregate_dataframe(df, 'customfield_10118', sub_field='UAT Resource')

                    # Generating DataFrames for Test Manager and Test Resource
            df_test_manager = segregate_dataframe(df, 'customfield_10116', sub_field='Test Manager')
            df_test_resource = segregate_dataframe(df, 'customfield_10116', sub_field='Test Resource')
            df_qa_effort = segregate_dataframe(df, 'customfield_10116', sub_field='QA Effort')

                    # A function for html styling
            def style_table(html):
                        return f"""
                        <html>
                        <head>
                        <style>
                        table {{
                            width: 100%;
                            border-collapse: collapse;
                        }}
                        th, td {{
                            border: 1px solid #ddd;
                            padding: 8px;
                            text-align: center;  
                            white-space: nowrap; 
                            max-width: 200px;  
                            overflow: hidden; 
                            text-overflow: ellipsis;  
                        }}
                        tr:nth-child(even) {{
                            background-color: #f2f2f2;
                        }}
                        th {{
                            background-color: #4CAF50;
                            color: white;
                            text-align: center;  
                            white-space: nowrap;
                            max-width: 200px;  
                        }}
                        </style>
                        </head>
                        <body>
                        <p>Please fill out the required data in the table below:</p>
                        {html}
                        <p>Sanidhya Mitra</p> 
                        <p>PMO Intern at CoreCard</p>
                        <p>CoreCard India Software Pvt Ltd</p>
                        </body>
                        </html>
                        """
                    
                    # Converting DataFrames to HTML tables
            df_ba_manager_html = style_table(df_ba_manager.to_html(index=False, escape=False))
            df_ba_effort_html = style_table(df_ba_effort.to_html(index=False, escape=False))
            df_dev_manager_html = style_table(df_dev_manager.to_html(index=False, escape=False))
            df_dev_resource_html = style_table(df_dev_resource.to_html(index=False, escape=False))
            df_uat_manager_html = style_table(df_uat_manager.to_html(index=False, escape=False))
            df_uat_resource_html = style_table(df_uat_resource.to_html(index=False, escape=False))
            df_test_manager_html = style_table(df_test_manager.to_html(index=False, escape=False))
            df_test_resource_html = style_table(df_test_resource.to_html(index=False, escape=False))
            df_qa_effort_html = style_table(df_qa_effort.to_html(index=False, escape=False))

                    # Email configurations
            smtp_server = "corecard-com.mail.protection.outlook.com"
            smtp_port = 25
            smtp_user = 'sanidhya.mitra@corecard.com'

                    # Recipients for BA and Dev teams along with the cc
                        # Add as many emails as needed, but they should be in the relevant array
            ba_manager_recipients = [
                        'sanidhya.mitra@corecard.com',
                        # 'kalyani.kharate@corecard.com',
                        # 'manmohan.singh@corecard.com',
                        # 'pawan.linjhara@corecard.com'
                    ]

            ba_effort_recipients = [
                        'sanidhya.mitra@corecard.com',
                        # 'kalyani.kharate@corecard.com'
                    ]
                    
            dev_manager_recipients = [
                        'sanidhya.mitra@corecard.com',
                        # 'kalyani.kharate@corecard.com',
                        # 'manmohan.singh@corecard.com',
                        # 'pawan.linjhara@corecard.com'
                    ]

            dev_resource_recipients = [
                        'sanidhya.mitra@corecard.com',
                        # 'kalyani.kharate@corecard.com',
                        # 'manmohan.singh@corecard.com',
                        # 'pawan.linjhara@corecard.com'
                    ]

            uat_manager_recipients        = [
                        'sanidhya.mitra@corecard.com',
                        # 'kalyani.kharate@corecard.com',
                        # 'manmohan.singh@corecard.com',
                        # 'pawan.linjhara@corecard.com'
                    ]

            uat_resource_recipients = [
                        'sanidhya.mitra@corecard.com',
                        # 'kalyani.kharate@corecard.com',
                        # 'manmohan.singh@corecard.com',
                        # 'pawan.linjhara@corecard.com'
                    ]

            test_manager_recipients = [
                        'sanidhya.mitra@corecard.com',
                        # 'kalyani.kharate@corecard.com',
                        # 'manmohan.singh@corecard.com',
                        # 'pawan.linjhara@corecard.com'
                    ]

            testing_resource_recipients = [
                        'sanidhya.mitra@corecard.com',
                        # 'kalyani.kharate@corecard.com',
                        # 'manmohan.singh@corecard.com',
                        # 'pawan.linjhara@corecard.com'
                    ]

            qa_effort_recipients = [
                        'sanidhya.mitra@corecard.com',
                        # 'kalyani.kharate@corecard.com',
                        # 'manmohan.singh@corecard.com',
                        # 'pawan.linjhara@corecard.com'
                    ]
                    
            cc_email = "sanidhya.mitra@corecard.com"

                    # Function to send email
            def send_email(subject, body, to_emails, cc_emails):
                        msg = MIMEMultipart()
                        msg['From'] = smtp_user
                        msg['To'] = ', '.join(to_emails)
                        msg['Cc'] = ', '.join(cc_emails)
                        msg['Subject'] = subject

                        # Attaching the main message body:
                        msg.attach(MIMEText(body, 'html'))

                        try:
                            with smtplib.SMTP(smtp_server, smtp_port) as server:
                                server.starttls()
                                server.sendmail(smtp_user, to_emails + cc_emails, msg.as_string())
                                print(f"Email sent to {', '.join(to_emails)} with CC to {', '.join(cc_emails)}")
                        except Exception as e:
                            print(f"Failed to send email. Error: {e}")

                    # Sending email to BA team
            print('Sending BA Manager Report...')
            send_email("BA Manager Report", df_ba_manager_html, ba_manager_recipients, [cc_email])
            print('Successfully sent BA Manager email!')

            print('Sending BA Effort Report...')
            send_email("BA Effort Report", df_ba_effort_html, ba_effort_recipients, [cc_email])
            print('Successfully sent BA Effort email!')

                    # Sending email to Dev team
            print('Sending Development Manager Report...')
            send_email("Development Manager Report", df_dev_manager_html, dev_manager_recipients, [cc_email])
            print("Sucessfully sent Development Manager email!")

            print('Sending Development Resource Report...')
            send_email("Development Resource Report", df_dev_resource_html, dev_resource_recipients, [cc_email])
            print("Sucessfully sent Development Resource email!")

                    # Sending email to UAT team
            print('Sending UAT Manager Report...')
            send_email("UAT Manager Report", df_uat_manager_html, uat_manager_recipients, [cc_email])
            print('Successfully sent UAT Manager email!')

            print('Sending UAT Resource Report...')
            send_email("UAT Resource Report", df_uat_resource_html, uat_resource_recipients, [cc_email])
            print('Successfully sent UAT Resource email!')

                    # Sending email to Testing team
            print('Sending Test Manager Report...')
            send_email("Test Manager Report", df_test_manager_html, test_manager_recipients, [cc_email])
            print('Successfully sent Testing Manager email!')

            print('Sending Testing Resource Report...')
            send_email("Test Resource Report", df_test_resource_html, testing_resource_recipients, [cc_email])
            print('Successfully sent Testing Resource email')

            print('Sending QA Effort Report...')
            send_email("QA Report", df_qa_effort_html, qa_effort_recipients, [cc_email])
            print('Successfully sent Testing Resource email')
        else:
            print(f"Failed to fetch data from JIRA API. Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            break

except Exception as e:
    print(f"An error occurred: {e}")