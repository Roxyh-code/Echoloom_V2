#!/usr/bin/env python3
"""Compare outputs of two independent benchmark runs; no external dependencies."""
import argparse
import csv
from pathlib import Path


def rows(path):
    if not path.exists():return []
    with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))


def pct(a,b):return f'{100*a/b:.1f}%' if b else 'n/a'


def summarize_chat(data):
    groups={}
    for r in data:
        cond=r['condition']; cat=r['category']
        for key in ((cond,'ALL'),(cond,cat)):
            z=groups.setdefault(key,[0,0,0]);w=int(r['weight'])
            z[0]+=int(r['heuristic_score_0_2'])*w;z[1]+=2*w;z[2]+=1
    return groups


def summarize_rehearsal(data):
    def n(x):
        try:return int(x)
        except:return 0
    return {'steps':len(data),'completed':sum(x['job_status']=='completed' for x in data),
            'retrieved':sum(n(x['retrieved_count']) for x in data),
            'used':sum(n(x['used_count']) for x in data),
            'statuses':','.join(x['memory_status'] for x in data)}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('a',help='first run folder e.g. benchmark_results/memory_off')
    p.add_argument('b',help='second run folder e.g. benchmark_results/memory_on')
    args=p.parse_args()
    a,b=Path(args.a),Path(args.b)
    A,B=rows(a/'chat_results.csv'),rows(b/'chat_results.csv')
    if A and B:
        print('CHAT: approximate keyword coverage (not verified semantic accuracy)')
        ga,gb=summarize_chat(A),summarize_chat(B)
        for k in sorted(set(ga)&set(gb)):
            aa,ab,_=ga[k];ba,bb,_=gb[k]
            print(f'{str(k):30s}  A={pct(aa,ab):>7s}  B={pct(ba,bb):>7s}')
    RA,RB=rows(a/'rehearsal_results.csv'),rows(b/'rehearsal_results.csv')
    if RA and RB:
        print('\nREHEARSAL: retrieval telemetry and generation progress (not a quality score)')
        for name,rec in [('A',RA),('B',RB)]:
            print(name,summarize_rehearsal(rec))
        print('Compare rehearsal_scene.json and rehearsal_jobs.json manually for continuity and knowledge leakage.')
    if not (A and B) and not (RA and RB):
        p.error('no matching result files in both folders')


if __name__=='__main__':main()
