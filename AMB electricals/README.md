# AMB Electricals & Services Website

This is a modern, responsive company website for AMB Electricals & Services.

## Publish to GitHub Pages
1. Create a GitHub repository and push this folder to it.
2. In GitHub, open the repository settings.
3. Go to Pages.
4. Under Build and deployment, choose GitHub Actions.
5. Push to the main branch and wait for the workflow to deploy.
6. Your site will be available at:
   https://<your-username>.github.io/<your-repo-name>/

## Run locally
1. Open the project folder.
2. Start a simple server from the project root, for example:
   python -m http.server 8000
3. Open: http://127.0.0.1:8000/

## Note
The website is fully static and works well on GitHub Pages. The payment backend files are included for future use, but they are not required for the public website itself.

## Deployment checklist
- The live URL will be `https://powertech285.github.io/ambelectricals/` after deployment.
- Push this repository to GitHub and enable Pages on the `main` branch.
- The existing `.github/workflows/deploy-pages.yml` will publish the site automatically when you push.
- If you later buy a custom domain, add a `CNAME` file at the project root with that domain.
