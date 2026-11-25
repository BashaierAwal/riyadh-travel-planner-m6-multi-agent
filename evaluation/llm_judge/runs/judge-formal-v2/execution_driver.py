import time, hashlib, shutil
from datetime import datetime, timezone
from google.colab import files
output = Path('/content/drive/MyDrive/M6_Judge_Results/judge-formal-v2')
output.mkdir(parents=True,exist_ok=True)
assert not (output/'results.json').exists(), 'Existing version: inspect before resuming'
policy = {'version':'judge-formal-v2','judge_model':MODEL,'logical_plan_cap':114,'http_cap':126,'previous_attempt_requests':2,'combined_cap':128,'max_attempts_per_plan':3,'retry_codes':[500,502,503,504],'retry_spacing_seconds':12,'rubric_changed':False,'prior_attempt_pooled':False,'input_fingerprint':fingerprint}
judge.write(output/'execution_policy.json',policy)
(output/'source_snapshot').mkdir(exist_ok=True)
for name in ['evaluate.py','rubric.json']:
    shutil.copy2(judge_dir/name,output/'source_snapshot'/name)
http_count=0
def resilient_provider(prompt):
    global http_count
    states=judge.read(output/'results.json')
    active=[rid for rid,value in states.items() if value['status']=='in_flight']
    assert len(active)==1
    rid=active[0]
    for attempt in range(1,4):
        if http_count >= 126:
            raise RuntimeError('Approved HTTP cap reached')
        http_count += 1
        path=output/'http_attempts'/('%03d.json'%http_count)
        receipt={'request_number':http_count,'run_id':rid,'attempt':attempt,'started_at_utc':datetime.now(timezone.utc).isoformat(),'status':'in_flight'}
        judge.write(path,receipt)
        print('JUDGE_PROGRESS',http_count,rid,'attempt',attempt,flush=True)
        try:
            response=client.models.generate_content(model=MODEL,contents=prompt,config=types.GenerateContentConfig(temperature=0,max_output_tokens=1600,response_mime_type='application/json'))
        except Exception as error:
            code=getattr(error,'code',None)
            receipt.update(status='provider_error',error_type=type(error).__name__,provider_code=code)
            judge.write(path,receipt)
            print('JUDGE_SERVICE_ERROR',code,'request',http_count,flush=True)
            if code in (500,502,503,504) and attempt<3:
                time.sleep(12)
                continue
            raise
        receipt.update(status='response_received',response_id=getattr(response,'response_id',None))
        judge.write(path,receipt)
        return response.model_dump(mode='json'),response.text
results=judge.run(items,fingerprint,output,MODEL,114,True,resilient_provider)
print('FORMAL_JUDGE_SUMMARY',json.dumps(judge.read(output/'summary.json')),flush=True)
print('FORMAL_JUDGE_HTTP_REQUESTS',http_count,flush=True)
archive=shutil.make_archive('/content/M6_Judge_Formal_v2','zip',output)
shutil.copy2(archive,output.parent/'M6_Judge_Formal_v2.zip')
print('JUDGE_ARCHIVE_READY',archive,flush=True)
files.download(archive)
