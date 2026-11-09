"""Bounded non-interactive calls with durable logs and conservative tool classification."""
from __future__ import annotations
import json
import os
from pathlib import Path
import subprocess
import threading
import time
import re
from process_guard import identity

TERMINAL = {'valid', 'format_failure', 'tool_contaminated', 'final_missing', 'quota_interrupted'}
TOOL_TYPES = {'function_call', 'custom_tool_call', 'tool_call', 'mcp_tool_call',
              'command_execution', 'file_change', 'web_search', 'web_search_call',
              'request_user_input', 'request_user_input_call'}
DENIALS = {
    'request_user_input is unavailable in Default mode',
    'request_user_input is not available in non-interactive mode',
    'request_user_input is unavailable in non-interactive mode',
    'code-mode host is disabled',
}

def append(path, obj):
    with path.open('a', encoding='utf-8') as f:
        f.write(json.dumps(obj, ensure_ascii=False) + '\n'); f.flush(); os.fsync(f.fileno())

def exact_denial(value):
    if isinstance(value, dict):
        # Only a single recognized error field; no unnoticed results or file content.
        if set(value) == {'error'}: return exact_denial(value['error'])
        if set(value) == {'message'}: return exact_denial(value['message'])
        return False
    if not isinstance(value, str): return False
    try:
        parsed = json.loads(value)
    except ValueError: parsed = None
    if isinstance(parsed, dict): return exact_denial(parsed)
    value = value.strip()
    if value.startswith('Error: '): value = value[7:]
    return value.rstrip('.') in DENIALS

def read_events(text):
    events, malformed = [], 0
    for line in text.splitlines():
        if not line.strip(): continue
        try: event = json.loads(line)
        except ValueError: malformed += 1; continue
        if isinstance(event, dict): events.append(event)
        else: malformed += 1
    return events, malformed

def inspect_tools(stdout, stderr, wire_items=()):
    events, malformed = read_events(stdout)
    calls, evidence = {}, []
    items=[]
    for e in events:
        item = e.get('item') or e.get('payload')
        if isinstance(item, dict): items.append((item,'stdout'))
        if e.get('type') in TOOL_TYPES or e.get('type') in ('function_call_output','custom_tool_call_output'):
            items.append((e,'stdout'))
        if e.get('method') in ('item/tool/requestUserInput','tool/requestUserInput'):
            p=e.get('params',{})
            items.append(({'type':'request_user_input','id':p.get('itemId',str(e.get('id'))),'name':'request_user_input'},'stdout'))
    for item in wire_items: items.append((item,'wire'))
    outputs=[]
    for item,source in items:
        typ=item.get('type','')
        if typ in ('function_call_output','custom_tool_call_output'):
            outputs.append((item,source)); continue
        if typ not in TOOL_TYPES: continue
        key=item.get('call_id') or item.get('id') or f'anonymous-{len(calls)}'
        name=item.get('name') or item.get('tool') or typ
        if isinstance(name,dict): name=name.get('name','unknown')
        call=calls.setdefault(key,{'id':key,'name':name,'state':'unknown','sources':[]})
        if source not in call['sources']:call['sources'].append(source)
        value=item.get('error') or item.get('output') or item.get('result')
        if exact_denial(value):call['state']='blocked'
        elif value is not None or item.get('status') in ('completed','succeeded'):
            call['state']='executed_or_unknown'
        if str(name).endswith('request_user_input') and call['state']=='unknown':call['state']='pending_question'
    for item,source in outputs:
        key=item.get('call_id') or item.get('id')
        call=calls.setdefault(key or f'orphan-{len(calls)}',{'id':key,'name':'unknown','state':'unknown','sources':[]})
        if source not in call['sources']:call['sources'].append(source)
        call['state']='blocked' if exact_denial(item.get('output')) else 'executed_or_unknown'
    for n,line in enumerate(stderr.splitlines()):
        # Match actual preflight router output, not model commentary or a general startup warning.
        unsupported=re.search(r'error=unsupported call: ([A-Za-z_][A-Za-z0-9_.]*)\s*$',line)
        if 'codex_core::tools::router:' in line and 'dispatch_tool_call' in line and unsupported:
            call_id=re.search(r'\bcall_id="?([^"\s}]+)',line)
            tool_name=re.search(r'\btool_name="?([^"\s}]+)',line)
            if call_id and tool_name and tool_name.group(1)==unsupported.group(1):
                evidence.append({'id':call_id.group(1),'name':tool_name.group(1),'state':'blocked',
                                 'sources':['stderr'],'reason':'unsupported_tool_dispatch',
                                 'runtime_dispatch_observed':True})
            else:
                evidence.append({'id':call_id.group(1) if call_id else f'stderr-{n}',
                                 'name':tool_name.group(1) if tool_name else 'unknown','state':'unknown',
                                 'sources':['stderr'],'reason':'unsupported_tool_denial_without_matching_identity'})
        elif 'codex_core::tools::router:' in line and 'error=code-mode host is disabled' in line:
            call_id=re.search(r'\bcall_id="?([^"\s}]+)',line)
            tool_name=re.search(r'\btool_name="?([^"\s}]+)',line)
            evidence.append({'id':call_id.group(1) if call_id else f'stderr-{n}',
                             'name':tool_name.group(1) if tool_name else 'code_mode_router',
                             'state':'blocked','sources':['stderr'],'reason':'code_mode_host_disabled',
                             'runtime_dispatch_observed':bool(call_id and tool_name and 'dispatch_tool_call' in line)})
        elif ('codex_core::tools::' in line and 'request_user_input' in line
              and not ('codex_core::tools::parallel:' in line and 'event.name="codex.tool_call"' in line)):
            # Completion telemetry is correlated by call ID below. Its
            # execution_started flag is not an outstanding question request.
            tail=line.split('error=',1)[-1].strip()
            if exact_denial(tail): state='blocked'
            elif any(x in line.lower() for x in ('pending','waiting','started')):state='pending_question'
            else:state='unknown'
            call_id=re.search(r'\bcall_id="?([^"\s}]+)',line)
            evidence.append({'id':call_id.group(1) if call_id else f'stderr-{n}','name':'request_user_input','state':state,'sources':['stderr']})
    for n,line in enumerate(stderr.splitlines()):
        if 'codex_core::tools::' not in line or 'event.name="codex.tool_call"' not in line:continue
        call_id=re.search(r'\bcall_id="?([^"\s}]+)',line);tool_name=re.search(r'\btool_name="?([^"\s}]+)',line)
        if not call_id or not tool_name:
            evidence.append({'id':f'stderr-completion-{n}','name':'unidentified_runtime_tool','state':'unknown','sources':['stderr']});continue
        ident=call_id.group(1)
        if ident in calls or any(r['id']==ident for r in evidence):continue
        # Runtime 'execution_started=true' also appears on denied dispatches. It proves an
        # attempt, not successful tool execution. Without matching denial evidence, exclude it.
        evidence.append({'id':ident,'name':tool_name.group(1),'state':'unknown','sources':['stderr'],'reason':'runtime_tool_completion_without_verified_denial'})
    # Evidence records are not asserted to be distinct attempts across different logging channels.
    return {'calls':list(calls.values()),'stderr_evidence':evidence,'malformed_event_lines':malformed,
            'coverage':'recognized events and allowlisted stderr patterns only'}

