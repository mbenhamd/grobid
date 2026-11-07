#!/usr/bin/env python3
"""Validate migration-kit consistency. Passing is not a runtime parity result."""
from __future__ import annotations
import argparse
import ast
import csv
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import urllib.parse


class KitError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise KitError(message)


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f'Duplicate JSON key: {key}')
        result[key] = value
    return result


def read_json(file):
    return json.loads(file.read_text(), object_pairs_hook=unique_pairs,
                      parse_constant=lambda x: (_ for _ in ()).throw(KitError(f'Invalid JSON number: {x}')))


def validate_graph(tasks):
    require(isinstance(tasks, list) and tasks, 'Task graph is empty')
    by_id = {}
    for task in tasks:
        ident = task.get('id')
        require(isinstance(ident, str) and re.fullmatch(r'T[0-9]{3}', ident), 'Invalid task ID')
        require(ident not in by_id, f'Duplicate task {ident}')
        require(isinstance(task.get('depends_on'), list), f'{ident}: missing dependency list')
        require(task.get('acceptance') and task.get('owned_paths') and task.get('skill'), f'{ident}: incomplete task contract')
        by_id[ident] = task
    visited, active = set(), set()
    def visit(ident):
        require(ident in by_id, f'Unknown dependency {ident}')
        require(ident not in active, f'Dependency cycle at {ident}')
        if ident in visited:
            return
        active.add(ident)
        for dependency in by_id[ident]['depends_on']:
            visit(dependency)
        active.remove(ident)
        visited.add(ident)
    for ident in by_id:
        visit(ident)
    return by_id


def check(root, upstream=None):
    root = Path(root).resolve()
    required = ['AGENTS.md', 'migration/START_HERE.md', 'migration/LAUNCH_PROMPT.md',
                'migration/ARCHITECTURE.md', 'migration/TEST_STRATEGY.md',
                'migration/PERFORMANCE.md', 'migration/AUTONOMOUS_RUNBOOK.md',
                'migration/contracts/upstream-lock.json', 'migration/contracts/scope.json',
                'migration/contracts/api-inventory.json', 'migration/FEATURE_MATRIX.csv',
                'migration/audit/CORE_AUDIT.md', 'migration/audit/API_AUDIT.md',
                'migration/audit/TESTING_AUDIT.md', 'migration/state/HANDOFF.md',
                'migration/tools/parity.py', 'migration/tools/taskctl.py']
    for name in required:
        require((root/name).is_file(), f'Missing file: {name}')
    json_files = list((root/'migration').rglob('*.json'))
    for file in json_files:
        if 'evidence' not in file.relative_to(root).parts:
            read_json(file)
    plan = read_json(root/'migration/plans/tasks.json')
    tasks = validate_graph(plan.get('tasks'))
    state = read_json(root/'migration/state/task-state.json')
    require(set(tasks) == set(state.get('tasks', {})), 'Plan/state task IDs differ')
    statuses = {'pending','running','submitted','done','blocked','failed'}
    for ident, record in state['tasks'].items():
        require(record.get('status') in statuses, f'Invalid state for {ident}')
    skill_files = list((root/'.agents/skills').glob('*/SKILL.md'))
    names = set()
    for file in skill_files:
        text = file.read_text()
        match = re.match(r'---\nname: ([a-z0-9-]+)\ndescription: (.+)\n---\n', text)
        require(match is not None, f'Invalid skill frontmatter: {file}')
        name = match[1]
        require(name == file.parent.name and name not in names and len(name)<64, f'Invalid skill name: {name}')
        require(len(match[2])>30 and len(text.splitlines())<500, f'Incomplete/oversized skill: {name}')
        names.add(name)
    for ident, task in tasks.items():
        require(task['skill'] in names, f'{ident}: missing skill {task["skill"]}')
    adrs = list((root/'migration/adr').glob('[0-9]*.md'))
    require(len(adrs)>=16, 'Missing architecture decisions')
    with (root/'migration/FEATURE_MATRIX.csv').open(newline='') as stream:
        features=list(csv.DictReader(stream))
    require(bool(features), 'Feature coverage matrix is empty')
    ids=set()
    for row in features:
        require(row.get('id') and row['id'] not in ids, 'Duplicate/missing feature ID')
        require(row.get('task_id') in tasks, f'{row.get("id")}: unknown task')
        require(row.get('status') in {'not_verified','captured','implemented','verified','blocked','deviation'}, 'Invalid feature state')
        ids.add(row['id'])
    api=read_json(root/'migration/contracts/api-inventory.json')
    handlers=api.get('endpoints',[])
    require(handlers and len({e['id'] for e in handlers})==len(handlers), 'Missing/duplicate API handlers')
    require(api.get('commit')==plan.get('upstream_commit'), 'API and task source pins differ')
    require(api['counts']['resource_handlers']==len(handlers), 'API handler count differs')
    require(api['counts']['distinct_resource_paths']==len({e['path'] for e in handlers}), 'API path count differs')
    require(api['counts']['method_path_pairs']==len({(e['method'],e['path']) for e in handlers}), 'API method/path count differs')
    for endpoint in handlers:
        require('API-'+endpoint['id'] in ids, f'Missing feature coverage row for {endpoint["id"]}')
        require(endpoint.get('parameters') is not None and endpoint.get('source'), 'Incomplete API contract')
    for file in (root/'migration/tools').rglob('*.py'):
        ast.parse(file.read_text(), filename=str(file))
    spec=importlib.util.spec_from_file_location('kit_parity_validator', root/'migration/tools/parity.py')
    parity=importlib.util.module_from_spec(spec);spec.loader.exec_module(parity)
    suites=list((root/'migration/cases').glob('*.json'))
    require(suites, 'Missing starter request suites')
    for file in suites:
        parity.validate_suite(read_json(file))
    if upstream:
        tree=subprocess.check_output(['git','-C',str(upstream),'ls-tree','-r','--name-only',plan['upstream_commit']],text=True).splitlines()
        available=set(tree)
        prefix='https://github.com/grobidOrg/grobid/blob/'+plan['upstream_commit']+'/'
        links=set()
        source_docs=list((root/'migration').rglob('*.md'))+list((root/'migration/contracts').glob('*.json'))
        source_docs += [root/'migration/plans/tasks.json',root/'migration/FEATURE_MATRIX.csv']
        for file in source_docs:
            for link in re.findall(r'https://github\.com/grobidOrg/grobid/blob/[^\s)"<>,]+',file.read_text()):
                if link.startswith(prefix):
                    links.add(urllib.parse.unquote(link[len(prefix):].split('#')[0]))
        for path in links:
            require(path in available or any(p.startswith(path.rstrip('/')+'/') for p in available),f'Unknown pinned source anchor: {path}')
    return {'status':'kit_structure_valid','runtime_parity_verified':False,
            'tasks':len(tasks),'skills':len(names),'adrs':len(adrs),'feature_rows':len(features),
            'api_handlers':len(handlers),
            'starter_suites':len(suites),'json_files_parsed':len(json_files),
            'note':'Runtime assets, baseline capture, Rust implementation and release gates remain separate tasks.'}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2])
    parser.add_argument('--upstream',type=Path,help='Optional local pinned source checkout for source-anchor validation')
    args=parser.parse_args(argv)
    try:
        print(json.dumps(check(args.root,args.upstream),indent=2));return 0
    except (KitError,OSError,ValueError,KeyError,TypeError,SyntaxError,subprocess.SubprocessError) as exc:
        print(json.dumps({'status':'error','error':str(exc)}));return 2


if __name__=='__main__':
    sys.exit(main())
