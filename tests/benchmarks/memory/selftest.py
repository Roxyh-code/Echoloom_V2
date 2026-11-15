#!/usr/bin/env python3
"""No-network no-cost smoke tests for the benchmark runner's output/scoring helpers."""
import tempfile
from pathlib import Path
from run_benchmark import question_score, save_json, write_rows, story_text


def run():
    assert question_score({'category':'fact','hints':[['blue'],['green']]},'blue and green')[0]==2
    assert question_score({'category':'unknown','hints':[]},'I do not know.')[0]==2
    assert question_score({'category':'unknown','hints':[]},'She studied chemistry.')[0]==0
    sample={'document':{'active_version':'v','versions':{'v':{'head':'n2'}},'nodes':{
        'n1':{'parent':None,'blocks':[{'text':'first line'}]},
        'n2':{'parent':'n1','blocks':[{'text':'second line'}]}}}}
    assert story_text(sample)=='first line\nsecond line'
    with tempfile.TemporaryDirectory() as d:
        p=Path(d)
        write_rows(p/'x.csv',[{'run':'a','score':2},{'run':'b','score':0}])
        save_json(p/'y.json',{'ok':True})
        assert (p/'x.csv').exists() and (p/'y.json').exists()
    print('Self-test PASSED: scoring, chain extraction, CSV and JSON writing.')


if __name__=='__main__':run()
