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
import { Button } from './components/ui/button'

function App() {
  const [userName, setUserName] = useState('not logged in')
  const [userId, setUserId] = useState('')
  const [displayName1, setDisplayName1] = useState('chat')
  const [displayName2, setDisplayName2] = useState('financials')
  const [displayName3, setDisplayName3] = useState('financials') // Need to create a third display

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
                This will eventually go into a seperate component */}
          <div className="flex flex-row flex-1 py-1 px-2">
            <div className='gap-1 p-0'>
              <h2 className='font-semibold text-lg justify-self-center'>Kocoon</h2>
              {/* This div should be some kind of popover / hover menu component */}
              <div className='flex gap-1'>
                <Button onClick={() => setDisplayName1(displayName1 === 'chat' ? 'financials' : 'chat')} variant='outline'>
                  Switch left display
                </Button>
                <Button onClick={() => setDisplayName2(displayName2 === 'chat' ? 'financials' : 'chat')} variant='outline'>
                  Switch right display
                </Button>
                <Button onClick={() => setDisplayName3(displayName3 === 'chat' ? 'financials' : 'chat')} variant='outline'>
                  Switch bottom display
                </Button>
              </div>
            </div>
            { /* TODO This div should be made into a login component once we add more login methods such as other auth providers, NOSTR, username / pass, blockchain, etc... */}
            <div className='flex-1 justify-end flex gap-2'>
              <GithubLoginButton username={userName} userId={userId}/>
              <ModeToggle />
            </div>
          </div>

        </ResizablePanel>
        <ResizableHandle withHandle/>
        <ResizablePanel className='w-full h-full'>
          <ResizablePanelGroup direction="horizontal"
          className="justify-self-center h-full rounded-lg border">
            <ResizablePanel className='w-full'>
              {/* Left Panel - Chat Panel */}
              { (displayName1 === 'chat') && <ChatDisplay fluxnoteUsername={userId + '-' + userName}/> }
              { (displayName1 === 'financials') && <FinancialsDisplay /> }

          </ResizablePanel>
            <ResizableHandle withHandle/>
            <ResizablePanel defaultSize={60} className='w-full'>
              {/* Right Panel - Financials */}
              { (displayName2 === 'financials' && <FinancialsDisplay />) }
              { (displayName2 === 'chat' && <ChatDisplay fluxnoteUsername={userId + '-' + userName}/> ) }
            </ResizablePanel>
          </ResizablePanelGroup>
        </ResizablePanel>
        <ResizableHandle withHandle/>
        <ResizablePanel defaultSize={0} className='w-full'>
          <div className="flex flex-col flex-1 py-1 px-2">
            { (displayName3 === 'financials' && <FinancialsDisplay />) }
            { (displayName3 === 'chat' && <ChatDisplay fluxnoteUsername={userId + '-' + userName}/> ) }
          </div>
        </ResizablePanel>
      </ResizablePanelGroup>
    </div>
  )
}

export default App