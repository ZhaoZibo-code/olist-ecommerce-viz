"""Persist meaningful source, aggregate, API and DOCX verification results."""
from pathlib import Path
import json,sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
if __name__=='__main__':
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover(str(ROOT/'tests')))
 record=dict(result='passed' if result.wasSuccessful() else 'failed',tests=result.testsRun,passed=result.testsRun-len(result.failures)-len(result.errors)-len(result.skipped),skipped=len(result.skipped),failed=len(result.failures),errors=len(result.errors))
 (ROOT/'reports/verification.json').write_text(json.dumps(record,indent=2))
 if not result.wasSuccessful():sys.exit(1)
