# Kocoon
#### is a personal finance and investment exploration platform that takes both a qualitative and a quantitative approach to financial literacy.

## Starting the frontend for development
- Ensure `nodejs` and `npm` are installed on your system
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