from pathlib import Path
import subprocess,sys
ROOT=Path(__file__).resolve().parent
if __name__=='__main__':
    if not (ROOT/'deliverables/analysis/dashboard_all.json').exists():
        subprocess.run([sys.executable,str(ROOT/'analysis/pipeline.py')],check=True)
    import uvicorn
    print('Olist Web 展示：http://127.0.0.1:8780')
    uvicorn.run('backend.app:app',host='127.0.0.1',port=8780,app_dir=str(ROOT))
