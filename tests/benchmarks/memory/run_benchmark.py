#!/usr/bin/env python3
"""Echoloom memory A/B harness. Standard library only; all inputs synthetic.

IMPORTANT: the program reports heuristics, not LLM-graded semantic correctness.
"""
import argparse
import csv
import json
import os
import re
import sys
import time
import uuid
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPCookieProcessor, Request, build_opener
from http.cookiejar import CookieJar

HERE = Path(__file__).resolve().parent


class APIError(RuntimeError):
    pass


class Client:
    def __init__(self, base, timeout=180):
        parsed = urlparse(base)
        if parsed.scheme != 'http' or parsed.hostname not in ('localhost','127.0.0.1','::1'):
            raise ValueError('For safety this runner only connects to local HTTP servers (localhost/127.0.0.1).')
        self.base = base.rstrip('/')
        self.timeout = timeout
        self.opener = build_opener(HTTPCookieProcessor(CookieJar()))

    def request(self, method, path, payload=None):
        raw = json.dumps(payload).encode() if payload is not None else None
        request = Request(self.base + path, data=raw, method=method,
                          headers={'Content-Type':'application/json', 'Accept':'application/json'})
        try:
            with self.opener.open(request, timeout=self.timeout) as response:
                data=response.read()
                return json.loads(data) if data else None
        except HTTPError as exc:
            detail=exc.read().decode('utf-8','replace')[:600]
            raise APIError(f'{method} {path}: HTTP {exc.code}: {detail}') from exc
        except (URLError, TimeoutError) as exc:
            raise APIError(f'{method} {path}: {exc}') from exc

    def get(self, path): return self.request('GET',path)
    def post(self, path, data): return self.request('POST',path,data)


def u(): return str(uuid.uuid4())


def login(client,args):
    state=client.get('/api/account/session')
    if not state.get('setup_required'):
        if not args.username or not args.password:
            raise APIError('Existing account detected. Pass --username and --password to log in. Password can be provided via ECHOLOOM_TEST_PASSWORD environment variable.')
        client.post('/api/account/login', {'username':args.username, 'password':args.password})
    else:
        if not args.create_account:
            raise APIError('No account exists. Runner will NOT create the first admin automatically. Set up your account in the app first, or pass --create-account --username ... --password ... explicitly.')
        if not args.username or not args.password:
            raise APIError('--create-account requires --username and --password')
        client.post('/api/account/register',{'username':args.username,'password':args.password})
    assert client.get('/api/account/session').get('authenticated'), 'Login failed'


def save_json(path,obj):
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')


def write_rows(path,rows):
    if not rows:return
    keys=list(dict.fromkeys(k for x in rows for k in x))
    with path.open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)


def reply(messages):
    if isinstance(messages,list):
        for m in reversed(messages):
            if m.get('role')=='assistant':return m.get('content','')
    raise APIError('Chat POST did not return assistant messages')


def question_score(question,answer):
    """Conservative keyword coverage; unknown responses require manual inspection."""
    a=answer.lower()
    if question['category']=='unknown':
        if re.search(r"(don't know|do not know|not (been )?(told|specified|provided|mentioned)|unknown|can't (tell|know)|no information|不(知道|清楚)|没(有|提到)|无法确定)",a):
            # Detect common definite hallucination phrases; final approval remains manual.
            return 2,'uncertainty_detected_manual_check'
        return 0,'no_clear_uncertainty'
    covered=sum(any(word in a for word in group) for group in question['hints'])
    total=len(question['hints'])
    if covered==total:return 2,'all_keywords_present_manual_check'
    if covered>0:return 1,'partial_keywords_manual_check'
    return 0,'no_keywords_manual_check'


def make_chat_character(client):
    char=client.post('/api/characters/generate',{'description':
        'A warm, thoughtful, patient adult companion named Rowan. Speak English. The person you chat with is a new acquaintance. '
        'Do not invent details about the user, and acknowledge when you cannot recall something. '
        'This is an isolated, fictional memory benchmark. No user profile facts are supplied here.'})
    return char['id'],char['conversation_id']


