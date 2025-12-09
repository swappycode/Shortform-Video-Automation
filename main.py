import sys, subprocess

def run(script, fatal=True):
    print(f"--- RUN: {script} ---")
    
    p = subprocess.run([sys.executable, script])

    # Layer allowed to fail softly
    if fatal and p.returncode != 0:
        print(f"ERROR running {script}. stopping.")
        sys.exit(1)

if __name__ == "__main__":
    run("layer1.py", fatal=True)
    run("layer2.py", fatal=False)   # allow warnings/errors but keep going
    run("layer3.py", fatal=True)

    print("ALL DONE.")
