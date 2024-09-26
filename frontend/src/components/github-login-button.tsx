import { Button } from "@/components/ui/button"
import { useEffect } from "react";

interface GithubLoginButtonProps {
    username: string;
    userId: string;
}

const GithubLoginButton = ({username, userId}: GithubLoginButtonProps) => {
    const handleLogin = () => {
        window.location.href = "https://host.zzimm.com/api/github_login";
    };
    const handleLogout = () => { 
        document.cookie = "user_id=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
        window.location.href = "/";
    }

    useEffect(() => {}, [username, userId]);
    console.log("userId: ", userId);
    if (userId !== '') {
        return (
            <Button onClick={handleLogout}>
                Logout {username}
            </Button>
        )
    }
    else {
        return (
            <Button onClick={handleLogin}>
                Login with GitHub
            </Button>
        )};
    };
export default GithubLoginButton;