def assess_input_probe(stdout,stderr,exit_code,timed_out,*,model_metadata=None,config=None,wire_items=()):
    """Probe success requires runtime evidence, never model self-report or a startup warning."""
    result=classify(stdout,stderr,exit_code,timed_out,lambda s:bool(s.strip()),wire_items)
    records=result['tools']['calls']+result['tools']['stderr_evidence']
    if result['state']!='valid':
        return {'passed':False,'status':'failed_or_inconclusive','call_result':result}
    direct=[r for r in records if r['name'].endswith('request_user_input') and r['state']=='blocked']
    if direct:
        return {'passed':True,'status':'verified_input_tool_rejection','evidence_ids':[r['id'] for r in direct],
                'scope':'observed request_user_input attempts only','call_result':result}
    entry=[r for r in records if r.get('runtime_dispatch_observed') and r.get('name')=='exec'
           and r.get('reason')=='code_mode_host_disabled' and r.get('state')=='blocked']
    if (entry and (model_metadata or {}).get('tool_mode')=='code_mode_only'
            and (config or {}).get('features',{}).get('code_mode_host') is False):
        return {'passed':True,'status':'verified_code_mode_entrypoint_blocked','evidence_ids':[r['id'] for r in entry],
                'scope':'code-mode entrypoint rejected before the nested input tool could run; not a direct input-tool rejection',
                'call_result':result}
    return {'passed':False,'status':'unverified_no_runtime_evidence','call_result':result}

def classify(stdout, stderr, exit_code, timed_out, validator, wire_items=()):
    tools=inspect_tools(stdout,stderr,wire_items)
    findings=tools['calls']+tools['stderr_evidence']
    pending=any(x['state']=='pending_question' for x in findings)
    unverified=any(x['state']!='blocked' for x in findings)
    events,_=read_events(stdout)
    msgs=[e['item'].get('text','') for e in events if e.get('type')=='item.completed' and e.get('item',{}).get('type')=='agent_message']
    final=msgs[-1] if msgs else ''
    terminals=[e.get('type') for e in events if e.get('type') in ('turn.completed','turn.failed')]
    completed=bool(terminals and terminals[-1]=='turn.completed')
    result={'tools':tools,'pending_question':pending,'blocked_evidence':any(x['state']=='blocked' for x in findings),'final_output':final,
            'completed_turn_observed':completed}
    if unverified:
        state,reason='tool_contaminated','pending_question_timeout' if timed_out and pending else 'executed_or_unverified_tool'
    elif tools['malformed_event_lines']:
        state,reason='tool_contaminated','incomplete_observability'
    elif completed:
        state,reason=('valid','completed_turn_validated') if validator(final) else ('format_failure','completed_turn_invalid_output')
    elif timed_out:
        state,reason='retryable_failure','timeout'
    elif exit_code != 0 or any(e.get('type')=='turn.failed' for e in events):
        state,reason='retryable_failure','process_or_service_error'
    elif validator(final):state,reason='valid','validated_output'
    else:state,reason='format_failure','invalid_output'
    return {**result,'state':state,'reason':reason,'retry_allowed':state=='retryable_failure'}

