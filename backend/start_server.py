import os, sys
os.chdir(r'd:\bzb\backend')
sys.path.insert(0, r'd:\bzb\backend')

if __name__ == '__main__':
    import uvicorn
    uvicorn.run('app.main:app', host='0.0.0.0', port=8000, reload=True)
