import { Button } from "@/components/ui/button";
const GithubLoginButton = () => {
    const handleLogin = () => {
        window.location.href = "https://host.zzimm.com/api/github_login";
    };

    return (
        <Button onClick={handleLogin}>
            Login with GitHub
        </Button>
    )};
export default GithubLoginButton;