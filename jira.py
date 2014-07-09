#!/usr/bin/env python

import argparse, requests, json, string, sys, datetime, math
from os.path import expanduser

resource_search = "/rest/api/2/search"
resource_issue = "/rest/api/2/issue/"
resource_project = "/rest/api/2/project"

home_dir = expanduser('~')
config_path = home_dir + "/.jira/jira.config"
log_dir = home_dir + "/.jira/log/"

log_date_format = "%Y-%m-%d %H:%M:%S"

class bcolors:
    HEADER = '\033[1;37;44m' 
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD_CYAN = '\033[1;36m'

def human_date_difference(now, then):
    print now

def log_transition(issueKey, transition):
    log_file = open(log_dir + issueKey + '.log', 'a')
    log_file.write(transition + '@' + datetime.datetime.now().strftime(log_date_format) + '\n')
    log_file.close()

def time_logged(issueKey):
    start = None
    acc = 0;
    log_file = open(log_dir + issueKey + '.log', 'r')
    for line in log_file:
        parts = line.split('@')
        transition = parts[0]
        dateStr = parts[1].strip()
        if start is None and transition == 'Start':
            start = datetime.datetime.strptime(dateStr, log_date_format)
        elif transition == 'Stop':
            end = datetime.datetime.strptime(dateStr, log_date_format)
            elapsed_time = end - start
            acc += elapsed_time.total_seconds()
            start = None
    log_file.close()
    if start != None:
        end = datetime.datetime.now()
        elapsed_time = end - start
        acc += elapsed_time.total_seconds()
    return acc

def print_time_logged(issueKey):
    logged = time_logged(issueKey)
    print '%d minutes, %d seconds logged for issue %s' % (math.floor(logged / 60), logged % 60, issueKey)

def load_config():
    import ConfigParser
    Config = ConfigParser.ConfigParser()
    Config.read(config_path)
    username = Config.get('Authentication', 'username')
    password = Config.get('Authentication', 'password')
    endpoint = Config.get('Authentication', 'endpoint')
    return {'username' : username, 'password' : password, 'endpoint' : endpoint }

def print_issue(issue):
    sys.stdout.write(bcolors.HEADER)
    print '{project} / {key}'.format(project=issue['fields']['project']['name'], key=issue['key'])
    sys.stdout.write(bcolors.ENDC)
    print
    print issue['fields']['summary'] + '\033[0m' 
    print
    print string.ljust('Type', 10) + issue['fields']['issuetype']['name']
    print string.ljust('Priority', 10) + issue['fields']['priority']['name']
    print string.ljust('Status', 10) + issue['fields']['status']['name']
    print
    print issue['fields']['description']
    print

def print_issue_oneline_header():
    print bcolors.OKGREEN + string.ljust('Key', 8) + 'Summary' + bcolors.ENDC

def print_issue_oneline(issue):
    print bcolors.OKBLUE + string.ljust(issue['key'], 8) + bcolors.ENDC + issue['fields']['summary']

def print_comment_oneline(comment):
    print comment['body']
    print bcolors.BOLD_CYAN + comment['author']['displayName'] + bcolors.ENDC

def get_issues():
    search_url = config['endpoint'] + "/rest/api/2/search?jql=status+!%3D+%22closed%22+and+assignee+%3D+" + config['username'] + '&fields=summary'
    r = requests.get(search_url, auth=(config['username'], config['password']), verify=False)
    return r.json()

def get_issue(key):
    issue_url = config['endpoint'] + resource_issue + key
    r = requests.get(issue_url, auth=(config['username'], config['password']), verify=False)
    return r.json()

def get_projects():
    project_url = config['endpoint'] + resource_project
    r = requests.get(project_url, auth=(config['username'], config['password']), verify=False)
    return r.json()

def get_comments(key):
    comment_url = config['endpoint'] + resource_issue + key + '/comment'
    r = requests.get(comment_url, auth=(config['username'], config['password']), verify=False)
    return r.json()

def start_progress(key):
    payload = {"transition" : {"id" : "4"}}
    transition_url = config['endpoint'] + resource_issue + key + '/transitions'
    headers = {'content-type': 'application/json'}
    r = requests.post(transition_url, data=json.dumps(payload), headers=headers, auth=(config['username'], config['password']), verify=False)
    log_transition(key, 'Start')

def stop_progress(key):
    payload = {"transition" : {"id" : "301"}}
    transition_url = config['endpoint'] + resource_issue + key + '/transitions'
    headers = {'content-type': 'application/json'}
    r = requests.post(transition_url, data=json.dumps(payload), headers=headers, auth=(config['username'], config['password']), verify=False)
    log_transition(key, 'Stop')

def show_issue(key):
    issue = get_issue(key)
    print_issue(issue)

def show_comments(key):
    comments = get_comments(key)
    print bcolors.HEADER + str(comments['total']) + ' comments on  ' + key + bcolors.ENDC
    for comment in comments['comments']:
        print_comment_oneline(comment)

def list_issues():
    issues = get_issues()
    print bcolors.HEADER + str(issues['total']) + ' open issues assigned to ' + config['username'] + bcolors.ENDC
    print_issue_oneline_header()
    for issue in issues['issues']:
        print_issue_oneline(issue)

def print_project_oneline_header():
    print bcolors.OKGREEN + string.ljust('Key', 8) + 'Name' + bcolors.ENDC

def print_project_oneline(project):
    print bcolors.OKBLUE + string.ljust(project['key'], 8) + bcolors.ENDC + project['name']

def list_projects():
    projects = get_projects()
    print bcolors.HEADER + 'Projects visible to ' + config['username'] + bcolors.ENDC
    for project in projects:
        print_project_oneline(project)

def comment_on_issue(issue_key, comment):
    payload = {"body" : comment}
    comment_url = config['endpoint'] + resource_issue + issue_key + '/comment'
    headers = {'content-type': 'application/json'}
    r = requests.post(comment_url, data=json.dumps(payload), headers=headers, auth=(config['username'], config['password']), verify=False)
    if r.status_code <> 201:
        print bcolors.WARNING + 'Commenting failed' + bcolors.ENDC

def parse_user_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("issuekey", nargs="?")
    parser.add_argument("--list", help="List issues assigned to you.", action="store_true")
    parser.add_argument("--projects", help="List projects visible to you.", action="store_true")
    parser.add_argument("--comments", help="List comments on an issue.", action="store_true")
    parser.add_argument("--start", help="Start Progress", action="store_true")
    parser.add_argument("--stop", help="Stop Progress", action="store_true")
    parser.add_argument("--time", help="Show time logged", action="store_true")
    parser.add_argument("-c", help="Comment on issue.", action="store", dest="comment_body")
    return parser.parse_args()

config = load_config()

args = parse_user_args()

if args.list:
    list_issues()

if args.projects:
    list_projects()

if args.issuekey:
    if args.start:
        start_progress(args.issuekey)
    elif args.stop:
        stop_progress(args.issuekey)
    if args.comment_body:
        comment_on_issue(args.issuekey, args.comment_body)
    elif args.comments:
        show_comments(args.issuekey)
    elif args.time:
        print_time_logged(args.issuekey)
    else:
        show_issue(args.issuekey)
