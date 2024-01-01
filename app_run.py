import subprocess
import os, sys, time

def main():
    try:
        print("APP LOADING...\n")
        print("--- 터미널을 닫을 경우 서버가 종료됩니다.")
        app_path = 'app.py'
        db_path = 'db.db'
        config_path = 'config.yaml'
        result0 = subprocess.run(['python.exe', '-m', 'pip', 'install', '--upgrade', 'pip'])
        result1 = subprocess.run(['python.exe', '-m', 'pip', 'install', 'numpy', 'pandas', 'plotly', 'streamlit', 'streamlit-option-menu', 'streamlit-authenticator'])
        result2 = subprocess.run(['python.exe', '-m', 'pip', 'install', 'numpy', 'pandas', 'plotly', 'streamlit', 'streamlit-option-menu', 'streamlit-authenticator'])
        result3 = subprocess.run(f"python.exe -m streamlit run {app_path} {db_path} {config_path}", shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
    except subprocess.CalledProcessError as e:
        print("Exit code:", e.returncode)
        print("Standard output:", e.stdout.decode('utf-8'))
        print("Standard error:", e.stderr.decode('utf-8'))
    
    except Exception as e:
        print(e)
    
    for i in range(31):
        print(f'{30-i}초 후에 종료합니다.', end="\r")
        time.sleep(1)


if __name__ == "__main__":
    main()
