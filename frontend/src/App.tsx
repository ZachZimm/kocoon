import { useState, useEffect } from 'react'
// Keeping these imports around as examples and reminders for now
import reactLogo from './assets/react.svg'
import viteLogo from '/vite.svg'
import './App.css'
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable"
import { ChatDisplay } from './components/chat-display'
import { FinancialsDisplay } from './components/financials-display'
import GithubLoginButton from './components/github-login-button'
import ModeToggle from './components/ui/mode-toggle'

function App() {
  const [userName, setUserName] = useState('not logged in')
  const [userId, setUserId] = useState('')

  useEffect(() => {
    // Check if user is logged in
    const userData = document.cookie
      .split('; ')
      .find(row => row.startsWith('user_id='))
      ?.split('=')[1];
    console.log(document.cookie)

    if (userData) {
      // Fetch user data from backend
      fetch(`https://host.zzimm.com/api/user/${userData}`)
        .then(res => res.json())
        .then(data => {
          // Data is returned as [user_id, username]
          setUserName(data[1])
          setUserId(data[0])
          });
    }
  }, []);

  return (
    <div className='h-[92vh] w-[93vw] items-center justify-center'>
      <ResizablePanelGroup direction="vertical"
      className="justify-self-center h-full rounded-lg border">        
        <ResizablePanel defaultSize={6} className='w-full'>

          {/* Header 
                This will eventually go into a seperate component8*/}
          <div className="flex flex-row flex-1 py-1 px-2">
            <h2 className='font-semibold text-lg justify-self-center pb-4'>Kocoon</h2>
            <div className='flex-1 justify-end flex gap-2'>
              <span className='font-semibold'>{userName}</span>
              <GithubLoginButton />
              <ModeToggle />
            </div>
          </div>

        </ResizablePanel>
        <ResizableHandle withHandle/>
        <ResizablePanel className='w-full h-full'>
          <ResizablePanelGroup direction="horizontal"
          className="justify-self-center h-full rounded-lg border">
            <ResizablePanel className='w-full'>
              {/* Chat Panel */}
              <ChatDisplay fluxnoteUsername={userId + '-' + userName}/>

          </ResizablePanel>
            <ResizableHandle withHandle/>
            <ResizablePanel defaultSize={60} className='w-full'>
              {/* Secondary panel */}
              <FinancialsDisplay />

            </ResizablePanel>
          </ResizablePanelGroup>
        </ResizablePanel>
        <ResizableHandle withHandle/>
        <ResizablePanel defaultSize={0} className='w-full'>
          <div className="flex flex-col flex-1 py-1 px-2">
            <span className='font-semibold'>Nothing here yet...</span>
          </div>
        </ResizablePanel>
      </ResizablePanelGroup>
    </div>
  )
}

export default App