def new_conv(client,cid):
    return client.post(f'/api/characters/{cid}/conversations',{})['id']


def send(client,conv,msg):
    return reply(client.post(f'/api/conversations/{conv}/messages',{'content':msg,'request_id':u()}))


def filler(i):
    # Deliberately neutral distractors: do not reintroduce any personal-memory answers.
    return (f'Unrelated reasoning exercise {i}: a cart contains {i%7+2} neutral boxes. '
            'Explain one general method for counting them. Please do not discuss my personal life.')


def wait_for_chat_index(client, cid, timeout):
    """Do not evaluate Mem0 ON before committed user turns are indexed."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        status = client.get(f'/api/characters/{cid}/memory/status')
        if not status.get('enabled'):
            raise APIError('Chat memory is OFF; set CHAT_MEMORY_ENABLED=true and restart backend')
        if status.get('failed_turns', 0):
            raise APIError(f'Memory indexing failed for {status["failed_turns"]} turn(s)')
        if status.get('pending_turns', 0) == 0 and not status.get('indexing', False):
            print(f'  Chat Mem0 indexed: {status.get("ready_turns", 0)} turns', flush=True)
            return
        time.sleep(1)
    raise APIError('Chat memory indexing still pending; increase --chat-memory-wait')


def chat_test(client,args,out):
    seed=json.loads((HERE/'seed_en.json').read_text(encoding='utf-8'))
    qs=json.loads((HERE/'questions_en.json').read_text(encoding='utf-8'))
    cid,first=make_chat_character(client)
    conversation=first
    trace=[]
    for j,session in enumerate(seed['sessions']):
        if args.chat_seed_mode=='separate' and j:
            conversation=new_conv(client,cid)
        for k,msg in enumerate(session['user_messages']):
            ans=send(client,conversation,msg)
            trace.append({'session':session['id'],'input':msg,'response':ans,'conversation_id':conversation})
        print(f'  seeded {session["id"]}',flush=True)
    if args.filler_turns:
        # Distinction: this inserts distractors into the final seed thread.
        for i in range(args.filler_turns):
            send(client,conversation,filler(i))
            if (i+1)%20==0:print(f'  filler turns {i+1}/{args.filler_turns}',flush=True)
    if args.wait_for_chat_memory:
        wait_for_chat_index(client, cid, args.chat_memory_wait)
    rows=[]
    for condition in args.chat_conditions.split(','):
        if condition not in ('same','fresh'):raise ValueError('chat conditions must be same,fresh')
        for q in qs:
            # Fresh probe conversation per question eliminates answer leakage.
            conv=conversation if condition=='same' else new_conv(client,cid)
            try:
                answer=send(client,conv,q['question'])
                score,criterion=question_score(q,answer)
                status='ok'
            except Exception as e:
                answer=str(e);score=0;criterion='api_error';status='error'
            row={'run_label':args.label,'module':'chat','seed_mode':args.chat_seed_mode,
                 'condition':condition,'id':q['id'],'category':q['category'],
                 'question':q['question'],'expected':q['expected'],
                 'response':answer,'heuristic_score_0_2':score,'weight':q['weight'],
                 'criterion':criterion,'status':status,'conversation_id':conv}
            rows.append(row)
            print(f'  {condition} {q["id"]}: {score}/2 ({status})',flush=True)
    write_rows(out/'chat_results.csv',rows)
    save_json(out/'chat_seed_trace.json',trace)
    save_json(out/'chat_metadata.json',{'character_id':cid,'first_conversation_id':first,
        'last_seed_conversation_id':conversation,'seed_mode':args.chat_seed_mode,
        'filler_turns':args.filler_turns,'note':'all questions are independent only in fresh condition; same probes accumulate in same thread'})
    return rows


def quick_character(client,name,description):
    result=client.post('/api/rehearsal/characters',{'operation_id':u(),'name':name,'description':description})
    return result['character_id']


def command(client,scene,kind,**fields):
    return client.post(f'/api/rehearsal/scenes/{scene["id"]}/commands',{
        'operation_id':u(),'expected_revision':scene['revision'],'kind':kind,**fields})


def poll(client,jid,seconds,interval):
    stop=time.monotonic()+seconds
    while time.monotonic()<stop:
        job=client.get(f'/api/rehearsal/jobs/{jid}')
        if job['status'] in ('completed','failed','cancelled'):
            return job
        time.sleep(interval)
    raise APIError(f'Job {jid} did not finish within {seconds}s; inspect server')


def story_text(scene):
    d=scene['document'];v=d['versions'][d['active_version']]
    ids=[];node=v.get('head');seen=set()
    while node and node not in seen:
        seen.add(node)
        current=d['nodes'].get(node)
        if not current:break
        ids.append(current)
        node=current.get('parent')
    ids.reverse()
    return '\n'.join(b.get('text','') for n in ids for b in n.get('blocks',[]))


def rehearsal_test(client,args,out):
    # The seeded event is provided as DIRECTOR INSTRUCTION inside the *first* generation.
    # Subsequent generations contain no copied secret, so only prior scene state/history or Mem0 can supply it.
    aid=quick_character(client,'Mira','Mira is a careful conservator who always speaks precisely, studies old maps, and protects private information.')
    bid=quick_character(client,'Noah','Noah is Mira’s friend, a curious researcher who follows clues but respects confidentiality.')
    scene=client.post('/api/rehearsal/scenes',{'operation_id':u(),'demo':False,'character_ids':[aid,bid],
        'setup':{'premise':'Two researchers work together in a quiet archive after discovering an old letter.',
            'goal':'Dramatize discoveries through concrete actions with clear knowledge boundaries.',
            'language':'en','knowledge_a':'Mira is familiar with the archive.','knowledge_b':'Noah has never met the archivist.'}})
    rows=[];jobs=[]
    prompts=[
      ('event','Mira finds a folded letter. The letter states that the blue cabinet contains a copper compass called ORION-47. Mira reads it silently and hides the letter; Noah does not see its contents. Represent this discovery as an explicit state change with known_by Mira only; do not expose it in dialogue.'),
      ('continue',''),('continue',''),('continue',''),
      ('event','Noah asks Mira whether she learned anything important from the letter. Maintain the established distinction between what Mira knows and what Noah has personally learned. Do not invent a confession unless the scene shows one.')
    ]
    for i,(kind,instruction) in enumerate(prompts,1):
        resp=command(client,scene,kind,**({'text':instruction} if instruction else {}))
        jid=resp.get('job_id')
        if not jid:raise APIError('Missing job_id from rehearsal command')
        job=poll(client,jid,args.job_timeout,args.poll_interval)
        jobs.append(job)
        scene=job['scene']
        mem=job.get('memory') or {}
        status=job['status']
        narrative=story_text(scene)
        row={'run_label':args.label,'module':'rehearsal','step':i,'kind':kind,
             'job_id':jid,'job_status':status,'memory_status':mem.get('status','unknown'),
             'retrieved_count':len(mem.get('items') or []),
             'used_count':len(mem.get('used_ids') or []),
             'pending_sources':mem.get('pending_sources',''),
             'elapsed_ms':mem.get('elapsed_ms',''),
             'error_type':mem.get('error_type',''),
             'orion_47_in_full_story':('orion-47' in narrative.lower()),
             'orion_47_in_memory_items':('orion-47' in json.dumps(mem.get('items') or []).lower()),
             'notes':'Memory extraction requires model-generated changes with source and known_by; manual review of isolation required.'}
        rows.append(row)
        print(f'  rehearsal {i}: {status}; memory={row["memory_status"]}; retrieved={row["retrieved_count"]}; used={row["used_count"]}',flush=True)
        if status!='completed':break
        # Do not modify 'revealed' or state; subsequent command should continue active head.
    write_rows(out/'rehearsal_results.csv',rows)
    save_json(out/'rehearsal_jobs.json',jobs)
    save_json(out/'rehearsal_scene.json',scene)
    save_json(out/'rehearsal_metadata.json',{'scene_id':scene['id'],'actor_ids':[aid,bid],
        'note':'Do not compare rehearsal scores with chat scores. Rehearsal A/B requires separate server restarts, identical code/model/settings, and MEMORY_ENABLED toggle.'})
    return rows


def main():
    p=argparse.ArgumentParser(description='Run Echoloom Chat & Rehearsal memory tests against local API')
    p.add_argument('--mode',choices=['chat','rehearsal','both'],default='both')
    p.add_argument('--base-url',default='http://127.0.0.1:8000')
    p.add_argument('--label',required=True,help='e.g. memory_off or memory_on')
    p.add_argument('--output',default=str(HERE / 'benchmark_results'))
    p.add_argument('--username',default=os.environ.get('ECHOLOOM_TEST_USERNAME'))
    p.add_argument('--password',default=os.environ.get('ECHOLOOM_TEST_PASSWORD'))
    p.add_argument('--create-account',action='store_true',help='explicitly create the FIRST local account if not initialized')
    p.add_argument('--chat-seed-mode',choices=['same','separate'],default='same',
                   help='same seed thread or separate conversation per session')
    p.add_argument('--chat-conditions',default='same,fresh',help='comma-separated: same,fresh')
    p.add_argument('--filler-turns',type=int,default=0,help='extra distractor user turns; each incurs a model call')
    p.add_argument('--wait-for-chat-memory',action='store_true',help='wait for asynchronous Mem0 indexing after chat seed')
    p.add_argument('--chat-memory-wait',type=int,default=600,help='maximum wait for chat memory indexing in seconds')
    p.add_argument('--job-timeout',type=int,default=300)
    p.add_argument('--poll-interval',type=float,default=1.0)
    p.add_argument('--timeout',type=int,default=180)
    args=p.parse_args()
    if args.filler_turns<0: p.error('--filler-turns must be >= 0')
    target=Path(args.output).resolve()/re.sub('[^a-zA-Z0-9_.-]','_',args.label)
    if target.exists() and any(target.iterdir()):p.error(f'Output directory already exists and is not empty: {target}; choose another label')
    target.mkdir(parents=True,exist_ok=True)
    client=Client(args.base_url,args.timeout)
    print('Checking API and logging in...',flush=True)
    health=client.get('/api/health')
    if not health.get('database_ready') or not health.get('text_configured'):
        raise APIError('Backend database or text provider not ready; check /api/health and .env')
    login(client,args)
    results={}
    try:
        if args.mode in ('chat','both'):
            print('Running Character Chat...',flush=True)
            results['chat']=chat_test(client,args,target)
        if args.mode in ('rehearsal','both'):
            print('Running Rehearsal...',flush=True)
            results['rehearsal']=rehearsal_test(client,args,target)
    finally:
        save_json(target/'run_config.json',{'label':args.label,'mode':args.mode,'base_url':args.base_url,
            'seed_mode':args.chat_seed_mode,'chat_conditions':args.chat_conditions,
            'filler_turns':args.filler_turns,'health':health,
            'memory_flag':'Not exposed by health endpoint; user must record MEMORY_ENABLED setting',
            'credentials_redacted':True})
    print(f'\nOutputs: {target}',flush=True)
    if 'chat' in results:
        for c in ('same','fresh'):
            r=[x for x in results['chat'] if x['condition']==c]
            if r:
                pts=sum(x['heuristic_score_0_2']*x['weight'] for x in r)
                total=sum(2*x['weight'] for x in r)
                print(f'  chat {c}: provisional keyword coverage {pts}/{total} ({pts/total:.1%}); requires human review')
    print('NOTE: Memory settings are not verified by the API. Confirm server .env and job telemetry yourself.')


if __name__=='__main__':
    try:main()
    except (APIError,ValueError,AssertionError) as exc:
        print(f'ERROR: {exc}',file=sys.stderr);sys.exit(1)
