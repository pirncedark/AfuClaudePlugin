import json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
import yonlendir as y
class FastTests(unittest.TestCase):
 def invoke(self,events):
  with tempfile.TemporaryDirectory() as d, patch.object(y,'BASE_DIR',Path(d)), patch.dict(y.os.environ,{'AFU_CODEX_LEGACY':'0'}), patch.object(y,'resolve_executable',return_value='codex'), patch.object(y,'run_process',return_value={'status':'ok','returncode':0,'output':'\n'.join(json.dumps(x) for x in events)}) as run:
   result=y.run_codex('merhaba'); return result,run.call_args.args[0]
 def test_direct_path(self):
  r,c=self.invoke([{'type':'item.completed','item':{'type':'agent_message','text':'Merhaba'}},{'type':'turn.completed'}]);self.assertEqual(r['status'],'ok');self.assertEqual(r['output'],'Merhaba');self.assertIn('exec',c);self.assertNotIn(y.CHAIN,c);self.assertIn('gpt-6-luna',c)
 def test_zero_exit_quota(self):
  r,_=self.invoke([{'type':'turn.failed','error':{'message':'usage limit'}}]);self.assertEqual(r['status'],'quota')
 def test_incomplete_not_success(self):
  r,_=self.invoke([{'type':'thread.started'}]);self.assertEqual(r['status'],'error')
 def test_success_discussing_limits(self):
  r,_=self.invoke([{'type':'item.completed','item':{'type':'agent_message','text':'usage limit handler fixed'}},{'type':'turn.completed'}]);self.assertEqual(r['status'],'ok')

 def test_success_uses_normal_conversation(self):
  import io
  output=io.StringIO()
  with patch.dict(y.RUNNERS, {'codex':lambda _: {'status':'ok','output':'Merhaba'}}), patch.object(y,'log_call'):
   y.route_task('mrb','codex',output)
  payload=json.loads(output.getvalue())
  self.assertNotIn('stopReason',payload)
  self.assertIn('Merhaba',payload['hookSpecificOutput']['additionalContext'])