def run_attempt(command, prompt, *, cwd, env, directory, timeout=600, validator=lambda _:True, redact=lambda s:s,cleanup_grace_seconds=5):
    directory=Path(directory); directory.mkdir(parents=True,exist_ok=False)
    started=time.time(); tick=time.monotonic()
    append(directory/'lifecycle.jsonl',{'event':'started','unix':started,'timeout_seconds':timeout})
    p=subprocess.Popen(command,cwd=cwd,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                       creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
    append(directory/'lifecycle.jsonl',{'event':'spawned','unix':time.time(),'process':identity(p.pid)})
    terminal_seen={'at':None,'type':None}
    def drain(pipe,path):
        with path.open('w',encoding='utf-8') as f:
            for line in iter(pipe.readline,b''):
                decoded=redact(line.decode('utf-8',errors='replace'));f.write(decoded);f.flush()
                if path.name=='events.jsonl':
                    try:event=json.loads(decoded)
                    except ValueError:event={}
                    if event.get('type') in ('turn.completed','turn.failed'):
                        terminal_seen.update(at=time.monotonic(),type=event['type'])
            os.fsync(f.fileno())
        pipe.close()
    readers=[threading.Thread(target=drain,args=(p.stdout,directory/'events.jsonl'),daemon=True),
             threading.Thread(target=drain,args=(p.stderr,directory/'stderr.txt'),daemon=True)]
    for t in readers:t.start()
    def write_and_close():
        try:p.stdin.write(prompt.encode('utf-8'));p.stdin.flush()
        except (BrokenPipeError,OSError):pass
        finally:
            try:p.stdin.close()
            except OSError:pass
            append(directory/'lifecycle.jsonl',{'event':'stdin_closed','unix':time.time()})
    writer=threading.Thread(target=write_and_close,daemon=True);writer.start()
    timed_out=False;cleanup_terminated=False
    while p.poll() is None:
        elapsed=time.monotonic()-tick
        terminal_age=time.monotonic()-terminal_seen['at'] if terminal_seen['at'] is not None else None
        if elapsed>=timeout or (terminal_age is not None and terminal_age>=cleanup_grace_seconds):
            cleanup_terminated=terminal_age is not None
            timed_out=not cleanup_terminated
            if os.name=='nt':subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],capture_output=True,timeout=15)
            else:p.kill()
            p.wait(timeout=15);break
        try:p.wait(timeout=min(.25,max(.01,timeout-elapsed)))
        except subprocess.TimeoutExpired:pass
    writer.join(5)
    for t in readers:t.join(5)
    if writer.is_alive() or any(t.is_alive() for t in readers):raise RuntimeError('Incomplete process/log shutdown')
    stdout=(directory/'events.jsonl').read_text(encoding='utf-8')
    stderr=(directory/'stderr.txt').read_text(encoding='utf-8')
    result=classify(stdout,stderr,p.returncode,timed_out,validator)
    result.update(exit_code=p.returncode,timed_out=timed_out,post_turn_cleanup_terminated=cleanup_terminated,seconds=round(time.monotonic()-tick,3))
    append(directory/'lifecycle.jsonl',{'event':'ended','unix':time.time(),**result})
    (directory/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return result

def run_call(command,prompt,*,directory,max_attempts=4,retry_delays=(30,120,480),**kwargs):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    saved=directory/'result.json'
    if saved.exists():
        old=json.loads(saved.read_text(encoding='utf-8'))
        if old['state'] in TERMINAL:return {**old,'reused_terminal_result':True}
    existing=sorted(directory.glob('attempt-*'))
    if existing:raise RuntimeError('Uncommitted attempts require recovery review; never silently replay them')
    result=None
    for number in range(1,max_attempts+1):
        result=run_attempt(command,prompt,directory=directory/f'attempt-{number:02d}',**kwargs)
        result['attempts']=number
        if not result['retry_allowed']:break
        if number<max_attempts:time.sleep(retry_delays[min(number-1,len(retry_delays)-1)])
    if result['retry_allowed']:
        result.update(state='pending_supplement',retry_allowed=False)
    saved.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return result
