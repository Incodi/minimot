import re
from datetime import datetime
from collections import defaultdict
from importlib.metadata import distributions
import subprocess
import sys

def hms_to_seconds(hms):
    if not hms: return 0
    parts = list(map(float, hms.split(':')))
    if len(parts) == 1: return parts[0]
    elif len(parts) == 2: return parts[0] * 60 + parts[1]
    elif len(parts) == 3: return parts[0] * 3600 + parts[1] * 60 + parts[2]
    return 0

def seconds_to_hms(seconds):
    seconds = int(seconds)
    return f"{seconds//3600:02d}:{(seconds%3600)//60:02d}:{seconds%60:02d}"

def is_valid_date(date_str):
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False

def split_preserving_quotes(text):
    tokens = []
    current = []
    in_quote = False
    in_parentheses = 0
    
    for char in text:
        if char == '"':
            if not in_quote and current and current[-1] == '\\':
                current[-1] = char  
            else:
                in_quote = not in_quote
                current.append(char)
        elif char == '(' and not in_quote:
            in_parentheses += 1
            current.append(char)
        elif char == ')' and not in_quote:
            in_parentheses -= 1
            current.append(char)
        elif char == ' ' and not in_quote and in_parentheses == 0:
            if current:
                tokens.append(''.join(current))
                current = []
        else:
            current.append(char)
    
    if current:
        tokens.append(''.join(current))
    
    return [t.strip() for t in tokens if t.strip()]

def process_search_query(query, mode="general"):
    query = query.strip()
    if not query: 
        return {'include': [], 'exclude': [], 'phrases': [], 'wildcards': [], 'partials': [], 'or_groups': []}
    
    if mode == "specific":
        parts = []
        current = []
        in_quote = False
        
        for char in query:
            if char == '"':
                if not in_quote and current and current[-1] == '\\':
                    current[-1] = char 
                else:
                    in_quote = not in_quote
                    current.append(char)
            elif char == '|' and not in_quote:
                if current:
                    parts.append(''.join(current).strip())
                    current = []
            else:
                current.append(char)
        
        if current: 
            parts.append(''.join(current).strip())
        
        include, wildcards, partials = [], [], []
        for part in parts:
            part = part.strip()
            if part.startswith('"') and part.endswith('"'):
                phrase = part[1:-1].strip()
                if '*' in phrase: 
                    wildcard_pattern = re.escape(phrase).replace(r'\*', r'\b\w+\b')
                    wildcards.append(wildcard_pattern)
                else: 
                    include.append(re.escape(phrase))
            elif '+' in part or '*' in part:
                pattern = re.escape(part).replace(r'\+', r'\w*').replace(r'\*', r'\w*')
                partials.append(pattern)
            else: 
                include.append(re.escape(part))
        
        return {'include': include, 'wildcards': wildcards, 'partials': partials}
    
    or_groups = []
    current = []
    in_quote = False
    
    for char in query:
        if char == '"':
            if not in_quote and current and current[-1] == '\\':
                current[-1] = char  
            else:
                in_quote = not in_quote
                current.append(char)
        elif char == '|' and not in_quote:
            if current:
                or_groups.append(''.join(current).strip())
                current = []
        else:
            current.append(char)
    
    if current: 
        or_groups.append(''.join(current).strip())
    
    result = {
        'include': [], 'exclude': [], 'phrases': [], 'wildcards': [], 'partials': [], 'or_groups': []
    }
    
    for group in or_groups:
        group_result = {
            'include': [], 'exclude': [], 'phrases': [], 'wildcards': [], 'partials': []
        }
        
        remaining = []
        for token in re.split(r'("[^"]*")', group):
            if token.startswith('"') and token.endswith('"'):
                phrase = token[1:-1].strip()
                if phrase.startswith('-'):
                    group_result['exclude'].append(('phrase', phrase[1:]))
                else:
                    group_result['phrases'].append(phrase)
            elif token.strip():
                remaining.append(token.strip())
        
        tokens = split_preserving_quotes(' '.join(remaining))
        
        for token in tokens:
            if token.startswith('(') and token.endswith(')'):
                inner = token[1:-1].strip()
                if inner.startswith('-'):
                    for term in split_preserving_quotes(inner[1:]):
                        if term.startswith('"') and term.endswith('"'):
                            group_result['exclude'].append(('phrase', term[1:-1]))
                        else:
                            group_result['exclude'].append(('term', term.lower()))
                else:
                    for term in split_preserving_quotes(inner):
                        if term.startswith('"') and term.endswith('"'):
                            group_result['phrases'].append(term[1:-1])
                        else:
                            group_result['include'].append(term.lower())
            elif token.startswith('-'):
                term = token[1:]
                if term.startswith('"') and term.endswith('"'):
                    group_result['exclude'].append(('phrase', term[1:-1]))
                else:
                    group_result['exclude'].append(('term', term.lower()))
            elif '*' in token:
                group_result['wildcards'].append(token.lower())
            elif '+' in token:
                group_result['partials'].append(token.lower())
            else:
                group_result['include'].append(token.lower())
        
        result['or_groups'].append(group_result)
    
    return result

def matches_search_terms(text, terms, mode="general"):
    text = text.lower()
    
    if mode == "specific":
        matches = []
        for term in terms['include']:
            matches.extend(re.findall(r'\b' + term + r'\b', text, re.IGNORECASE))
        for wildcard in terms['wildcards']:
            matches.extend(re.findall(wildcard, text, re.IGNORECASE))
        for partial in terms['partials']:
            matches.extend(re.findall(r'\b' + partial + r'\b', text, re.IGNORECASE))
        return matches
    
    if not terms.get('or_groups'):
        return check_single_group(text, terms)
    
    for group in terms['or_groups']:
        if check_single_group(text, group):
            return True
    return False

def check_single_group(text, group):
    for phrase in group['phrases']:
        if phrase not in text:
            return False
    
    for wildcard in group['wildcards']:
        pattern = wildcard.replace('*', r'\w*')
        if not re.search(r'\b' + pattern + r'\b', text):
            return False
    
    for partial in group['partials']:
        pattern = partial.replace('+', r'\w*')
        if not re.search(r'\b' + pattern + r'\b', text):
            return False
    
    for term in group['include']:
        if not re.search(r'\b' + re.escape(term) + r'\b', text):
            return False
    
    for exclude_type, term in group['exclude']:
        if exclude_type == 'phrase':
            if term in text:
                return False
        else: 
            if re.search(r'\b' + re.escape(term) + r'\b', text):
                return False
    
    return True  

def check_requirements():
    required = {'wordcloud', 'matplotlib', 'pillow', 'numpy', 'pytube', 'webvtt-py'}
    installed = {dist.metadata['Name'].lower() for dist in distributions()}
    missing = required - installed
    
    if missing:
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', *missing])
            return True
        except Exception as e:
            raise Exception(f"Failed to install: {str(e)}")
    return True

def extract_video_id(filename):
    matches = re.findall(r'\[([^\]]+)\]', filename)
    return matches[-1] if matches else None