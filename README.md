# Kocoon
#### is a personal finance and investment exploration platform that takes both a qualitative and a quantitative approach to financial literacy.

## Starting the frontend for development
- ensure `nodejs` and `npm` are installed on your system
- `cd` into the `frontend` directory
- run `npm install`
- run `npm run dev`
- verify that there are no errors and if the build was successful navigate to the address indicated in your terminal output
    - The address is probably http://localhost:5173

## Building the frontend for deployment
- navigate into the frontend directory
- run `npm install`
- run `npm build` to build after performing a strict TypeScript check
    - run `npm devbuild` to build without the TypeScript check
- run `npm preview` to deploy the app

## Starting the backend server
- ensure `python` is installed on your system
- `cd` into the `backend` directory
- create a virtual environment if one does not already exist on your system
    - on macOS / linux this is `python -m venv venv` 
        - it's similar on windows but ultimately WSL might be a better option
- activate the virtual environment
    - unix-based command: `source venv/bin/activate`
- run `python python_usage.py` to see usage

## Frontend tech stack
- React JS web interface
  - Bootstrapped with ShadCN UI components
  - Further customized using TaiwindCSS
- Vite build server

## Backend tech stack
- Python FastAPI / Uvicorn WSGI server
- PostgreSQL database
