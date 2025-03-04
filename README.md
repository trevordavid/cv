# **Automated CV with Citation Updates**

This repository hosts my CV, which is automatically updated with my latest citation metrics and regenerated as a PDF using GitHub Actions.

## **Features**
✅ Automatically fetches updated citation metrics from NASA ADS and Google Scholar  
✅ Recompiles the CV using LaTeX  
✅ Commits and pushes changes to the repository  
✅ Publishes the updated CV as an artifact  


## **Setup**

### **Locally Compiling the CV**
1. Install LaTeX (e.g., via TeX Live or MiKTeX)  
2. Run:  
   ```sh
   xelatex cv.tex

## **GitHub Actions Workflow**
- The workflow updates citation metrics and compiles the CV.
- Private details (email, phone) are stored securely using **GitHub Secrets**.
- The compiled PDF is uploaded as an artifact and pushed to the repository.

### **Download the Latest Compiled CV**
You can always download the most up-to-date version of my CV from the **GitHub Actions artifacts** or via the latest release:

🔗 **[Download Latest CV](https://github.com/trevordavid/cv/blob/main/cv.pdf)**  

## **Security Considerations**
- `private_info.tex` is **not** tracked in Git to protect personal details.
- GitHub Secrets securely store sensitive information.
- `.github/workflows/update.yml` automates the CV update process.

## **Usage with `act` (Local Testing)**
To test the GitHub Actions workflow locally, use [`act`](https://github.com/nektos/act):  
```sh
act -s GH_PAT=$GH_PAT
