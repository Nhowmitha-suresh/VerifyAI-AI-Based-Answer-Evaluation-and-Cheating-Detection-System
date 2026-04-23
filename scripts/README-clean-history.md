Cleaning large files from history with git-filter-repo

1) Install git-filter-repo

   - Using pip:
     ```powershell
     pip install git-filter-repo
     ```

2) Edit `scripts/paths-to-remove.txt` to include any paths or directories to remove from history.

3) Run the helper (PowerShell):
   ```powershell
   cd <somewhere/outside/your/repo>
   powershell -ExecutionPolicy Bypass -File path\to\project\verifiX\scripts\clean_history_gitfilter.ps1
   ```

4) After success, re-clone the cleaned repository:
   ```powershell
   git clone https://github.com/<your>/repo.git
   ```

Notes:
- This rewrites history and force-pushes; all collaborators must re-clone.
- You may prefer BFG Repo Cleaner for a simpler UI, but git-filter-repo is more flexible.
- If you intend to keep large binary assets, use Git LFS after cleaning and re-add them tracked by LFS.
